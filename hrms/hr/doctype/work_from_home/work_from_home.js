// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Work From Home", {
    after_save(frm) {
        // Perform actions after saving the document
        if (frm.doc.status === "Requested") {
            // Sharing the document with the approver
            const users = [
                {
                    user: frm.doc.approver_id,
                    read: 1,
                    write: 1,
                    submit: 1,
                    share: 1
                }
            ];
            for (const user of users) {
                frm.call({
                    method: "frappe.share.add",
                    args: {
                        doctype: "Work From Home",
                        name: frm.doc.name,
                        user: user.user,
                        read: user.read,
                        write: user.write,
                        submit: user.submit,
                        share: user.share,
                        everyone: 0,
                        notify: 1
                    }
                });
            }
        }
    },

    validate_half_day_date(frm) {
        // If half_day is checked and from_date is not equal to to_date
        if (frm.doc.half_day && frm.doc.from_date !== frm.doc.to_date && !frm.doc.half_day_date) {
            frappe.msgprint(__('Please select a Half Day Date since Half Day is selected and From Date is different from To Date.'));
            frappe.validated = false;
        }
    },

    validate(frm) {
        frm.trigger('validate_half_day_date');
    },

    to_date_datepicker: function (frm) {
		const to_date_datepicker = frm.fields_dict.to_date.datepicker;
		to_date_datepicker.update({
			minDate: frappe.datetime.str_to_obj(frm.doc.from_date),
		});
	},


    half_day_datepicker: function (frm) {
		frm.set_value("half_day_date", "");
		if (!(frm.doc.half_day && frm.doc.from_date && frm.doc.to_date)) return;

		const half_day_datepicker = frm.fields_dict.half_day_date.datepicker;
		half_day_datepicker.update({
			minDate: frappe.datetime.str_to_obj(frm.doc.from_date),
			maxDate: frappe.datetime.str_to_obj(frm.doc.to_date),
		});
	},
    onload: function(frm) {
        if (!frm.doc.employee) { // Check if the employee field is empty
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Employee",
                    filters: {
                        "user_id": frappe.session.user
                    }
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('employee', r.message.name); // Set the employee field
                    }
                }
            });
        }
    },
    // Trigger to calculate total days when from_date changes
    from_date(frm) {
        frm.trigger('calculate_total_days');
        frm.trigger("half_day_datepicker");
        frm.trigger("to_date_datepicker");


        if (frm.doc.from_date) {
            frm.fields_dict.to_date.$input.datepicker("option", "minDate", frm.doc.from_date);
            frm.fields_dict.to_date.$input.datepicker("option", "defaultDate", frm.doc.from_date);
        }
    },
    validate: function (frm) {
		if (frm.doc.from_date === frm.doc.to_date && cint(frm.doc.half_day)) {
			frm.doc.half_day_date = frm.doc.from_date;
		} else if (frm.doc.half_day === 0) {
			frm.doc.half_day_date = "";
		}
		frm.toggle_reqd("half_day_date", cint(frm.doc.half_day));
	},

    // Trigger to calculate total days when to_date changes
    to_date(frm) {
        frm.trigger('calculate_total_days');
        frm.trigger("half_day_datepicker");

    },

    // Trigger to calculate total days when half_day is toggled
    half_day(frm) {
        frm.trigger('calculate_total_days');
    },

    half_day_date(frm) {
        frm.trigger('calculate_total_days');
    },
    half_day: function (frm) {
		if (frm.doc.half_day) {
			if (frm.doc.from_date == frm.doc.to_date) {
				frm.set_value("half_day_date", frm.doc.from_date);
			} else {
				frm.trigger("half_day_datepicker");
			}
		} else {
			frm.set_value("half_day_date", "");
		}
		frm.trigger("calculate_total_days");
	},
    // Function to calculate total days
    calculate_total_days(frm) {
        if (frm.doc.from_date && frm.doc.to_date) {
            // Server call to calculate total WFH days including holidays and half days
            return frappe.call({
                method: "hrms.hr.doctype.work_from_home.work_from_home.get_number_of_wfh_days",
                args: {
                    from_date: frm.doc.from_date,
                    to_date: frm.doc.to_date,
                    half_day: frm.doc.half_day,
                    half_day_date: frm.doc.half_day_date,
                    holiday_list: frm.doc.holiday_list,
                },
                callback: function (r) {
                    if (r && r.message) {
                        frm.set_value("total_days", r.message);
                    }
                },
            });
        }
    }
});
