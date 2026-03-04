# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ZRATaxInvoice(Document):
	def validate(self):
		self._set_company_from_invoice()

	def _set_company_from_invoice(self):
		"""Auto-set company from the linked Sales Invoice."""
		if self.sales_invoice and not self.company:
			self.company = frappe.db.get_value(
				"Sales Invoice", self.sales_invoice, "company"
			)


def create_tax_invoice(
    sales_invoice,
    company,
    tax_type,
    status="Pending",
    is_cancellation=False,
    is_correction=False,
    receipt_reference=None,
):
    """Create a new ZRA Tax Invoice record.

    Args:
        sales_invoice: Name of the Sales Invoice.
        company: Company name.
        tax_type: "VAT", "Seaport", or "Stamp Duty".
        status: Initial status (default: "Pending").
        is_cancellation: Whether this is a cancellation.
        is_correction: Whether this is a correction (credit note).
        receipt_reference: Original receipt number for corrections.

    Returns:
        ZRA Tax Invoice document.
    """
    tax_inv = frappe.new_doc("ZRA Tax Invoice")
    tax_inv.sales_invoice = sales_invoice
    tax_inv.company = company
    tax_inv.tax_type = tax_type
    tax_inv.status = status
    tax_inv.is_cancellation = is_cancellation
    tax_inv.is_correction = is_correction

    if receipt_reference:
        tax_inv.receipt_reference = receipt_reference

    tax_inv.insert(ignore_permissions=True)
    frappe.db.commit()
    return tax_inv


def update_tax_invoice(
    tax_invoice_name,
    response_data=None,
    status=None,
    error_message=None,
):
    """Update a ZRA Tax Invoice with API response data.

    Args:
        tax_invoice_name: Name of the ZRA Tax Invoice.
        response_data: Dict from VFMS API response.
        status: "Success" or "Failed".
        error_message: Error message on failure.

    Returns:
        Updated ZRA Tax Invoice document.
    """
    tax_inv = frappe.get_doc("ZRA Tax Invoice", tax_invoice_name)

    if status:
        tax_inv.status = status

    if error_message is not None:
        tax_inv.error_message = error_message

    if response_data:
        # Sales endpoints return receiptNumber; Error Correction does not
        tax_inv.receipt_number = response_data.get("receiptNumber") or ""

        # issueDate format: "2022-08-12T15:14:16.197+03:00"
        receipt_time = response_data.get("issueDate")
        if receipt_time:
            tax_inv.receipt_time = receipt_time

        # VFMS does not return QR/verify URLs in the response;
        # per API Guide v1.5 note: QR code should be generated
        # client-side using the receipt number.
        tax_inv.qr_code_url = ""
        tax_inv.verify_url = ""

    tax_inv.save(ignore_permissions=True)
    frappe.db.commit()
    return tax_inv


def get_tax_invoice(sales_invoice, tax_type=None):
    """Get existing ZRA Tax Invoice for a Sales Invoice.

    Args:
        sales_invoice: Name of the Sales Invoice.
        tax_type: Optional tax type filter.

    Returns:
        ZRA Tax Invoice document or None.
    """
    filters = {"sales_invoice": sales_invoice}
    if tax_type:
        filters["tax_type"] = tax_type

    name = frappe.db.get_value("ZRA Tax Invoice", filters)
    if name:
        return frappe.get_doc("ZRA Tax Invoice", name)
    return None
