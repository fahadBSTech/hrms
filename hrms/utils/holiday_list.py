import frappe
from frappe.utils import getdate, add_days, get_first_day, get_last_day, nowdate
from datetime import datetime


def is_holiday(holiday_list, date):
	if not holiday_list:
		return False

	date = getdate(date)
	holidays = frappe.get_all('Holiday', filters={'parent': holiday_list, 'holiday_date': date},
							  fields=['holiday_date'])

	return bool(holidays)


@frappe.whitelist()
def get_current_month_working_days(company):
	user = frappe.session.user
	employee = frappe.get_value("Employee", {"user_id": user}, "name")

	if not employee:
		frappe.throw("Employee record not found for the logged-in user")

	today = getdate(nowdate())
	start_date = get_first_day(today)
	end_date = get_last_day(today)
	holiday_list = frappe.get_value("Company", company, "default_holiday_list")

	total_working_days_count = 0
	current_date = start_date

	while current_date <= end_date:
		if not is_holiday(holiday_list,
						  current_date) and current_date.weekday() < 5:  # Count weekdays and non-holidays as working days
			total_working_days_count += 1
		current_date = add_days(current_date, 1)

	leaves = frappe.get_all('Leave Application',
							filters={
								'employee': employee,
								'status': 'Approved',
								'from_date': ('<=', today),
								'to_date': ('>=', start_date)
							},
							fields=['from_date', 'to_date', 'half_day'])

	leave_days_count = 0
	for leave in leaves:
		leave_start = getdate(leave['from_date'])
		leave_end = getdate(leave['to_date'])
		current_leave_date = leave_start

		while current_leave_date <= leave_end:
			if start_date <= current_leave_date <= today:
				if leave['half_day']:
					leave_days_count += 0.5
				else:
					leave_days_count += 1
			current_leave_date = add_days(current_leave_date, 1)

	working_days_till_today = 0
	current_date = start_date

	while current_date <= today:
		if not is_holiday(holiday_list,
						  current_date) and current_date.weekday() < 5:  # Count weekdays and non-holidays as working days
			working_days_till_today += 1
		current_date = add_days(current_date, 1)

	actual_working_days_count = working_days_till_today - leave_days_count

	return {
		'total_working_days': total_working_days_count,
		'off_days': leave_days_count,
		'employee_working_days': actual_working_days_count
	}

def get_holiday_dates_between(holiday_list: str, start_date: str, end_date: str) -> list:
	Holiday = frappe.qb.DocType("Holiday")
	return (
		frappe.qb.from_(Holiday)
		.select(Holiday.holiday_date)
		.where((Holiday.parent == holiday_list) & (Holiday.holiday_date.between(start_date, end_date)))
		.orderby(Holiday.holiday_date)
	).run(pluck=True)


def invalidate_cache(doc, method=None):
	from hrms.payroll.doctype.salary_slip.salary_slip import HOLIDAYS_BETWEEN_DATES

	frappe.cache.delete_value(HOLIDAYS_BETWEEN_DATES)
