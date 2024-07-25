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

