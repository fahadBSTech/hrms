# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# import json
import frappe
from frappe.model.document import Document
from frappe.integrations.utils import make_post_request

# def make_slack_message_attachment(self):
# 	return """[
# 		{
# 			"color": "#f2c744",
# 			"blocks": [
# 				{
# 					"type": "header",
# 					"text": {
# 						"type": "plain_text",
# 						"text": "Leave Approval Request",
# 						"emoji": True
# 					}
# 				},
# 				{
# 					"type": "context",
# 					"elements": [
# 						{
# 							"type": "plain_text",
# 							"text": "Muhammad Fahad",
# 							"emoji": True
# 						}
# 					]
# 				},
# 				{
# 					"type": "divider"
# 				},
# 				{
# 					"type": "section",
# 					"fields": [
# 						{
# 							"type": "mrkdwn",
# 							"text": "*From Date:*\n%s"
# 						},
# 						{
# 							"type": "mrkdwn",
# 							"text": "*To Date:*\n%s"
# 						}
# 					]
# 				},
# 				{
# 					"type": "actions",
# 					"elements": [
# 						{
# 							"type": "button",
# 							"text": {
# 								"type": "plain_text",
# 								"emoji": True,
# 								"text": "Approve"
# 							},
# 							"style": "primary",
# 							"value": "click_me_123"
# 						},
# 						{
# 							"type": "button",
# 							"text": {
# 								"type": "plain_text",
# 								"emoji": True,
# 								"text": "Reject"
# 							},
# 							"style": "danger",
# 							"value": "click_me_123"
# 						}
# 					]
# 				}
# 			]
# 		}
# 	]""" % (frappe.utils.formatdate(self.from_date, "dd, MMMM YYYY"), frappe.utils.formatdate(self.to_date, "dd, MMMM YYYY"))

# def make_slack_message_paylaod(self):
# 	return {
# 			"channel": "U03C4B40G94",
# 			"text": "Hi, <@U03C4B40G94> you have applide for the work from home",
# 			"attachments": json.loads(make_slack_message_attachment(self))
# 	}

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
				# try:
				# 	frappe.msgprint("Slack Message Payload: \n %s" % (str(make_slack_message_paylaod(self))))
				# 	slack_respone = make_post_request('https://slack.com/api/chat.postMessage',
		    #    headers={'Authorization': 'Bearer xoxb-292309334836-5588859041094-OBql6ELHm3T9rnTs7ROJaWwT'},
				# 	 data=make_slack_message_paylaod(self)
				# 	)
				# 	frappe.msgprint("Slack Message Res: \n %s" % (str(slack_respone)))
				# except Exception as e:
				# 	frappe.msgprint("Getting issue while sending slack message :\n %s" % (str(e)))
		except Exception as e:
			frappe.msgprint('Something went wrong! \n %s' % (str(e)))
