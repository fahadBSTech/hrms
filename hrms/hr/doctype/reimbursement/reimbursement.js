// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Reimbursement", {
	// refresh: function(frm) {

	// }
	onload: function (frm) {
		if (!frm.doc.employee) {
			// Check if the employee field is empty
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Employee",
					filters: {
						user_id: frappe.session.user,
					},
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("employee", r.message.name); // Set the employee field
					}
				},
			});
		}
	},
});
