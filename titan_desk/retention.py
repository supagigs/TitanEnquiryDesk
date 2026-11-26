import frappe
from frappe.utils import add_days, now_datetime

PURGED = ["Titan Desk Event", "Titan Zoho Sync Log", "Titan Reply Approval"]


def purge_old_records():
	days = frappe.db.get_single_value("Titan Desk Settings", "retention_days") or 90
	cutoff = add_days(now_datetime(), -int(days))
	for dt in PURGED:
		filters = {"creation": ["<", cutoff]}
		if dt == "Titan Reply Approval":
			filters["status"] = ["!=", "Pending"]
		frappe.db.delete(dt, filters)
