# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WorkFromHome(Document):
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
					frappe.msgprint(("Email sent to HR <b>%s</b> and the lead <b>%s</b>") % (self.approver_id, self.team_lead_id))
				except frappe.OutgoingEmailError:
					pass
		except:
			frappe.msgprint('Something went wrong!')
