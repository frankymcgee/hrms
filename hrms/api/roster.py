import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, get_datetime_str

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

from hrms.hr.doctype.shift_assignment.shift_assignment import ShiftAssignment
from hrms.hr.doctype.shift_assignment_tool.shift_assignment_tool import create_shift_assignment
from hrms.hr.doctype.shift_schedule.shift_schedule import get_or_insert_shift_schedule


@frappe.whitelist()
def get_default_company() -> str:
	return frappe.defaults.get_user_default("Company")


@frappe.whitelist()
def get_values(doctype: str, name: str, fields: list) -> dict[str, str]:
	return frappe.db.get_value(doctype, name, fields, as_dict=True)


@frappe.whitelist()
def get_events(
	month_start: str, month_end: str, employee_filters: dict[str, str], shift_filters: dict[str, str]
) -> dict[str, list[dict]]:
	employee_filters = _clean_filters(employee_filters)
	shift_filters = _clean_filters(shift_filters)

	holidays = get_holidays(month_start, month_end, employee_filters)
	leaves = get_leaves(month_start, month_end, employee_filters)
	shifts = get_shifts(month_start, month_end, employee_filters, shift_filters)

	return merge_employee_events(holidays, leaves, shifts)


@frappe.whitelist()
def get_year_events(
	year: str | int, employee_filters: dict[str, str], shift_filters: dict[str, str]
) -> dict:
	"""Return compact annual roster data.

	The annual view keeps project/planning rows and employee rows separate. Employee
	rows still use the same holiday, leave and shift assignment data as the month
	view, while project rows are a compact daily summary by Shift Assignment
	custom_project/custom_project_name.
	"""
	employee_filters = _clean_filters(employee_filters)
	shift_filters = _clean_filters(shift_filters)

	year = int(year)
	year_start = f"{year}-01-01"
	year_end = f"{year}-12-31"

	holidays = get_holidays(year_start, year_end, employee_filters)
	leaves = get_leaves(year_start, year_end, employee_filters)
	shift_rows = get_shift_rows(year_start, year_end, employee_filters, shift_filters)
	shifts = group_by_employee(shift_rows)

	return {
		"events": merge_employee_events(holidays, leaves, shifts),
		"project_rows": get_year_project_rows(shift_rows, year_start, year_end),
	}


def _clean_filters(filters: dict | str | None) -> dict:
	if not filters:
		return {}
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or {}
	return {key: value for key, value in dict(filters).items() if value not in (None, "")}


def merge_employee_events(*event_groups: dict[str, list[dict]]) -> dict[str, list[dict]]:
	events = {}
	for event_group in event_groups:
		for key, value in event_group.items():
			if key in events:
				events[key].extend(value)
			else:
				events[key] = value
	return events


@frappe.whitelist()
def get_schedule_from_assignment(shift_schedule_assignment: str):
	shift_schedule = frappe.db.get_value(
		"Shift Schedule Assignment", shift_schedule_assignment, "shift_schedule"
	)
	frequency = frappe.db.get_value("Shift Schedule", shift_schedule, "frequency")
	repeat_on_days = frappe.get_all("Assignment Rule Day", filters={"parent": shift_schedule}, pluck="day")
	return {"frequency": frequency, "repeat_on_days": repeat_on_days}


@frappe.whitelist()
def create_shift_schedule_assignment(
	employee: str,
	company: str,
	shift_type: str,
	status: str,
	start_date: str,
	end_date: str | None,
	repeat_on_days: list[str],
	frequency: str,
	shift_location: str | None = None,
	custom_project: str | None = None,
) -> None:
	shift_schedule = get_or_insert_shift_schedule(shift_type, frequency, repeat_on_days)
	shift_schedule_assignment = frappe.get_doc(
		{
			"doctype": "Shift Schedule Assignment",
			"shift_schedule": shift_schedule,
			"employee": employee,
			"company": company,
			"shift_status": status,
			"shift_location": shift_location,
			"custom_project": custom_project,
			"enabled": 0 if end_date else 1,
		}
	).insert()

	if not end_date or date_diff(end_date, start_date) <= 90:
		return shift_schedule_assignment.create_shifts(start_date, end_date)

	frappe.enqueue(
		shift_schedule_assignment.create_shifts, timeout=4500, start_date=start_date, end_date=end_date
	)


@frappe.whitelist()
def delete_shift_schedule_assignment(shift_schedule_assignment: str) -> None:
	for shift_assignment in frappe.get_all(
		"Shift Assignment", {"shift_schedule_assignment": shift_schedule_assignment}, pluck="name"
	):
		doc = frappe.get_doc("Shift Assignment", shift_assignment)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Shift Assignment", shift_assignment)
	frappe.delete_doc("Shift Schedule Assignment", shift_schedule_assignment)


@frappe.whitelist()
def swap_shift(
	src_shift: str, src_date: str, tgt_employee: str, tgt_date: str, tgt_shift: str | None
) -> None:
	if src_shift == tgt_shift:
		frappe.throw(_("Source and target shifts cannot be the same"))

	if tgt_shift:
		tgt_shift_doc = frappe.get_doc("Shift Assignment", tgt_shift)
		tgt_company = tgt_shift_doc.company
		break_shift(tgt_shift_doc, tgt_date)
	else:
		tgt_company = frappe.db.get_value("Employee", tgt_employee, "company")

	src_shift_doc = frappe.get_doc("Shift Assignment", src_shift)
	break_shift(src_shift_doc, src_date)
	insert_shift(
		tgt_employee,
		tgt_company,
		src_shift_doc.shift_type,
		tgt_date,
		tgt_date,
		src_shift_doc.status,
		src_shift_doc.shift_location,
		src_shift_doc.custom_project,
	)

	if tgt_shift:
		insert_shift(
			src_shift_doc.employee,
			src_shift_doc.company,
			tgt_shift_doc.shift_type,
			src_date,
			src_date,
			tgt_shift_doc.status,
			tgt_shift_doc.shift_location,
			tgt_shift_doc.custom_project,
		)


@frappe.whitelist()
def _to_date_str(value):
	if not value:
		return None
	# getdate handles str/date/datetime; str() gives YYYY-MM-DD for date
	return str(getdate(value))


@frappe.whitelist()
def break_shift(assignment: str | ShiftAssignment, date: str) -> None:
	if isinstance(assignment, str):
		assignment = frappe.get_doc("Shift Assignment", assignment)

	if assignment.end_date and date_diff(assignment.end_date, date) < 0:
		frappe.throw(_("Cannot break shift after end date"))
	if date_diff(assignment.start_date, date) > 0:
		frappe.throw(_("Cannot break shift before start date"))

	employee = assignment.employee
	company = assignment.company
	shift_type = assignment.shift_type
	status = assignment.status
	end_date = assignment.end_date
	shift_location = assignment.shift_location
	custom_project = assignment.custom_project

	if date_diff(date, assignment.start_date) == 0:
		assignment.cancel()
		assignment.delete()
	else:
		assignment.end_date = add_days(date, -1)
		assignment.save()

	if not end_date or date_diff(end_date, date) > 0:
		create_shift_assignment(
			employee,
			company,
			shift_type,
			_to_date_str(add_days(date, 1)),
			_to_date_str(end_date),
			status,
			custom_project,
			shift_location,
		)


@frappe.whitelist()
def insert_shift(
	employee: str,
	company: str,
	shift_type: str,
	start_date: str,
	end_date: str | None,
	status: str,
	shift_location: str | None = None,
	custom_project: str | None = None,
) -> None:
	from frappe.utils import add_days

	# Treat project as part of the identity so only same-project blocks merge
	filters = {
		"doctype": "Shift Assignment",
		"employee": employee,
		"company": company,
		"shift_type": shift_type,
		"status": status,
		"shift_location": shift_location,
		"custom_project": custom_project,
	}

	prev_shift = frappe.db.exists(dict({"end_date": add_days(start_date, -1)}, **filters))
	next_shift = (
		frappe.db.exists(dict({"start_date": add_days(end_date, 1)}, **filters)) if end_date else None
	)

	if prev_shift:
		if next_shift:
			end_date = frappe.db.get_value("Shift Assignment", next_shift, "end_date")
			frappe.db.set_value("Shift Assignment", next_shift, "docstatus", 2)
			frappe.delete_doc("Shift Assignment", next_shift)

		frappe.db.set_value("Shift Assignment", prev_shift, "end_date", end_date or None)
		# ensure project sticks even if previous block had None
		if custom_project:
			frappe.db.set_value("Shift Assignment", prev_shift, "custom_project", custom_project)

	elif next_shift:
		frappe.db.set_value("Shift Assignment", next_shift, "start_date", start_date)
		if custom_project:
			frappe.db.set_value("Shift Assignment", next_shift, "custom_project", custom_project)

	else:
		create_shift_assignment(
			employee=employee,
			company=company,
			shift_type=shift_type,
			start_date=start_date,
			end_date=end_date,
			status=status,
			custom_project=custom_project,
			shift_location=shift_location,
		)


def get_holidays(month_start: str, month_end: str, employee_filters: dict[str, str]) -> dict[str, list[dict]]:
	employee_filters = _clean_filters(employee_filters)
	holidays = {}
	holiday_lists = {}

	for employee in frappe.get_list("Employee", filters=employee_filters, pluck="name"):
		if not (holiday_list := get_holiday_list_for_employee(employee, raise_exception=False)):
			continue
		if holiday_list not in holiday_lists:
			holiday_lists[holiday_list] = frappe.get_all(
				"Holiday",
				filters={"parent": holiday_list, "holiday_date": ["between", [month_start, month_end]]},
				fields=["name as holiday", "holiday_date", "description", "weekly_off"],
			)
		holidays[employee] = holiday_lists[holiday_list].copy()

	return holidays


def get_leaves(month_start: str, month_end: str, employee_filters: dict[str, str]) -> dict[str, list[dict]]:
	employee_filters = _clean_filters(employee_filters)
	LeaveApplication = frappe.qb.DocType("Leave Application")
	Employee = frappe.qb.DocType("Employee")

	query = (
		frappe.qb.select(
			LeaveApplication.name.as_("leave"),
			LeaveApplication.employee,
			LeaveApplication.leave_type,
			LeaveApplication.from_date,
			LeaveApplication.to_date,
		)
		.from_(LeaveApplication)
		.left_join(Employee)
		.on(LeaveApplication.employee == Employee.name)
		.where(
			(LeaveApplication.docstatus == 1)
			& (LeaveApplication.status == "Approved")
			& (LeaveApplication.from_date <= month_end)
			& (LeaveApplication.to_date >= month_start)
		)
	)

	for filter in employee_filters:
		query = query.where(Employee[filter] == employee_filters[filter])

	return group_by_employee(query.run(as_dict=True))


def get_shifts(
	month_start: str, month_end: str, employee_filters: dict[str, str], shift_filters: dict[str, str]
) -> dict[str, list[dict]]:
	return group_by_employee(get_shift_rows(month_start, month_end, employee_filters, shift_filters))


def get_shift_rows(
	month_start: str, month_end: str, employee_filters: dict[str, str], shift_filters: dict[str, str]
) -> list[dict]:
	employee_filters = _clean_filters(employee_filters)
	shift_filters = _clean_filters(shift_filters)

	ShiftAssignment = frappe.qb.DocType("Shift Assignment")
	ShiftType = frappe.qb.DocType("Shift Type")
	Employee = frappe.qb.DocType("Employee")
	Project = frappe.qb.DocType("Project")

	query = (
		frappe.qb.select(
			ShiftAssignment.name,
			ShiftAssignment.employee,
			ShiftAssignment.shift_type,
			ShiftAssignment.shift_location,
			ShiftAssignment.start_date,
			ShiftAssignment.end_date,
			ShiftAssignment.status,
			ShiftAssignment.shift_schedule_assignment,
			ShiftAssignment.custom_project,
			ShiftAssignment.custom_project_name,
			ShiftAssignment.note,
			ShiftType.start_time,
			ShiftType.end_time,
			ShiftType.color,
			Project.customer_abbreviation.as_("customer_abbreviation"),
		)
		.from_(ShiftAssignment)
		.left_join(ShiftType)
		.on(ShiftAssignment.shift_type == ShiftType.name)
		.left_join(Employee)
		.on(ShiftAssignment.employee == Employee.name)
		.left_join(Project)
		.on(ShiftAssignment.custom_project == Project.name)
		.where(
			(ShiftAssignment.docstatus == 1)
			& (ShiftAssignment.start_date <= month_end)
			& ((ShiftAssignment.end_date >= month_start) | (ShiftAssignment.end_date.isnull()))
		)
	)

	for filter in employee_filters:
		query = query.where(Employee[filter] == employee_filters[filter])

	for filter in shift_filters:
		query = query.where(ShiftAssignment[filter] == shift_filters[filter])

	return query.run(as_dict=True)


def _first_existing_project_field(candidates: list[str]) -> str | None:
	meta = frappe.get_meta("Project")
	for field in candidates:
		if meta.has_field(field):
			return field
	return None


def _truthy_project_value(value) -> bool:
	if value in (None, ""):
		return False
	if isinstance(value, str):
		return value.strip().lower() not in ("0", "no", "false", "missing", "not entered", "none")
	return bool(value)


def _safe_int(value) -> int:
	try:
		return int(value or 0)
	except (TypeError, ValueError):
		return 0


def get_active_project_meta(project_names: list[str] | set[str]) -> dict[str, dict]:
	"""Return Project metadata for projects that should appear in annual planning rows.

	The annual project/planning table should only show active/open projects.
	Employee rows are intentionally left unchanged so historical/assigned shifts still
	appear for employees if they exist in the selected year.

	The annual project bar mirrors the monthly project timeline. The optional PO/DS/NS
	fields are detected defensively so this method still works if those custom fields
	do not exist on a particular site.
	"""
	project_names = sorted({project for project in project_names if project})
	if not project_names:
		return {}

	inactive_statuses = [
		"Completed",
		"Cancelled",
		"Closed",
		"Archived",
		"Inactive",
	]

	po_field = _first_existing_project_field([
		"custom_po_entered",
		"custom_purchase_order_entered",
		"custom_purchase_order",
		"custom_purchase_order_number",
		"purchase_order",
		"purchase_order_number",
		"po_number",
		"po_no",
	])
	ds_field = _first_existing_project_field([
		"ds_number",
		"custom_ds_number",
		"custom_ds_requested",
		"custom_day_shift_requested",
		"custom_day_shifts_requested",
		"ds_requested",
		"day_shift_requested",
		"day_shifts_requested",
	])
	ns_field = _first_existing_project_field([
		"ns_number",
		"custom_ns_number",
		"custom_ns_requested",
		"custom_night_shift_requested",
		"custom_night_shifts_requested",
		"ns_requested",
		"night_shift_requested",
		"night_shifts_requested",
	])

	customer_abbreviation_field = _first_existing_project_field(["customer_abbreviation"])
	customer_field = _first_existing_project_field(["customer"])
	optional_fields = [
		field
		for field in [po_field, ds_field, ns_field, customer_abbreviation_field, customer_field]
		if field
	]

	projects = frappe.get_all(
		"Project",
		filters={
			"name": ["in", project_names],
			"status": ["not in", inactive_statuses],
		},
		fields=["name", "project_name", "status", *optional_fields],
	)

	customer_colors = {}
	if customer_field:
		customer_color_field = None
		try:
			customer_meta = frappe.get_meta("Customer")
			if customer_meta.has_field("customer_color"):
				customer_color_field = "customer_color"
		except Exception:
			customer_color_field = None

		if customer_color_field:
			customer_names = sorted(
				{project.get(customer_field) for project in projects if project.get(customer_field)}
			)
			if customer_names:
				customer_colors = {
					customer.name: customer.get(customer_color_field)
					for customer in frappe.get_all(
						"Customer",
						filters={"name": ["in", customer_names]},
						fields=["name", customer_color_field],
					)
				}

	for project in projects:
		# If no PO field exists on this site yet, default to entered so the annual
		# bar uses the same visual style as the current monthly project timeline.
		project["po_entered"] = True if not po_field else _truthy_project_value(project.get(po_field))
		project["ds_requested"] = _safe_int(project.get(ds_field)) if ds_field else 0
		project["ns_requested"] = _safe_int(project.get(ns_field)) if ns_field else 0
		project["customer_color"] = (
			customer_colors.get(project.get(customer_field)) if customer_field else None
		)

	return {project.name: project for project in projects}


def get_year_project_rows(shift_rows: list[dict], year_start: str, year_end: str) -> list[dict]:
	projects = {}
	year_start_date = getdate(year_start)
	year_end_date = getdate(year_end)

	active_projects = get_active_project_meta(
		{shift.get("custom_project") for shift in shift_rows if shift.get("custom_project")}
	)

	for shift in shift_rows:
		project = shift.get("custom_project")

		# Only show active/open linked projects in the annual Projects / Planning table.
		# Skip unallocated rows and projects that are completed/cancelled/closed/etc.
		if not project or project not in active_projects:
			continue

		project_meta = active_projects[project]
		project_name = (
			project_meta.get("project_name")
			or shift.get("custom_project_name")
			or project
		)

		if project not in projects:
			projects[project] = {
				"project": project,
				"project_name": project_name,
				"status": project_meta.get("status"),
				"po_entered": project_meta.get("po_entered"),
				"ds_requested": _safe_int(project_meta.get("ds_requested")),
				"ns_requested": _safe_int(project_meta.get("ns_requested")),
				"customer_color": project_meta.get("customer_color"),
				"assignments": {},
			}

		start_date = max(getdate(shift.get("start_date")), year_start_date)
		end_date = getdate(shift.get("end_date")) if shift.get("end_date") else year_end_date
		end_date = min(end_date, year_end_date)

		current = start_date
		while current <= end_date:
			date_key = str(current)
			cell = projects[project]["assignments"].setdefault(
				date_key,
				{
					"count": 0,
					"color": None,
					"_shift_types": [],
					"_employees": [],
				},
			)
			cell["count"] += 1
			if not cell["color"] and shift.get("color"):
				cell["color"] = str(shift.get("color")).lower()
			if shift.get("shift_type"):
				cell["_shift_types"].append(shift.get("shift_type"))
			if shift.get("employee"):
				cell["_employees"].append(shift.get("employee"))
			current = getdate(add_days(current, 1))

	for project in projects.values():
		for cell in project["assignments"].values():
			shift_types = sorted(set(cell.pop("_shift_types", [])))
			employees = sorted(set(cell.pop("_employees", [])))
			cell["shift_types"] = shift_types
			cell["employees"] = employees
			cell["count"] = len(employees) or cell["count"]
			if cell["count"] > 1:
				cell["label"] = str(cell["count"])
			else:
				cell["label"] = shift_types[0] if shift_types else "1"

	return sorted(projects.values(), key=lambda row: row["project_name"] or "")


def group_by_employee(events: list[dict]) -> dict[str, list[dict]]:
	grouped_events = {}
	for event in events:
		grouped_events.setdefault(event["employee"], []).append(
			{k: v for k, v in event.items() if k != "employee"}
		)
	return grouped_events


@frappe.whitelist()
def get_available_employees(from_date: str, to_date: str, **employee_filters) -> dict:
	ALLOWED = {"company", "department", "branch", "designation", "status"}
	ef = {k: v for k, v in (employee_filters or {}).items() if k in ALLOWED and v}
	all_emp_names = set(frappe.get_all("Employee", filters=ef, pluck="name"))
	if not all_emp_names:
		return {"employees": []}
	ShiftAssignment = frappe.qb.DocType("Shift Assignment")
	busy_rows = (
		frappe.qb.select(ShiftAssignment.employee)
		.from_(ShiftAssignment)
		.where(
			(ShiftAssignment.docstatus == 1)
			& (ShiftAssignment.start_date <= to_date)
			& ((ShiftAssignment.end_date >= from_date) | (ShiftAssignment.end_date.isnull()))
			& (ShiftAssignment.employee.isin(list(all_emp_names)))
		)
		.distinct()
	).run(pluck="employee")

	busy = set(busy_rows or [])
	available = sorted(all_emp_names - busy)
	return {"employees": [{"name": e} for e in available]}
