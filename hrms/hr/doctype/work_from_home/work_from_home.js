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

    // Trigger to calculate total days when from_date changes
    from_date(frm) {
        frm.trigger('calculate_total_days');
    },

    // Trigger to calculate total days when to_date changes
    to_date(frm) {
        frm.trigger('calculate_total_days');
    },

    // Trigger to calculate total days when half_day is toggled
    half_day(frm) {
        frm.trigger('calculate_total_days');
    },

    // Function to calculate total days
    calculate_total_days(frm) {
        if (frm.doc.from_date && frm.doc.to_date && frm.doc.employee) {
            // Server call to calculate total WFH days including holidays and half days
            return frappe.call({
                method: "hrms.hr.doctype.work_from_home.work_from_home.get_number_of_wfh_days",
                args: {
                    employee: frm.doc.employee,
                    from_date: frm.doc.from_date,
                    to_date: frm.doc.to_date,
                    half_day: frm.doc.half_day,
                    half_day_date: frm.doc.half_day_date,
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
