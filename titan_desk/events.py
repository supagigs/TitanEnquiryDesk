import json

import frappe


def log_event(event, lead=None, data=None, user=None):
	frappe.get_doc({
		"doctype": "Titan Desk Event", "event": event, "lead": lead,
		"user": user or frappe.session.user, "data": json.dumps(data or {}, default=str),
	}).insert(ignore_permissions=True)
	if lead:
		frappe.publish_realtime("titan_desk_update", {"lead": lead, "event": event}, after_commit=True)


def on_whatsapp_message(doc, method=None):
	if doc.reference_doctype != "CRM Lead" or not doc.reference_name:
		return
	if doc.type == "Incoming":
		frappe.db.set_value("CRM Lead", doc.reference_name, "titan_last_inbound", doc.creation, update_modified=False)
		log_event("Message in", doc.reference_name, {"message": doc.name})
		from titan_desk.escalation import evaluate_message
		frappe.db.set_value("CRM Lead", doc.reference_name, {"titan_followup_count": 0, "titan_next_followup": None}, update_modified=False)
		evaluate_message(doc.reference_name, doc.message or "", has_attachment=bool(doc.attach))
	else:
		log_event("Message out", doc.reference_name, {"message": doc.name})
		from titan_desk.followups import schedule_next
		if frappe.db.get_value("CRM Lead", doc.reference_name, "titan_ai_status") == "Active":
			schedule_next(doc.reference_name)


def on_lead_insert(doc, method=None):
	log_event("Lead created", doc.name, {"source": doc.source})
	if doc.get("titan_ai_status") in (None, "", "Active"):
		frappe.db.set_value("CRM Lead", doc.name, {"titan_ai_status": "Active", "titan_next_followup": frappe.utils.now_datetime()}, update_modified=False)


def on_lead_update(doc, method=None):
	before = doc.get_doc_before_save()
	if before and before.lead_temperature != doc.lead_temperature and doc.lead_temperature == "Hot":
		from titan_desk.escalation import apply_rules_for_temperature
		apply_rules_for_temperature(doc.name, "Hot")
