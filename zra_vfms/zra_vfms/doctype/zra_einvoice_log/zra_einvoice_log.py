# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document


class ZRAEinvoiceLog(Document):
	pass


def create_log(
    sales_invoice,
    request_type,
    request_payload=None,
    zra_tax_invoice=None,
    status="Pending",
):
    """Create a new ZRA Einvoice Log entry.

    This is a reusable utility that can be called from any module
    that needs to log VFMS API interactions.

    Args:
        sales_invoice: Name of the Sales Invoice.
        request_type: Endpoint name (e.g., "Normal Sales", "B2B Sales").
        request_payload: Dict of the API request body.
        zra_tax_invoice: Name of linked ZRA Tax Invoice (optional).
        status: Initial status (default: "Pending").

    Returns:
        ZRA Einvoice Log document.
    """
    log = frappe.new_doc("ZRA Einvoice Log")
    log.sales_invoice = sales_invoice
    log.request_type = request_type
    log.status = status
    log.zra_tax_invoice = zra_tax_invoice

    if request_payload:
        log.request_payload = json.dumps(request_payload, indent=2)

    log.insert(ignore_permissions=True)
    frappe.db.commit()
    return log


def update_log(log_name, response_payload=None, status=None, error_message=None):
    """Update an existing ZRA Einvoice Log entry.

    Args:
        log_name: Name of the ZRA Einvoice Log.
        response_payload: Dict of the API response body.
        status: New status ("Success" or "Failed").
        error_message: Error message on failure.

    Returns:
        Updated ZRA Einvoice Log document.
    """
    log = frappe.get_doc("ZRA Einvoice Log", log_name)

    if response_payload:
        log.response_payload = json.dumps(response_payload, indent=2)
    if status:
        log.status = status
    if error_message:
        log.error_message = error_message

    log.save(ignore_permissions=True)
    frappe.db.commit()
    return log


def increment_retry(log_name):
    """Increment the retry count on an Einvoice Log entry.

    Args:
        log_name: Name of the ZRA Einvoice Log.
    """
    current = frappe.db.get_value("ZRA Einvoice Log", log_name, "retry_count") or 0
    frappe.db.set_value(
        "ZRA Einvoice Log", log_name, "retry_count", current + 1,
        update_modified=False,
    )
    frappe.db.commit()
