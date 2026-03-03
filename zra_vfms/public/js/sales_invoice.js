// Copyright (c) 2026, Aakvatech Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Invoice", {
  refresh(frm) {
    zra_vfms_update_tax_status_indicator(frm);
  },

  send_tax(frm) {
    if (frm.doc.docstatus !== 1) {
      frappe.msgprint(__("Please submit the invoice first."));
      return;
    }

    if (frm.doc.is_non_taxable) {
      frappe.msgprint(__("This invoice is marked as non-taxable."));
      return;
    }

    frappe.confirm(__("Send this invoice to ZRA Tax Authority?"), function () {
      frappe.call({
        method: "zra_vfms.api.sales_invoice.send_tax",
        args: {
          sales_invoice: frm.doc.name,
        },
        freeze: true,
        freeze_message: __("Sending to ZRA..."),
        callback: function (r) {
          if (r.message) {
            if (r.message.success) {
              frappe.show_alert({
                message: __(r.message.message),
                indicator: "green",
              });
            } else {
              frappe.show_alert({
                message: __(r.message.message),
                indicator: "red",
              });
            }
            frm.reload_doc();
          }
        },
      });
    });
  },
});

/**
 * Update the visual indicator for tax_status field.
 * Changes the field description colour based on current status.
 */
function zra_vfms_update_tax_status_indicator(frm) {
  if (!frm.doc.tax_status) return;

  const status_colors = {
    "Not Sent": "orange",
    Pending: "yellow",
    Success: "green",
    Failed: "red",
  };

  const color = status_colors[frm.doc.tax_status] || "grey";

  frm.fields_dict.tax_status &&
    frm.fields_dict.tax_status.$wrapper
      .find(".control-value, .like-disabled-input")
      .css("color", color);
}
