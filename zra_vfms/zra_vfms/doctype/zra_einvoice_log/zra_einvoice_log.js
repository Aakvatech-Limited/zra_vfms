// Copyright (c) 2026, Administrator and contributors
// For license information, please see license.txt

frappe.ui.form.on("ZRA Einvoice Log", {
  refresh(frm) {
    // Called when form is refreshed
    if (frm.doc.__islocal) {
      // Document is new
    } else {
      // Document exists
    }
  },

  validate(frm) {
    // Called before document is saved (client-side validation)
  },

  onload(frm) {
    // Called when form is loaded
  },

  // Field-specific events
  // Example: fieldname: function(frm) { }
});
