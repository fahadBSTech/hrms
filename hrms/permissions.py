import frappe


def te_query(user):
	if not user:
		user = frappe.session.user

	if "Restricted Training Events" in frappe.get_roles(user) and user != "Administrator":
		return f"(`tabTraining Event`.employee_emails like '%{user}%')"
	return


def has_te_permission_query(doc, user=None, permission_type=None):
	if not user:
		user = frappe.session.user
	if (
		"Restricted Training Events" in frappe.get_roles(user) and user in doc.employee_emails
	) or "HR Manager" in frappe.get_roles(user):
		return True
	return False
