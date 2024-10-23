# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Reimbursement(Document):
	def on_submit(self):
		if self.reimbursement_type == "Medical":
			claim_employee = frappe.get_doc("Employee", self.employee)
			if self.total_amount <= claim_employee.medical_balance:
				claim_employee.set("medical_availed", self.total_amount + claim_employee.medical_availed)
				claim_employee.set(
					"medical_balance", claim_employee.medical_allowance - claim_employee.medical_availed
				)
				claim_employee.db_update()
			else:
				frappe.throw("Employee does not have enough balance to claim medical allowance")

	def on_cancel(self):
		if self.reimbursement_type == "Medical":
			claim_employee = frappe.get_doc("Employee", self.employee)
			claim_employee.set("medical_availed", claim_employee.medical_availed - self.total_amount)
			claim_employee.set(
				"medical_balance", claim_employee.medical_allowance - claim_employee.medical_availed
			)
			claim_employee.db_update()
			frappe.msgprint("Balance of %d added back to the employee medical balance" % (self.total_amount))
