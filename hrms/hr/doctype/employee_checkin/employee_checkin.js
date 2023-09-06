// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Checkin", "validate", frm => {
  try {
    const checkTime = new Date(frm.doc.time).getTime();
    const currentTime = new Date().getTime();
    if (checkTime > currentTime) {
      frappe.throw(
        `Check-${frm.doc.log_type.toLowerCase()} cannot be set for future.`
      );
      frappe.validated = false;
    }
  } catch (error) {
    frappe.throw(error);
  }
});
