// Copyright (c) 2026, Aakvatech Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Invoice", {
  refresh(frm) {
    zra_vfms_update_tax_status_indicator(frm);
    zra_vfms_toggle_relief_fields(frm);
  },

  relief_number(frm) {
    // Reset verification when relief number changes
    if (frm.doc.relief_id) {
      frm.set_value("relief_id", "");
    }
    zra_vfms_toggle_relief_fields(frm);
  },

  verify_relief_number(frm) {
    if (!frm.doc.relief_number) {
      frappe.msgprint(__("Please enter a relief number first."));
      return;
    }

    frappe.call({
      method: "zra_vfms.api.sales_invoice.verify_relief_number",
      args: {
        sales_invoice: frm.doc.name,
      },
      freeze: true,
      freeze_message: __("Verifying relief number with ZRA..."),
      callback: function (r) {
        if (r.message && r.message.success) {
          frappe.show_alert({
            message: __(r.message.message),
            indicator: "green",
          });
          frm.reload_doc();
        }
      },
    });
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
  },
});

/**
 * Show/hide relief-related fields based on current state.
 */
function zra_vfms_toggle_relief_fields(frm) {
  const has_relief = !!frm.doc.relief_number;
  const is_verified = !!frm.doc.relief_id;

  // Show verify button only when relief_number is filled and not yet verified
  frm.toggle_display("verify_relief_number", has_relief && !is_verified);

  // Show a verified indicator
  if (has_relief && is_verified && frm.fields_dict.relief_number) {
    frm.fields_dict.relief_number.set_description(
      '<span style="color: green;">&#10003; Verified</span>'
    );
  } else if (frm.fields_dict.relief_number) {
    frm.fields_dict.relief_number.set_description("");
  }
}
function zra_vfms_update_tax_status_indicator(frm) {
  if (!frm.doc.tax_status) return;

  let color = "grey";
  switch (frm.doc.tax_status) {
    case "Not Sent":
      color = "orange";
      break;
    case "Pending":
      color = "yellow";
      break;
    case "Success":
      color = "green";
      break;
    case "Failed":
      color = "red";
      break;
  }

  frm.fields_dict.tax_status &&
    frm.fields_dict.tax_status.$wrapper
      .find(".control-value, .like-disabled-input")
      .css("color", color);
}
