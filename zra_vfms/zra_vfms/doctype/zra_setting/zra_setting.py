# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# All 10 VFMS API endpoints per API Guide v1.5 (April 2024)
DEFAULT_ENDPOINTS = [
    {
        "endpoint_name": "Normal Sales",
        "endpoint_path": "/vfms/api/sales/",
        "request_type": "NORMAL_SALES",
        "http_method": "POST",
        "description": "For normal/walk-in customers day-to-day sales",
    },
    {
        "endpoint_name": "B2B Sales",
        "endpoint_path": "/vfms/api/btob/sales/",
        "request_type": "BTOB_SALES",
        "http_method": "POST",
        "description": "For ZRA registered customers (B2B taxpayers) with ZRB number",
    },
    {
        "endpoint_name": "Institution Sales",
        "endpoint_path": "/vfms/api/institution/sales/",
        "request_type": "WITHHOLDING_AGENT_SALES",
        "http_method": "POST",
        "description": "For government institutions / withholding agents",
    },
    {
        "endpoint_name": "Check Relief",
        "endpoint_path": "/vfms/api/checkReliefSales/",
        "request_type": "RELIEF_SALES",
        "http_method": "POST",
        "description": "Verify and check validity of special relief number issued by ZRB",
    },
    {
        "endpoint_name": "Save Relief Sales",
        "endpoint_path": "/vfms/api/saveReliefSales/",
        "request_type": "RELIEF_SALES",
        "http_method": "POST",
        "description": "Issue special relief sales/transaction receipt using validated relief ID",
    },
    {
        "endpoint_name": "Get Non-Tax Items",
        "endpoint_path": "/vfms/api/getNonTaxItems/",
        "request_type": "NON_TAX_ITEMS",
        "http_method": "POST",
        "description": "List all non-taxable (exempted) items per tax laws and regulation",
    },
    {
        "endpoint_name": "Seaport Sales",
        "endpoint_path": "/vfms/api/seaport/sales/",
        "request_type": "SEAPORT_SALES",
        "http_method": "POST",
        "description": "For seaport ticketing agents - local/mainland passenger fiscal receipts",
    },
    {
        "endpoint_name": "Seaport Foreign Charge",
        "endpoint_path": "/vfms/api/seaport/foreign/",
        "request_type": "SEAPORT_FOREIGN_CHARGE",
        "http_method": "POST",
        "description": "Charge foreign passengers travelling outside Tanzania",
    },
    {
        "endpoint_name": "Error Correction",
        "endpoint_path": "/vfms/error-management/new",
        "request_type": "ERROR_SAVE",
        "http_method": "POST",
        "description": "Submit error correction for wrongly issued invoices",
    },
    {
        "endpoint_name": "Error Correction Report",
        "endpoint_path": "/vfms/error-management/errors/",
        "request_type": "ERRORS_MANAGEMENTS",
        "http_method": "POST",
        "description": "Get list of error correction reports by status",
    },
]


class ZRASetting(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        base_url: DF.Data
        business_name: DF.Data | None
        company: DF.Link
        contact_email: DF.Data | None
        contact_phone: DF.Data | None
        credentials: DF.Table[ZRACredential]
        endpoints: DF.Table[ZRAEndpoint]
        tin_number: DF.Data | None
        unit_id: DF.Data | None
        vrn_number: DF.Data | None
        zrb_number: DF.Data | None
    # end: auto-generated types

    def validate(self):
        self._validate_unique_tax_types()
        self._validate_unique_endpoint_names()

    def _populate_default_endpoints(self):
        """Add all default VFMS endpoints to the endpoints child table."""
        for ep in DEFAULT_ENDPOINTS:
            self.append("endpoints", ep)

    def _validate_unique_tax_types(self):
        """Ensure no duplicate tax types in credentials."""
        seen = set()
        for row in self.credentials:
            if row.tax_type in seen:
                frappe.throw(
                    f"Duplicate tax type <b>{row.tax_type}</b> in credentials. "
                    "Each tax type should appear only once."
                )
            seen.add(row.tax_type)

    def _validate_unique_endpoint_names(self):
        """Ensure no duplicate endpoint names."""
        seen = set()
        for row in self.endpoints:
            if row.endpoint_name in seen:
                frappe.throw(
                    f"Duplicate endpoint <b>{row.endpoint_name}</b>. "
                    "Each endpoint should appear only once."
                )
            seen.add(row.endpoint_name)

    @frappe.whitelist()
    def reset_endpoints(self):
        """Reset endpoints to defaults. Can be called from a button on the form."""
        self.endpoints = []
        self._populate_default_endpoints()
        self.save()
        frappe.msgprint(_("Endpoints have been reset to defaults."), alert=True)
