// Copyright (c) 2026, Aakvatech Limited and contributors
// For license information, please see license.txt

// All 10 VFMS API endpoints per API Guide v1.5 (April 2024)
const DEFAULT_ENDPOINTS = [
  {
    endpoint_name: "Normal Sales",
    endpoint_path: "/vfms/api/sales/",
    request_type: "NORMAL_SALES",
    http_method: "POST",
    description: "For normal/walk-in customers day-to-day sales",
  },
  {
    endpoint_name: "B2B Sales",
    endpoint_path: "/vfms/api/btob/sales/",
    request_type: "BTOB_SALES",
    http_method: "POST",
    description: "For ZRA registered customers (B2B taxpayers) with ZRB number",
  },
  {
    endpoint_name: "Institution Sales",
    endpoint_path: "/vfms/api/institution/sales/",
    request_type: "WITHHOLDING_AGENT_SALES",
    http_method: "POST",
    description: "For government institutions / withholding agents",
  },
  {
    endpoint_name: "Check Relief",
    endpoint_path: "/vfms/api/checkReliefSales/",
    request_type: "RELIEF_SALES",
    http_method: "POST",
    description:
      "Verify and check validity of special relief number issued by ZRB",
  },
  {
    endpoint_name: "Save Relief Sales",
    endpoint_path: "/vfms/api/saveReliefSales/",
    request_type: "RELIEF_SALES",
    http_method: "POST",
    description:
      "Issue special relief sales/transaction receipt using validated relief ID",
  },
  {
    endpoint_name: "Get Non-Tax Items",
    endpoint_path: "/vfms/api/getNonTaxItems/",
    request_type: "NON_TAX_ITEMS",
    http_method: "POST",
    description:
      "List all non-taxable (exempted) items per tax laws and regulation",
  },
  {
    endpoint_name: "Seaport Sales",
    endpoint_path: "/vfms/api/seaport/sales/",
    request_type: "SEAPORT_SALES",
    http_method: "POST",
    description:
      "For seaport ticketing agents - local/mainland passenger fiscal receipts",
  },
  {
    endpoint_name: "Seaport Foreign Charge",
    endpoint_path: "/vfms/api/seaport/foreign/",
    request_type: "SEAPORT_FOREIGN_CHARGE",
    http_method: "POST",
    description: "Charge foreign passengers travelling outside Tanzania",
  },
  {
    endpoint_name: "Error Correction",
    endpoint_path: "/vfms/error-management/new",
    request_type: "ERROR_SAVE",
    http_method: "POST",
    description: "Submit error correction for wrongly issued invoices",
  },
  {
    endpoint_name: "Error Correction Report",
    endpoint_path: "/vfms/error-management/errors/",
    request_type: "ERRORS_MANAGEMENTS",
    http_method: "POST",
    description: "Get list of error correction reports by status",
  },
];

frappe.ui.form.on("ZRA Setting", {
  setup: (frm) => {
    frm.clear_table("endpoints");
    DEFAULT_ENDPOINTS.forEach((ep) => {
      let row = frm.add_child("endpoints", ep);
    });
    frm.refresh_field("endpoints");
  },

  refresh: (frm) => {
    if (!frm.doc.__islocal) {
      frm.add_custom_button(
        __("Reset Endpoints to Defaults"),
        function () {
          frappe.confirm(
            __(
              "This will remove all current endpoints and re-populate with the 10 default VFMS endpoints. Continue?"
            ),
            function () {
              frm.call("reset_endpoints").then(() => {
                frm.reload_doc();
              });
            }
          );
        },
        __("Actions")
      );

      frm.add_custom_button(
        __("Fetch Non-Tax Items"),
        function () {
          frm
            .call({
              method: "fetch_non_tax_items",
              doc: frm.doc,
              freeze: true,
              freeze_message: __("Fetching non-taxable items from ZRA..."),
            })
            .then(() => {
              frm.reload_doc();
            });
        },
        __("Actions")
      );
    }
  },
});
