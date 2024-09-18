
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# import json
import frappe
from frappe.model.document import Document
import datetime


@frappe.whitelist()
def get_number_of_wfh_days(
        employee: str,
        from_date: datetime.date,
        to_date: datetime.date,
        half_day: int | str | None = None,
        half_day_date: datetime.date | str | None = None
) -> float:
    from frappe.utils import cint, add_days, date_diff, getdate
    """Returns number of leave days between 2 dates after considering half day and holidays
    (Based on the include_holiday setting in Leave Type)"""
    number_of_days = 0
    if cint(half_day) == 1:
        if getdate(from_date) == getdate(to_date):
            number_of_days = 0.5
        elif half_day_date and getdate(from_date) <= getdate(half_day_date) <= getdate(to_date):
            number_of_days = date_diff(to_date, from_date) + 0.5
        else:
            number_of_days = date_diff(to_date, from_date) + 1
    else:
        number_of_days = date_diff(to_date, from_date) + 1
    return number_of_days



class WorkFromHome(Document):
    def before_submit(self):
        if self.status != 'Approved' and self.status != 'Rejected':
            frappe.throw("Only document with status 'Approved' or 'Rejected' can be submitable.")

    def after_insert(self):
        try:
            if self.status == 'Requested':
                parent_doc = frappe.get_doc("Work From Home", self.name)
                args = parent_doc.as_dict()
                email_template = frappe.get_doc("Email Template", "WFH Request Template")
                message_res = frappe.render_template(email_template.response, args)
                sender_email = frappe.get_doc("User", frappe.session.user).email
                try:
                    frappe.sendmail(
                        recipients=self.approver_id,
                        cc=self.team_lead_id,
                        sender=sender_email,
                        subject=email_template.subject,
                        message=message_res
                    )
                    frappe.msgprint(
                        ("Email sent to HR <b>%s</b> and the lead <b>%s</b>") % (self.approver_id, self.team_lead_id))
                except frappe.OutgoingEmailError:
                    pass
        except Exception as e:
            frappe.msgprint('Something went wrong! \n %s' % (str(e)))
