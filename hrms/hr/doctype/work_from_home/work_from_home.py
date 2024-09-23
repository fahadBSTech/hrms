
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
    def validate(self):
        self.half_day_wfh_scenarios()
        self.full_day_wfh_scenarios()

    def half_day_wfh_scenarios(self):
        if not self.half_day:
            conflicting_leaves = frappe.db.sql("""
                        SELECT name FROM `tabLeave Application`
                        WHERE employee = %s AND docstatus = 1
                        AND ((from_date <= %s AND to_date >= %s)  # leave overlaps with WFH
                        OR (from_date = %s AND half_day = 1))     # half-day leave on WFH day
                    """, (self.employee, self.start_date, self.end_date, self.start_date))
            if conflicting_leaves:
                frappe.throw(f"Cannot apply for full-day WFH as there are existing leaves on the same date.")

    def full_day_wfh_scenarios(self):
        if self.half_day and self.half_day_date:
            # Half-day WFH, check if there is any full-day leave on the same day
            conflicting_leaves = frappe.db.sql("""
                        SELECT name FROM `tabLeave Application`
                        WHERE employee = %s AND docstatus = 1
                        AND from_date = %s AND to_date = %s
                        AND (half_day = 0)  # full-day leave on the half-day WFH date
                    """, (self.employee, self.half_day_date, self.half_day_date))
            if conflicting_leaves:
                frappe.throw(f"Cannot apply for half-day WFH as there is a full-day leave on the same day.")
    def before_save(self):
        if self.status == 'Approved' and self.wfh_limit_reached():
            frappe.msgprint(
                    f"Warning: This user has reached or exceeded the 5 days WFH limit for this month",
                    indicator = 'orange',
                title = "WFH Limit Reached")
    def wfh_limit_reached(self):
        total_wfh_days = 0
        if self.employee and self.from_date and self.to_date:
            first_day_of_month = frappe.utils.get_first_day(self.from_date)
            last_day_of_month = frappe.utils.get_last_day(self.from_date)
            total_wfh_days = frappe.db.sql("""
                    SELECT SUM(total_days) FROM `tabWork From Home`
                    WHERE employee = %s AND from_date BETWEEN %s AND %s
                    AND docstatus = 1
                """, (self.employee, first_day_of_month, last_day_of_month))
            total_wfh_days = total_wfh_days[0][0] if total_wfh_days else 0
            frappe.log_error(total_wfh_days + self.total_days)
        return True if total_wfh_days + self.total_days > 5 else False
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
