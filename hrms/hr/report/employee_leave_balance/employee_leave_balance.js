// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
const currentDate = new Date();
const currentYear = currentDate.getFullYear();
const from_date = currentYear + '-01-01'; // January 1 of the current year
const to_date = currentYear + '-12-31'; // December 31 of the current year
frappe.query_reports["Employee Leave Balance"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      reqd: 1,
      default: from_date
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      reqd: 1,
      default: to_date
    },
    {
      label: __("Company"),
      fieldname: "company",
      fieldtype: "Link",
      options: "Company",
      reqd: 1,
      default: frappe.defaults.get_user_default("Company")
    },
    {
      fieldname: "department",
      label: __("Department"),
      fieldtype: "Link",
      options: "Department"
    },
    {
      fieldname: "employee",
      label: __("Employee"),
      fieldtype: "Link",
      options: "Employee"
    },
    {
      fieldname: "employee_status",
      label: __("Employee Status"),
      fieldtype: "Select",
      options: [
        "",
        { value: "Active", label: __("Active") },
        { value: "Inactive", label: __("Inactive") },
        { value: "Suspended", label: __("Suspended") },
        { value: "Left", label: __("Left") }
      ],
      default: "Active"
    }
  ],

  onload: () => {
    frappe.call({
      type: "GET",
      method: "hrms.hr.utils.get_leave_period",
      args: {
        from_date,
        to_date,
        company: frappe.defaults.get_user_default("Company")
      },
      freeze: true,
      callback: data => {
        frappe.query_report.set_filter_value(
          "from_date",
          from_date
        );
        frappe.query_report.set_filter_value(
          "to_date",
          to_date
        );
      }
    });
  }
};
