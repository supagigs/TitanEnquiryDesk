import frappe

from titan_desk.events import log_event


def assign_internal(args):
	"""Assign after the desk has already authorised the user (frappe 16 `_add`, with a fallback)."""
	try:
		from frappe.desk.form.assign_to import _add
		return _add(args, ignore_permissions=True)
	except ImportError:
		from frappe.desk.form.assign_to import add
		return add(args)


def _rules(trigger):
	return frappe.get_all("Titan Escalation Rule", filters={"enabled": 1, "trigger": trigger},
		fields=["name", "keywords", "temperature", "reason_label", "action_assign", "assign_to", "action_notify", "action_pause_ai"],
		order_by="priority asc")


def match_keywords(text, keywords):
	t = (text or "").lower()
	return any(k.strip().lower() in t for k in (keywords or "").splitlines() if k.strip())


def evaluate_message(lead, text, has_attachment=False):
	"""Returns the first matching rule name (or None) and applies its actions."""
	for r in _rules("Keyword"):
		if match_keywords(text, r.keywords):
			return escalate(lead, r)
	if has_attachment:
		for r in _rules("Attachment received"):
			return escalate(lead, r)
	return None


def apply_rules_for_temperature(lead, temperature):
	for r in _rules("Lead temperature"):
		if r.temperature == temperature:
			return escalate(lead, r)


def escalate(lead, rule):
	values = {"titan_escalation_reason": rule.reason_label}
	if rule.action_pause_ai:
		values["titan_ai_status"] = "Paused (escalated)"
	frappe.db.set_value("CRM Lead", lead, values)
	if rule.action_assign and rule.assign_to:
		if not frappe.db.exists("ToDo", {"reference_type": "CRM Lead", "reference_name": lead, "allocated_to": rule.assign_to, "status": "Open"}):
			assign_internal({"doctype": "CRM Lead", "name": lead, "assign_to": [rule.assign_to], "description": rule.reason_label})
	log_event("Escalated", lead, {"rule": rule.name, "reason": rule.reason_label})
	return rule.name
