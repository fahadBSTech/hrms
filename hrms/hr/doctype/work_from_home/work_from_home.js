// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Work From Home", {
  after_save(frm) {
    // your code here
    if (frm.doc.status === "Requested") {
      // sharing the document with the approvals
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
  }
});

frappe.ui.form.on("Work From Home", "validate", async function (frm) {
  const leaveRes = await frm.call({
    method: "frappe.desk.reportview.get_count",
    args: {
      doctype: "Leave Application",
      filters: [
        [
          "Leave Application",
          "from_date",
          "Between",
          [frm.doc.from_date, frm.doc.to_date]
        ],
        ["Leave Application", "employee", "=", frm.doc.employee]
      ],
      fields: [],
      distinct: false
    }
  });
  if (leaveRes.message > 0) {
    frappe.throw("Already leaves applied for the same dates");
    frappe.validated = false;
  } else if (frm.doc.from_date && frm.doc.from_date < get_today()) {
    frappe.throw("Can't select past date in From Date");
    frappe.validated = false;
  } else if (frm.doc.to_date && frm.doc.to_date < frm.doc.from_date) {
    frappe.throw("To date should be greater than from date");
    frappe.validated = false;
  }
});
