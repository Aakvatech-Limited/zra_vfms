# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

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

    # Return invoices (credit notes) are not auto-sent;
    # Error Correction requires a replacement receipt and must be
    # triggered manually via the Send Tax button.
    if doc.get("is_return"):
        return

    setting = get_zra_setting(doc.company)
    if not setting:
        return

    if not setting.auto_send_tax:
        return

    if setting.zra_start_date and getdate(doc.posting_date) < getdate(setting.zra_start_date):
        return

    # Process synchronously so the submit waits for the ZRA response
    process_tax_submission(doc.name)


@frappe.whitelist()
def send_tax(sales_invoice: str):
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
        frappe.throw(_(f"No ZRA Setting found for company {sinv.company}. Please create one in ZRA Setting."))

    if setting.zra_start_date and getdate(sinv.posting_date) < getdate(setting.zra_start_date):
        frappe.throw(
            _(f"Cannot send tax for invoices before ZRA start date <b>{setting.zra_start_date}</b>.")
        )

    # Check if already sent successfully
    existing = get_tax_invoice(sinv.name)
    if existing and existing.status == "Success":
        frappe.throw(
            _(
                f"Tax has already been sent successfully for this invoice. "
                f"Receipt Number: {existing.receipt_number}"
            )
        )

    # Process synchronously for manual send
    return process_tax_submission(sinv.name)


def send_all_tax_invoices():
    """Send tax to ZRA for all pending/failed Sales Invoices.

    Scheduled task (every 15 minutes) that runs as a single background
    job and processes invoices sequentially in one pass:
    1. Finds all submitted, taxable Sales Invoices with tax_status
       in ('Not Sent', 'Failed') or NULL
    2. Filters by companies that have an active ZRA Setting
    3. Processes each invoice directly (no per-invoice enqueue)

    Invoices are processed oldest-first to maintain chronological order.
    Each invoice is committed independently so a failure in one does not
    roll back others.

    Uses a cache lock to prevent overlapping runs when a job exceeds
    the 15-minute scheduler interval.
    """
    lock_key = "zra_vfms_bulk_send_tax_running"

    # Check if another run is already in progress
    if frappe.cache.get_value(lock_key):
        frappe.log_error(
            title="ZRA VFMS Bulk Send: Skipped",
            message="Previous run still in progress",
        )
        return

    try:
        # Acquire lock with 30-minute expiry as safety net
        frappe.cache.set_value(lock_key, True, expires_in_sec=1800)

        _process_bulk_tax_invoices()

    finally:
        # Always release the lock when done
        frappe.cache.delete_value(lock_key)


def _process_bulk_tax_invoices():
    """Internal: Process all eligible invoices for bulk tax submission."""
    # Get companies with active ZRA Settings
    zra_companies = frappe.get_all(
        "ZRA Setting",
        filters={"docstatus": 0},
        pluck="company",
    )

    if not zra_companies:
        return

    # Find all submitted invoices that need tax sending
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "company": ["in", zra_companies],
            "is_non_taxable": 0,
            "is_return": 0,
            "tax_status": ["in", ["Not Sent", "Failed", "", None]],
        },
        fields=["name", "company", "posting_date"],
        order_by="posting_date asc, creation asc",
    )

    if not invoices:
        return

    # Filter invoices by zra_start_date per company
    settings_cache = {}
    eligible = []

    for inv in invoices:
        if inv.company not in settings_cache:
            settings_cache[inv.company] = get_zra_setting(inv.company)

        setting = settings_cache[inv.company]
        if not setting:
            continue

        if setting.zra_start_date and getdate(inv.posting_date) < getdate(setting.zra_start_date):
            continue

        eligible.append(inv)

    if not eligible:
        return

    success_count = 0
    fail_count = 0

    for inv in eligible:
        try:
            result = process_tax_submission(inv.name)
            if result and result.get("success"):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            fail_count += 1

            traceback = frappe.get_traceback()
            msg = f"ZRA VFMS: Bulk tax failed for {inv.name} <br><br>\n{e!s} <br><br>\n{traceback}"
            frappe.log_error(
                title=f"ZRA VFMS: Bulk tax failed for {inv.name}",
                message=msg,
                reference_doctype="Sales Invoice",
                reference_name=inv.name,
            )


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
        _update_tax_status(sinv.name, "Pending")
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
        status="Failed",
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

        receipt_number = (result["response"] or {}).get("receiptNumber", "")
        return {
            "success": True,
            "message": _(f"Tax sent successfully. Receipt: {receipt_number}"),
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
            reference_doctype="Sales Invoice",
            reference_name=sinv.name,
        )
        frappe.db.commit()  # nosemgrep

        msg = _(f"Tax submission failed: <br><br>Message: <b>{result.get('error')}</b>")
        frappe.throw(msg)


def _determine_tax_type_and_endpoint(sinv):
    """Determine the tax type and VFMS endpoint for a Sales Invoice.

    Routing logic per VFMS API Guide v1.5:
    - Return invoices (credit notes) → Error Correction (Section 3.9)
    - relief_number is set and verified → Check Relief / Save Relief Sales
    - tax_id present + customer_group == 'Government' → Institution Sales
    - tax_id present + customer_group != 'Government' → B2B Sales
    - Default walk-in customer → Normal Sales (Section 3.1)

    Returns:
        Tuple of (tax_type, endpoint_name).
    """
    tax_type = "VAT"

    if sinv.is_return:
        return tax_type, "Error Correction"

    # Relief Sales: if relief_number is filled and verified
    if sinv.get("relief_number"):
        if not sinv.get("relief_id"):
            frappe.throw(
                _("Relief number must be verified before sending tax. " "Click 'Verify Relief Number' first.")
            )
        return tax_type, "Save Relief Sales"

    if sinv.tax_id:
        # Fetch customer group to distinguish B2B vs Institution
        customer_group = frappe.db.get_value("Customer", sinv.customer, "customer_group")
        if customer_group == "Government":
            return tax_type, "Institution Sales"

        return tax_type, "B2B Sales"

    return tax_type, "Normal Sales"


def _build_request_payload(sinv, setting, endpoint_name):
    """Build the VFMS API request payload from Sales Invoice data.

    Delegates to specialised builders based on endpoint type.
    """
    if endpoint_name == "Error Correction":
        return _build_error_correction_payload(sinv, setting)

    if endpoint_name == "Save Relief Sales":
        return _build_save_relief_payload(sinv)

    return _build_sales_payload(sinv, endpoint_name)


def _build_sales_payload(sinv, endpoint_name):
    """Build a sales request payload for Normal, B2B, or Institution Sales.

    Per VFMS API Guide v1.5 Sections 3.1, 3.2, 3.3:

    Normal Sales request:
        phoneNumber, referenceNumber, salesCurrency, salesCustomer,
        salesItems[]

    B2B / Institution Sales request:
        phoneNumber, referenceNumber, salesCurrency, salesItems[],
        zrbnumber  (replaces salesCustomer)

    salesItems[] per item:
        itemId  — 0 for taxable; VFMS non-tax ID for exempt items
        itemName, price (tax-inclusive selling price), quantity, discount

    IMPORTANT: VFMS calculates taxes from the submitted prices.
    We do NOT send tax codes, rates, or amounts in the request.
    The ``price`` field must be the tax-inclusive selling price per
    unit, because VFMS back-calculates tax-exclusive and tax amounts.
    """
    payload = {
        "phoneNumber": _get_customer_phone(sinv),
        "referenceNumber": sinv.name,
        "salesCurrency": sinv.currency,
        "salesItems": _build_sales_items(sinv),
    }

    if endpoint_name in ("B2B Sales", "Institution Sales"):
        # B2B / Institution: identify buyer by ZRB number
        payload["zrbnumber"] = sinv.tax_id or ""
    else:
        # Normal Sales: identify buyer by name
        payload["salesCustomer"] = sinv.customer_name or sinv.customer or ""

    return payload


def _build_error_correction_payload(sinv, setting):
    """Build an Error Correction request payload.

    Per VFMS API Guide v1.5 Section 3.9:
        b_unit_name, email, new_receipt_number, old_receipt_number,
        phone_no, reasons, unitId, zrb_number

    Error Correction voids a wrong receipt and links it to a
    corrected replacement receipt.  Both receipt numbers must exist
    before this request can be sent.

    For credit notes (return invoices) in ERPNext:
    - old_receipt_number = receipt of the original invoice
    - new_receipt_number = receipt of the amended/replacement invoice
    """
    old_receipt_number = ""
    new_receipt_number = ""

    if sinv.return_against:
        # Get the receipt of the original (wrong) invoice
        old_receipt_number = (
            frappe.db.get_value(
                "ZRA Tax Invoice",
                {"sales_invoice": sinv.return_against, "status": "Success"},
                "receipt_number",
            )
            or ""
        )

        # Find the amended/replacement invoice and its receipt
        amended_name = frappe.db.get_value(
            "Sales Invoice",
            {"amended_from": sinv.return_against, "docstatus": 1},
            "name",
        )
        if amended_name:
            new_receipt_number = (
                frappe.db.get_value(
                    "ZRA Tax Invoice",
                    {"sales_invoice": amended_name, "status": "Success"},
                    "receipt_number",
                )
                or ""
            )

    if not old_receipt_number:
        frappe.throw(
            _(
                "Cannot send Error Correction: original invoice has no "
                "successful ZRA receipt.  Send the original invoice first."
            )
        )

    if not new_receipt_number:
        frappe.throw(
            _(
                "Cannot send Error Correction: no replacement invoice with "
                "a successful ZRA receipt was found.  Submit and send the "
                "amended invoice to ZRA first."
            )
        )

    return {
        "b_unit_name": setting.business_name or "",
        "email": setting.contact_email or "",
        "new_receipt_number": new_receipt_number,
        "old_receipt_number": old_receipt_number,
        "phone_no": setting.contact_phone or "",
        "reasons": sinv.remarks or "Error Correction",
        "unitId": int(setting.unit_id) if setting.unit_id else 0,
        "zrb_number": setting.zrb_number or "",
    }


def _build_save_relief_payload(sinv):
    """Build a Save Relief Sales request payload.

    Per VFMS API Guide v1.5 Section 3.5:
    The request only requires the reliefId (long) obtained from the
    Check Relief endpoint (Section 3.4).  VFMS returns the full
    receipt with salesItems, taxAmount, etc. in the response.
    """
    relief_id = sinv.get("relief_id")
    if not relief_id:
        frappe.throw(_("Relief ID is missing. Verify the relief number first."))

    return {
        "reliefId": int(relief_id),
    }


@frappe.whitelist()
def verify_relief_number(sales_invoice: str):
    """Verify a special relief number against ZRA (Check Relief endpoint).

    Per VFMS API Guide v1.5 Section 3.4:
    Request:  {"reliefnumber": "22081303"}
    Response: {reliefId, reliefNumber, customer, isValid, items[], ...}

    On success, stores the reliefId on the Sales Invoice for later use
    by Save Relief Sales.
    """
    sinv = frappe.get_doc("Sales Invoice", sales_invoice)

    relief_number = sinv.get("relief_number")
    if not relief_number:
        frappe.throw(_("Please enter a relief number first."))

    setting = get_zra_setting(sinv.company)
    if not setting:
        frappe.throw(_(f"No ZRA Setting found for company {sinv.company}."))

    payload = {"reliefnumber": relief_number}

    result = send_request(setting, "Check Relief", payload, "VAT")

    if result["success"]:
        response = result["response"] or {}

        if not response.get("isValid"):
            frappe.throw(_("Relief number <b>{0}</b> is not valid or has expired.").format(relief_number))

        relief_id = response.get("reliefId")
        if not relief_id:
            frappe.throw(_("ZRA returned no Relief ID for this relief number."))

        # Store relief_id (its presence proves verification)
        frappe.db.set_value(
            "Sales Invoice",
            sinv.name,
            "relief_id",
            str(relief_id),
            update_modified=False,
        )
        frappe.db.commit()  # nosemgrep

        return {
            "success": True,
            "message": _(
                "Relief number verified successfully. " "Customer: {0}, Amount Relieved: {1}"
            ).format(
                response.get("customer", ""),
                response.get("amountRevield", 0),
            ),
            "relief_id": relief_id,
        }
    else:
        frappe.throw(_("Relief verification failed: {0}").format(result["error"]))


def _build_sales_items(sinv):
    """Build the salesItems array per VFMS API Guide v1.5.

    Each item has:
        itemId    — 0 for taxable items (VFMS applies registered tax rate);
                    for non-taxable (exempt) items, use the item ID from the
                    VFMS Non-Tax Items list (getNonTaxItems endpoint).
        itemName  — item/service description (max 200 chars)
        price     — tax-inclusive unit selling price
        quantity  — number of units
        discount  — total line discount amount (tax-inclusive)

    Note: Non-taxable item ID mapping is not yet implemented;
    all items default to itemId=0 (taxable).
    """
    items = []
    for item in sinv.items:
        items.append(
            {
                "itemId": 0,
                "itemName": (item.item_name or item.description or "")[:200],
                "price": _get_item_selling_price(item, sinv),
                "quantity": float(item.qty),
                "discount": 0.0,
            }
        )
    return items


def _get_item_selling_price(item, sinv):
    """Return the tax-inclusive selling price per unit.

    VFMS always treats the submitted ``price`` as tax-inclusive and
    back-calculates the tax-exclusive amount and tax:

        tax_exclusive = price × qty / (1 + rate)
        tax_amount    = price × qty − tax_exclusive

    So we must ensure the price includes tax.

    - If tax is **included in rate** (``included_in_print_rate``),
      ``item.rate`` already contains tax → use directly.
    - If tax is **on net total** (not included), ``item.rate`` is the
      net price → gross it up using grand_total / net_total.
    """
    if not sinv.taxes:
        return round(float(item.rate), 2)

    # When any tax row has included_in_print_rate, ERPNext stores the
    # tax-inclusive rate in item.rate.
    if any(tax.included_in_print_rate for tax in sinv.taxes):
        return round(float(item.rate), 2)

    # Tax not included in rate — gross up proportionally.
    # grand_total / net_total gives the effective (1 + tax_rate) factor.
    if sinv.net_total:
        gross_factor = float(sinv.grand_total) / float(sinv.net_total)
        return round(float(item.rate) * gross_factor, 2)

    return round(float(item.rate), 2)


def _get_customer_phone(sinv):
    """Get customer mobile/phone from the invoice contact fields."""
    phone_number = sinv.get("contact_mobile") or sinv.get("contact_phone") or ""
    if not phone_number:
        phone_number = frappe.db.get_value("Customer", sinv.customer, "mobile_no") or ""

    if not phone_number:
        frappe.throw(
            _(
                f"No contact phone number found for customer: {sinv.customer}, please enter a phone number in the invoice or customer record."
            )
        )

    return phone_number


def _update_tax_status(sales_invoice, status):
    """Update the tax_status custom field on Sales Invoice."""
    frappe.db.set_value(
        "Sales Invoice",
        sales_invoice,
        "tax_status",
        status,
        update_modified=False,
    )
    frappe.db.commit()  # nosemgrep
