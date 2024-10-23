#!/usr/bin/python
import calendar
import logging
from datetime import date, timedelta

import frappe
from frappe.utils import getdate, today


def calculate_employee_fuel_allowance():
	# Get the current date
	currentDate = getdate(today())

	# Calculate the start and end of the previous month
	firstDayOfCurrentMonth = currentDate.replace(day=1)
	endOfPreviousMonth = firstDayOfCurrentMonth - timedelta(days=1)
	startOfPreviousMonth = endOfPreviousMonth.replace(day=1)

	average_fuel_allowance = get_average_fuel_allowance_for_month(startOfPreviousMonth, endOfPreviousMonth)
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active", "custom_distancekm": ["!=", ""], "custom_transport_type": ["!=", ""]},
		fields=["name", "employee_name", "custom_distancekm", "custom_transport_type"],
	)

	total_days_in_month = calendar.monthrange(endOfPreviousMonth.year, endOfPreviousMonth.month)[1]
	public_holidays_count = fetch_public_holidays(startOfPreviousMonth, endOfPreviousMonth)
	total_days = total_days_in_month - public_holidays_count
	for emp in employees:
		leaves = count_leaves(emp.name, startOfPreviousMonth, endOfPreviousMonth)
		wfh_days = count_work_from_home(emp.name, startOfPreviousMonth, endOfPreviousMonth)
		working_days = total_days - leaves - wfh_days
		fuel_allowance = calculate_allowance(emp, working_days, average_fuel_allowance)
		create_employee_fuel_allowance_record(emp, fuel_allowance, endOfPreviousMonth)


def count_leaves(employee, start_date, end_date):
	leaves = frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee,
			"from_date": ["<=", end_date],
			"to_date": [">=", start_date],
			"status": "Approved",
			"docstatus": 1,
		},
		fields=["name", "from_date", "to_date", "half_day"],
	)

	leave_days = 0
	for leave in leaves:
		# Skip the leave if it's a half-day
		if not leave.half_day:
			leave_days += frappe.utils.date_diff(leave.to_date, leave.from_date) + 1

	return leave_days


def count_work_from_home(employee, start_date, end_date):
	wfh_days_count = frappe.get_all(
		"Work From Home",
		filters={
			"employee": employee,
			"from_date": ["<=", end_date],
			"to_date": [">=", start_date],
			"status": "Approved",
			"docstatus": 1,
		},
		fields=["name", "from_date", "to_date"],
	)

	wfh_days = 0
	for day in wfh_days_count:
		wfh_days += frappe.utils.date_diff(day.to_date, day.from_date) + 1
	return wfh_days


def get_average_fuel_allowance_for_month(start_date, end_date):
	fuel_allowances = frappe.get_all(
		"Fuel Allowance",
		filters={"date": ["between", (start_date, end_date)]},
		fields=["fuel_amount", "base_fuel_amount"],
	)

	if not fuel_allowances:
		return 0
	# Calculate the difference between fuel_amount and base_fuel_amount for each record
	total_difference = sum(fuel["fuel_amount"] - fuel["base_fuel_amount"] for fuel in fuel_allowances)

	# Calculate the average of these differences
	average_difference = total_difference / len(fuel_allowances)
	return average_difference


def calculate_allowance(employee, working_days, fuel_allowance):
	if not fuel_allowance:
		return 0

	# Example calculation, adjust as needed

	working_days = int(working_days)  # Convert to int if it's not already
	fuel_allowance = float(fuel_allowance)  # Convert to float if it's not already
	distance = float(frappe.db.get_value("Employee", employee, "custom_distancekm"))
	transport_type = frappe.db.get_value("Employee", employee, "custom_transport_type")
	vehicleMileage = 10
	if transport_type == "Bike":
		vehicleMileage = 20
	allowance = distance * 2 * working_days / vehicleMileage * fuel_allowance

	return allowance


def fetch_public_holidays(startDate, endDate):
	# Retrieve the default holiday list for the given company
	default_holiday_list_name = frappe.get_value("Company", "Bitsol Technologies", "default_holiday_list")

	if not default_holiday_list_name:
		return 0

	# Fetch public holidays within the specified date range from the default holiday list
	public_holidays = frappe.get_all(
		"Holiday",
		filters={"parent": default_holiday_list_name, "holiday_date": ["between", [startDate, endDate]]},
		fields=["holiday_date"],
	)
	return len(public_holidays)


def create_employee_fuel_allowance_record(employee, fuel_allowance, fuel_allowance_month):
	if fuel_allowance < 1000:
		fuel_allowance = 1000
	elif fuel_allowance > 10000:
		fuel_allowance = 10000

	new_record = frappe.get_doc(
		{
			"doctype": "Employee Fuel Allowance",
			"employee": employee["name"],
			"allowance_amount": fuel_allowance,
			"fuel_allowance_month": fuel_allowance_month,
		}
	)
	new_record.insert()
	frappe.db.commit()


def reset_medical_allowances():
	employees = frappe.get_all("Employee", fields=["name", "medical_allowance"])

	for employee in employees:
		# Set medical_availed to 0 and medical_balance to medical_allowance
		frappe.db.set_value("Employee", employee["name"], "medical_availed", 0)
		frappe.db.set_value("Employee", employee["name"], "medical_balance", employee["medical_allowance"])
	frappe.db.commit()
