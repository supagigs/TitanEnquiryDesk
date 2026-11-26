"""Whitelisted desk APIs. Every call checks the desk role and lead access on the server."""

import frappe

from titan_desk import zoho
from titan_desk.events import log_event
from titan_desk.permissions import is_manager, require_desk_user, require_lead_access, require_manager


@frappe.whitelist()
def get_boot():
	require_desk_user()
	s = frappe.get_single("Titan Desk Settings")
	return {
		"user": frappe.session.user,
		"full_name": frappe.utils.get_fullname(frappe.session.user),
		"roles": [r for r in frappe.get_roles() if r.startswith("Titan") or r == "System Manager"],
		"is_manager": is_manager(),
		"supervised_mode": supervised_mode_active(s),
		"zoho_mode": s.zoho_mode,
		"crm_installed": bool(frappe.db.exists("DocType", "CRM Lead")),
		"whatsapp_installed": bool(frappe.db.exists("DocType", "WhatsApp Message")),
	}


def supervised_mode_active(s=None):
	s = s or frappe.get_single("Titan Desk Settings")
	if not s.supervised_mode:
		return False
	if not s.supervised_start or not s.supervised_weeks:
		return True
	return frappe.utils.date_diff(frappe.utils.today(), s.supervised_start) < int(s.supervised_weeks) * 7


@frappe.whitelist(methods=["POST"])
def take_over(lead):
	require_lead_access(lead)
	frappe.db.set_value("CRM Lead", lead, {"lead_owner": frappe.session.user, "titan_ai_status": "Paused (human)"})
	log_event("Taken over", lead)
	zoho.push_lead(lead)
	return _lead_state(lead)


@frappe.whitelist(methods=["POST"])
def toggle_ai(lead):
	require_lead_access(lead)
	cur = frappe.db.get_value("CRM Lead", lead, "titan_ai_status")
	new = "Paused" if cur == "Active" else "Active"
	frappe.db.set_value("CRM Lead", lead, "titan_ai_status", new)
	log_event("AI paused" if new == "Paused" else "AI resumed", lead)
	zoho.push_lead(lead)
	return _lead_state(lead)


@frappe.whitelist(methods=["POST"])
def assign(lead, user):
	require_lead_access(lead)
	if user and user != frappe.session.user and not is_manager():
		frappe.throw("Only a Titan Sales Manager can assign leads to someone else.", frappe.PermissionError)
	if user and not frappe.db.exists("User", {"name": user, "enabled": 1}):
		frappe.throw("Unknown user.")
	frappe.db.set_value("CRM Lead", lead, "lead_owner", user or None)
	log_event("Assigned", lead, {"to": user})
	zoho.push_lead(lead)
	return _lead_state(lead)


@frappe.whitelist(methods=["POST"])
def start_zoho_import(from_date, to_date):
	require_manager()
	if "Titan Desk Admin" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
		frappe.throw("Only a Titan Desk Admin can import from Zoho.", frappe.PermissionError)
	if frappe.utils.getdate(from_date) > frappe.utils.getdate(to_date):
		frappe.throw("From date must be before To date.")
	imp = frappe.get_doc({"doctype": "Titan Zoho Import", "from_date": from_date, "to_date": to_date, "status": "Queued"}).insert()
	frappe.enqueue("titan_desk.zoho.run_import", import_name=imp.name, queue="long", enqueue_after_commit=True)
	return imp.name


def _lead_state(lead):
	return frappe.db.get_value("CRM Lead", lead, ["name", "lead_owner", "titan_ai_status", "titan_escalation_reason", "lead_temperature"], as_dict=True)
