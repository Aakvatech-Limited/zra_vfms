# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import strip_html

from zra_vfms.utils.utils import get_zra_setting, send_request
from zra_vfms.zra_vfms.doctype.zra_einvoice_log.zra_einvoice_log import create_log, update_log
from zra_vfms.zra_vfms.doctype.zra_tax_invoice.zra_tax_invoice import (
    create_tax_invoice,
    get_tax_invoice,
    update_tax_invoice,
)


def on_submit(doc, method):
    """Hook: Auto-send tax to ZRA when Sales Invoice is submitted.

    Called via doc_events hook on Sales Invoice on_submit.
    Skips silently if:
    - is_non_taxable is checked
    - No ZRA Setting exists for the company
    - posting_date is before the ZRA start date
    """
    if doc.get("is_non_taxable"):
        return

    setting = get_zra_setting(doc.company)
    if not setting:
        return

    if setting.zra_start_date and doc.posting_date < setting.zra_start_date:
        return

    # Set status to Pending immediately
    frappe.db.set_value(
        "Sales Invoice", doc.name, "tax_status", "Pending",
        update_modified=False,
    )

    # Enqueue the actual sending to avoid blocking the submit transaction
    frappe.enqueue(
        "zra_vfms.api.sales_invoice.process_tax_submission",
        queue="short",
        sales_invoice=doc.name,
        enqueue_after_commit=True,
    )


@frappe.whitelist()
def send_tax(sales_invoice):
    """Manually send tax to ZRA via the Send Tax button.

    Args:
        sales_invoice: Name of the Sales Invoice.

    Returns:
        Dict with success (bool) and message (str).
    """
    sinv = frappe.get_doc("Sales Invoice", sales_invoice)

    if sinv.get("is_non_taxable"):
        frappe.throw(_("This invoice is marked as non-taxable."))

    if sinv.docstatus != 1:
        frappe.throw(_("Sales Invoice must be submitted before sending tax."))

    setting = get_zra_setting(sinv.company)
    if not setting:
        frappe.throw(
            _("No ZRA Setting found for company {0}. "
              "Please create one in ZRA Setting.").format(sinv.company)
        )

    # Check if already sent successfully
    existing = get_tax_invoice(sinv.name)
    if existing and existing.status == "Success":
        frappe.throw(
            _("Tax has already been sent successfully for this invoice. "
              "Receipt Number: {0}").format(existing.receipt_number)
        )

    # Process synchronously for manual send
    return process_tax_submission(sinv.name)


def process_tax_submission(sales_invoice):
    """Process the actual tax submission to VFMS.

    Core function that:
    1. Determines the endpoint and tax type
    2. Builds the request payload
    3. Creates ZRA Tax Invoice and eInvoice Log
    4. Sends the API request
    5. Updates all records with the response

    Args:
        sales_invoice: Name of the Sales Invoice.

    Returns:
        Dict with success (bool), message (str), and receipt_number (str).
    """
    sinv = frappe.get_doc("Sales Invoice", sales_invoice)
    setting = get_zra_setting(sinv.company)

    if not setting:
        _update_tax_status(sinv.name, "Failed")
        return {"success": False, "message": _("No ZRA Setting found")}

    # Determine tax type and endpoint
    tax_type, endpoint_name = _determine_tax_type_and_endpoint(sinv)

    # Build request payload
    payload = _build_request_payload(sinv, setting, endpoint_name)

    # Create or reuse existing ZRA Tax Invoice
    tax_inv = get_tax_invoice(sinv.name, tax_type)
    if not tax_inv:
        is_correction = bool(sinv.is_return)
        receipt_reference = None

        if is_correction and sinv.return_against:
            original_tax_inv = get_tax_invoice(sinv.return_against, tax_type)
            if original_tax_inv:
                receipt_reference = original_tax_inv.receipt_number

        tax_inv = create_tax_invoice(
            sales_invoice=sinv.name,
            company=sinv.company,
            tax_type=tax_type,
            status="Pending",
            is_correction=is_correction,
            receipt_reference=receipt_reference,
        )
    else:
        # Retry scenario — reset to Pending
        update_tax_invoice(tax_inv.name, status="Pending", error_message="")

    # Create eInvoice Log
    log = create_log(
        sales_invoice=sinv.name,
        request_type=endpoint_name,
        request_payload=payload,
        zra_tax_invoice=tax_inv.name,
        status="Pending",
    )

    # Send the API request
    result = send_request(setting, endpoint_name, payload, tax_type)

    if result["success"]:
        update_tax_invoice(
            tax_inv.name,
            response_data=result["response"],
            status="Success",
        )
        update_log(
            log.name,
            response_payload=result["response"],
            status="Success",
        )
        _update_tax_status(sinv.name, "Success")

        receipt_number = (result["response"] or {}).get("Receipt_number", "")
        return {
            "success": True,
            "message": _("Tax sent successfully. Receipt: {0}").format(
                receipt_number
            ),
            "receipt_number": receipt_number,
        }
    else:
        update_tax_invoice(
            tax_inv.name,
            response_data=result.get("response"),
            status="Failed",
            error_message=result["error"],
        )
        update_log(
            log.name,
            response_payload=result.get("response"),
            status="Failed",
            error_message=result["error"],
        )
        _update_tax_status(sinv.name, "Failed")

        frappe.log_error(
            title=f"ZRA VFMS: Tax submission failed for {sinv.name}",
            message=result["error"],
        )

        return {
            "success": False,
            "message": _("Tax submission failed: {0}").format(result["error"]),
        }


def _determine_tax_type_and_endpoint(sinv):
    """Determine the tax type and VFMS endpoint for a Sales Invoice.

    Logic:
    - Return invoices (credit notes) → Error Correction
    - Customer has TIN (tax_id) → B2B Sales
    - Default → Normal Sales

    Returns:
        Tuple of (tax_type, endpoint_name).
    """
    tax_type = "VAT"

    if sinv.is_return:
        return tax_type, "Error Correction"

    if sinv.tax_id:
        return tax_type, "B2B Sales"

    return tax_type, "Normal Sales"


def _build_request_payload(sinv, setting, endpoint_name):
    """Build the VFMS API request payload from Sales Invoice data.

    Delegates to specialised builders based on endpoint type.
    """
    if endpoint_name == "Error Correction":
        return _build_error_correction_payload(sinv, setting)

    return _build_sales_payload(sinv, setting)


def _build_sales_payload(sinv, setting):
    """Build a sales request payload (Normal, B2B, Institution).

    Maps ERPNext Sales Invoice fields to the VFMS API format
    per API Guide v1.5.
    """
    buyer_id_type = "6"  # NIL (walk-in customer)
    buyer_id = ""

    if sinv.tax_id:
        buyer_id_type = "1"  # TIN
        buyer_id = sinv.tax_id

    items = []
    for item in sinv.items:
        tax_rate = _get_item_tax_rate(item, sinv)
        tax_amount = _get_item_tax_amount(item, sinv)

        items.append({
            "Item_code": item.item_code or "",
            "Item_desc": (item.item_name or item.description or "")[:200],
            "Qty": float(item.qty),
            "Unit_price": float(item.rate),
            "Discount": float(item.discount_amount or 0),
            "Tax_code": _get_tax_code(tax_rate),
            "Tax_percent": float(tax_rate),
            "Tax_amount": float(tax_amount),
            "Nontaxable_amount": (
                float(item.net_amount) if tax_rate == 0 else 0.0
            ),
            "Amount": float(item.amount),
        })

    return {
        "Buyer_id_type": buyer_id_type,
        "Buyer_id": buyer_id,
        "Buyer_name": sinv.customer_name or sinv.customer or "",
        "Buyer_phone": _get_customer_phone(sinv),
        "Buyer_email": _get_customer_email(sinv),
        "Buyer_address": _get_customer_address(sinv),
        "Total_tax_excl": float(sinv.net_total),
        "Total_tax_incl": float(sinv.grand_total),
        "Total_discount": float(sinv.discount_amount or 0),
        "Tax_group": "A",
        "Payment_type": _get_payment_type(sinv),
        "Items": items,
    }


def _build_error_correction_payload(sinv, setting):
    """Build an error correction payload for credit notes / return invoices.

    References the original invoice receipt via Receipt_reference.
    Amounts are sent as positive values (absolute).
    """
    receipt_reference = ""
    if sinv.return_against:
        receipt_reference = (
            frappe.db.get_value(
                "ZRA Tax Invoice",
                {"sales_invoice": sinv.return_against, "status": "Success"},
                "receipt_number",
            )
            or ""
        )

    items = []
    for item in sinv.items:
        tax_rate = _get_item_tax_rate(item, sinv)
        tax_amount = _get_item_tax_amount(item, sinv)

        items.append({
            "Item_code": item.item_code or "",
            "Item_desc": (item.item_name or item.description or "")[:200],
            "Qty": abs(float(item.qty)),
            "Unit_price": float(item.rate),
            "Discount": abs(float(item.discount_amount or 0)),
            "Tax_code": _get_tax_code(tax_rate),
            "Tax_percent": float(tax_rate),
            "Tax_amount": abs(float(tax_amount)),
            "Nontaxable_amount": (
                abs(float(item.net_amount)) if tax_rate == 0 else 0.0
            ),
            "Amount": abs(float(item.amount)),
        })

    return {
        "Receipt_reference": receipt_reference,
        "Reason": sinv.remarks or "Error Correction",
        "Buyer_id_type": "1" if sinv.tax_id else "6",
        "Buyer_id": sinv.tax_id or "",
        "Buyer_name": sinv.customer_name or sinv.customer or "",
        "Total_tax_excl": abs(float(sinv.net_total)),
        "Total_tax_incl": abs(float(sinv.grand_total)),
        "Total_discount": abs(float(sinv.discount_amount or 0)),
        "Items": items,
    }


def _get_item_tax_amount(item, sinv):
    """Calculate the tax amount for a single item.

    Tries item_wise_tax_detail JSON first, falls back to
    proportional calculation from total taxes.
    """
    if sinv.taxes:
        for tax_row in sinv.taxes:
            if tax_row.item_wise_tax_detail:
                try:
                    tax_detail = json.loads(tax_row.item_wise_tax_detail)
                    item_key = item.item_code or item.item_name
                    if item_key in tax_detail:
                        _rate, amount = tax_detail[item_key]
                        return amount
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

        # Fallback: proportional
        if sinv.net_total:
            return (
                (item.net_amount / sinv.net_total)
                * sinv.total_taxes_and_charges
            )

    return 0.0


def _get_item_tax_rate(item, sinv):
    """Get the tax rate for a single item.

    Tries item_wise_tax_detail JSON first, falls back to the
    first tax row's rate.
    """
    if sinv.taxes:
        for tax_row in sinv.taxes:
            if tax_row.item_wise_tax_detail:
                try:
                    tax_detail = json.loads(tax_row.item_wise_tax_detail)
                    item_key = item.item_code or item.item_name
                    if item_key in tax_detail:
                        rate, _amount = tax_detail[item_key]
                        return rate
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

        # Fallback: first tax row
        if sinv.taxes[0].rate:
            return sinv.taxes[0].rate

    return 0.0


def _get_tax_code(tax_rate):
    """Map tax rate to VFMS tax code.

    A = Standard rate (18%)
    B = Special rate
    C = Zero rated (0%)
    D = Exempt
    E = Special relief
    """
    if tax_rate == 0:
        return "C"
    elif tax_rate == 18:
        return "A"
    else:
        return "B"


def _get_payment_type(sinv):
    """Determine VFMS payment type from Sales Invoice.

    Maps ERPNext mode of payment to VFMS values:
    CASH, CREDIT, CHEQUE, BANK_TRANSFER, MOBILE_MONEY.
    """
    if sinv.is_pos and sinv.payments:
        for payment in sinv.payments:
            mode = (payment.mode_of_payment or "").upper()
            if "CASH" in mode:
                return "CASH"
            elif "BANK" in mode or "TRANSFER" in mode:
                return "BANK_TRANSFER"
            elif "CHEQUE" in mode or "CHECK" in mode:
                return "CHEQUE"
            elif "MOBILE" in mode or "MPESA" in mode or "TIGO" in mode:
                return "MOBILE_MONEY"

    # Non-POS invoices are credit by default
    if not sinv.is_pos:
        return "CREDIT"

    return "CASH"


def _get_customer_phone(sinv):
    """Get customer phone from the invoice contact fields."""
    return sinv.get("contact_mobile") or sinv.get("contact_phone") or ""


def _get_customer_email(sinv):
    """Get customer email from the invoice contact fields."""
    return sinv.get("contact_email") or ""


def _get_customer_address(sinv):
    """Get customer address, stripping any HTML markup."""
    address = sinv.get("address_display") or ""
    if address:
        return strip_html(address)[:200]
    return ""


def _update_tax_status(sales_invoice, status):
    """Update the tax_status custom field on Sales Invoice."""
    frappe.db.set_value(
        "Sales Invoice", sales_invoice, "tax_status", status,
        update_modified=False,
    )
    frappe.db.commit()
