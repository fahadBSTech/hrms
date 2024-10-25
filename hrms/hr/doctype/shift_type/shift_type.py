# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from datetime import datetime, timedelta
from itertools import groupby

import frappe
from frappe.model.document import Document
from frappe.utils import cint, create_batch, get_datetime, get_time, getdate

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday

from hrms.hr.doctype.attendance.attendance import mark_attendance
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
)
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift, get_shift_details
from hrms.utils import get_date_range
from hrms.utils.holiday_list import get_holiday_dates_between

EMPLOYEE_CHUNK_SIZE = 50

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("shift_type", allow_site=True, file_count=10)


class ShiftType(Document):
	@frappe.whitelist()
	def process_auto_attendance(self):
		if (
			not cint(self.enable_auto_attendance) or not self.process_attendance_after
			# or not self.last_sync_of_checkin
		):
			logger.info(
				f"Skipping Shift due to; Auto-Attendance: {cint(self.enable_auto_attendance)}, Process Attendance After: {self.process_attendance_after}, Last Sync of Checkin: {self.last_sync_of_checkin}"
			)
			return

		logs = self.get_employee_checkins()

		group_key = lambda x: (x["employee"], x["shift_start"])  # noqa
		for key, group in groupby(sorted(logs, key=group_key), key=group_key):
			single_shift_logs = list(group)
			attendance_date = key[1].date()
			employee = key[0]

			if not self.should_mark_attendance(employee, attendance_date):
				logger.info(f"Skipping Attendance due to holiday. {employee}-{attendance_date}")
				continue

			(
				attendance_status,
				working_hours,
				late_entry,
				early_exit,
				in_time,
				out_time,
			) = self.get_attendance(single_shift_logs)
			mark_attendance_and_link_log(
				single_shift_logs,
				attendance_status,
				attendance_date,
				working_hours,
				late_entry,
				early_exit,
				in_time,
				out_time,
				self.name,
			)

		# commit after processing checkin logs to avoid losing progress
		frappe.db.commit()  # nosemgrep

		assigned_employees = self.get_assigned_employees(self.process_attendance_after, True)

		# mark absent in batches & commit to avoid losing progress since this tries to process remaining attendance
		# right from "Process Attendance After" to "Last Sync of Checkin"
		for batch in create_batch(assigned_employees, EMPLOYEE_CHUNK_SIZE):
			for employee in batch:
				self.mark_absent_for_dates_with_no_attendance(employee)

			frappe.db.commit()  # nosemgrep

	def get_employee_checkins(self) -> list[dict]:
		return frappe.get_all(
			"Employee Checkin",
			fields=[
				"name",
				"employee",
				"log_type",
				"time",
				"shift",
				"shift_start",
				"shift_end",
				"shift_actual_start",
				"shift_actual_end",
				"device_id",
			],
			filters={
				"skip_auto_attendance": 0,
				"attendance": ("is", "not set"),
				"time": (">=", self.process_attendance_after),
				"shift_actual_end": ("<", getdate(self.last_sync_of_checkin)),
				"shift": self.name,
			},
			order_by="employee,time",
		)

	def get_attendance(self, logs):
		"""Return attendance_status, working_hours, late_entry, early_exit, in_time, out_time
		for a set of logs belonging to a single shift.
		Assumptions:
		1. These logs belongs to a single shift, single employee and it's not in a holiday date.
		2. Logs are in chronological order
		"""
		late_entry = early_exit = False
		total_working_hours, in_time, out_time = calculate_working_hours(
			logs, self.determine_check_in_and_check_out, self.working_hours_calculation_based_on
		)
		if (
			cint(self.enable_late_entry_marking)
			and in_time
			and in_time > logs[0].shift_start + timedelta(minutes=cint(self.late_entry_grace_period))
		):
			late_entry = True

		if (
			cint(self.enable_early_exit_marking)
			and out_time
			and out_time < logs[0].shift_end - timedelta(minutes=cint(self.early_exit_grace_period))
		):
			early_exit = True

		if (
			self.working_hours_threshold_for_absent
			and total_working_hours < self.working_hours_threshold_for_absent
		):
			return "Absent", total_working_hours, late_entry, early_exit, in_time, out_time

		if (
			self.working_hours_threshold_for_half_day
			and total_working_hours < self.working_hours_threshold_for_half_day
		):
			return "Half Day", total_working_hours, late_entry, early_exit, in_time, out_time

		return "Present", total_working_hours, late_entry, early_exit, in_time, out_time

	def mark_absent_for_dates_with_no_attendance(self, employee: str):
		"""Marks Absents for the given employee on working days in this shift that have no attendance marked.
		The Absent status is marked starting from 'process_attendance_after' or employee creation date.
		"""
		start_time = get_time(self.start_time)
		dates = self.get_dates_for_attendance(employee)
		logger.info(f"Dates = {dates}")

		for date in dates:
			logger.info(f"Getting employee {employee} shift having data: {date} {start_time}")
			timestamp = datetime.combine(date, start_time)
			shift_details = get_employee_shift(employee, timestamp, True)
			if shift_details and shift_details.shift_type.name == self.name:
				logger.info(f"Shift Assigned {shift_details} and employee {employee}")
				logger.info(f"Going to mark attendance date: {date} as Absent due to no attendance")
				attendance = mark_attendance(employee, date, "Absent", self.name)
				logger.info(f"Attendance marked: {attendance}")
				if not attendance:
					continue

				frappe.get_doc(
					{
						"doctype": "Comment",
						"comment_type": "Comment",
						"reference_doctype": "Attendance",
						"reference_name": attendance,
						"content": frappe._("Employee was marked Absent due to missing Employee Checkins."),
					}
				).insert(ignore_permissions=True)

	def get_dates_for_attendance(self, employee: str) -> list[str]:
		start_date, end_date = self.get_start_and_end_dates(employee)
		logger.info(
			f"Employee: {employee}, Attendance Start Date: {start_date}, Attendance End Date: {end_date}"
		)

		# no shift assignment found, no need to process absent attendance records
		if start_date is None:
			return []

		date_range = get_date_range(start_date, end_date)

		# skip marking absent on holidays
		holiday_list = self.get_holiday_list(employee)
		holiday_dates = get_holiday_dates_between(holiday_list, start_date, end_date)
		# skip dates with attendance
		marked_attendance_dates = self.get_marked_attendance_dates_between(employee, start_date, end_date)

		return sorted(set(date_range) - set(holiday_dates) - set(marked_attendance_dates))

	def get_start_and_end_dates(self, employee):
		"""Returns start and end dates for checking attendance and marking absent
		return: start date = max of `process_attendance_after` and DOJ
		return: end date = min of shift before `last_sync_of_checkin` and Relieving Date
		"""
		date_of_joining, relieving_date, employee_creation = frappe.get_cached_value(
			"Employee", employee, ["date_of_joining", "relieving_date", "creation"]
		)

		if not date_of_joining:
			date_of_joining = employee_creation.date()

		start_date = max(getdate(self.process_attendance_after), date_of_joining)
		end_date = None

		shift_details = get_shift_details(self.name, get_datetime(self.last_sync_of_checkin))
		last_shift_time = (
			shift_details.actual_end if shift_details else get_datetime(self.last_sync_of_checkin)
		)

		# check if shift is found for 1 day before the last sync of checkin
		# absentees are auto-marked 1 day after the shift to wait for any manual attendance records
		prev_shift = get_employee_shift(employee, last_shift_time - timedelta(days=1), True, "reverse")
		if prev_shift and prev_shift.shift_type.name == self.name:
			end_date = (
				min(prev_shift.start_datetime.date(), relieving_date)
				if relieving_date
				else prev_shift.start_datetime.date()
			)
		else:
			# no shift found
			return None, None
		return start_date, end_date

	def get_marked_attendance_dates_between(self, employee: str, start_date: str, end_date: str) -> list[str]:
		Attendance = frappe.qb.DocType("Attendance")
		return (
			frappe.qb.from_(Attendance)
			.select(Attendance.attendance_date)
			.where(
				(Attendance.employee == employee)
				& (Attendance.docstatus < 2)
				& (Attendance.attendance_date.between(start_date, end_date))
				& ((Attendance.shift.isnull()) | (Attendance.shift == self.name))
			)
		).run(pluck=True)

	def get_assigned_employees(self, from_date=None, consider_default_shift=False) -> list[str]:
		filters = {"shift_type": self.name, "docstatus": "1", "status": "Active"}
		if from_date:
			filters["start_date"] = (">=", from_date)

		assigned_employees = frappe.get_all("Shift Assignment", filters=filters, pluck="employee")

		if consider_default_shift:
			default_shift_employees = self.get_employees_with_default_shift(filters)
			assigned_employees = set(assigned_employees + default_shift_employees)

		# exclude inactive employees
		inactive_employees = frappe.db.get_all("Employee", {"status": "Inactive"}, pluck="name")

		return list(set(assigned_employees) - set(inactive_employees))

	def get_employees_with_default_shift(self, filters: dict) -> list:
		default_shift_employees = frappe.get_all(
			"Employee", filters={"default_shift": self.name, "status": "Active"}, pluck="name"
		)

		if not default_shift_employees:
			return []

		# exclude employees from default shift list if any other valid shift assignment exists
		del filters["shift_type"]
		filters["employee"] = ("in", default_shift_employees)

		active_shift_assignments = frappe.get_all(
			"Shift Assignment",
			filters=filters,
			pluck="employee",
		)

		return list(set(default_shift_employees) - set(active_shift_assignments))

	def get_holiday_list(self, employee: str) -> str:
		holiday_list_name = self.holiday_list or get_holiday_list_for_employee(employee, False)
		return holiday_list_name

	def should_mark_attendance(self, employee: str, attendance_date: str) -> bool:
		"""Determines whether attendance should be marked on holidays or not"""
		if self.mark_auto_attendance_on_holidays:
			# no need to check if date is a holiday or not
			# since attendance should be marked on all days
			return True

		holiday_list = self.get_holiday_list(employee)
		if is_holiday(holiday_list, attendance_date):
			return False
		return True


def process_auto_attendance_for_all_shifts():
	shift_list = frappe.get_all("Shift Type", filters={"enable_auto_attendance": "1"}, pluck="name")
	for shift in shift_list:
		print("Shift Type:", shift)
		doc = frappe.get_cached_doc("Shift Type", shift)
		doc.process_auto_attendance()


def get_time_difference(obj1, obj2):
	difference = (obj1 - obj2).time()
	hours, minutes, seconds_microseconds = str(difference).split(":")
	seconds, microseconds = seconds_microseconds.split(".")
	hours = int(hours)
	minutes = int(minutes)
	seconds = int(seconds)
	microseconds = int(microseconds)
	total_minutes = hours * 60 + minutes + seconds / 60 + microseconds / 60000000
	return round(total_minutes)


def get_assigned_employees_with_specified_threshold(
	name, from_date=None, start_time=None, end_time=None
) -> list[str]:
	filters = {"shift_type": name, "docstatus": "1", "status": "Active"}
	if from_date:
		filters["start_date"] = (">=", from_date)
	assigned_employees = frappe.get_all("Shift Assignment", filters=filters, pluck="employee")

	# exclude inactive employees
	inactive_employees = frappe.db.get_all("Employee", {"status": "inactive"}, pluck="name")

	if start_time is not None:
		assigned_employees = [
			emp
			for emp in assigned_employees
			if (
				start_time - 1
				<= int(frappe.get_value("Employee", emp, "custom_notification_threshold_checkin") or 15)
				<= start_time + 1
			)
			and not has_valid_log_for_today(in_log="IN", emp=emp)
		]
	elif end_time is not None:
		assigned_employees = [
			emp
			for emp in assigned_employees
			if (
				end_time - 1
				<= int(frappe.get_value("Employee", emp, "custom_notification_threshold_checkout") or 15)
				<= end_time + 1
			)
			and not has_valid_log_for_today(in_log="OUT", emp=emp)
		]
	return list(set(assigned_employees) - set(inactive_employees))


def has_valid_log_for_today(in_log=None, out_log=None, emp=None):
	today = datetime.today()
	log_type = in_log if in_log else out_log
	valid_log = frappe.db.sql(
		"""SELECT log_type FROM `tabEmployee Checkin`
		WHERE CAST(time as DATE)=%(time_val)s AND log_type=%(log_type)s AND employee = %(emp)s
		""",
		{"time_val": today.strftime("%Y-%m-%d"), "log_type": log_type, "emp": emp},
	)
	return True if valid_log else False


def notify_employees_to_checkin_or_checkout():
	frappe.utils.logger.set_log_level("DEBUG")
	notification_logger = frappe.logger("reminder_notifications", allow_site=True, file_count=10)
	notify_checkin = notify_checkout = []
	now = frappe.utils.now_datetime()
	two_hours_back = frappe.utils.add_to_date(now, hours=-2)
	query = """
			SELECT start_time, end_time, name, holiday_list
			FROM `tabShift Type`
			WHERE (start_time BETWEEN %s AND %s) OR (end_time BETWEEN %s AND %s)
		"""

	# Execute the query with the formatted time strings
	shifts = frappe.db.sql(query, (two_hours_back, now, two_hours_back, now), as_dict=True)
	for shift in shifts:
		notification_logger.info(f"Shift Name: {shift.name}")
		if is_holiday(shift.holiday_list, frappe.utils.getdate(now)):
			notification_logger.info("Skipped: holiday found")
			continue
		notify_checkin = []
		notify_checkout = []
		time_difference_in = get_time_difference(now, shift.start_time)
		time_difference_out = get_time_difference(now, shift.end_time)
		employees_closer_to_checkin = get_assigned_employees_with_specified_threshold(
			shift.name, start_time=time_difference_in
		)
		for emp in employees_closer_to_checkin:
			employee = frappe.get_doc("Employee", emp)
			if employee:
				notify_checkin.append(employee.user_id)
			frappe.enqueue(
				method="fcm_notification.send_notification.send_push_to_user",
				email=employee.user_id,
				title="Don’t Forget to Check In!",
				message="Good morning! Please remember to check in for your shift. Have a productive day!",
			)
		employees_closer_to_checkout = get_assigned_employees_with_specified_threshold(
			shift.name, end_time=time_difference_out
		)
		for emp in employees_closer_to_checkout:
			employee = frappe.get_doc("Employee", emp)
			if employee:
				notify_checkout.append(employee.user_id)
			frappe.enqueue(
				method="fcm_notification.send_notification.send_push_to_user",
				email=employee.user_id,
				title="Time to Check Out!",
				message="Your shift is almost over. Please remember to check out. Have a great evening!",
			)
		notification_logger.info(f"Employees to be notified for Check In: {notify_checkin}")
		notification_logger.info(f"Employees to be notified for Check Out: {notify_checkout}")
