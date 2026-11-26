"""Install / migrate helpers. Everything here is idempotent."""

import re

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

ROLES = {
	"Titan Sales User": "Uses the desk: reads and replies to enquiries, approves replies on own leads, books calls.",
	"Titan Sales Manager": "All leads, reassignment, approvals, escalation rules and cadences, reports.",
	"Titan Desk Admin": "Desk settings, Zoho connection and import, spec templates, retention.",
}

LEAD_FIELDS = [
	dict(fieldname="titan_section", fieldtype="Section Break", label="Titan Enquiry Desk", insert_after="facebook", collapsible=1),
	dict(fieldname="titan_ai_status", fieldtype="Select", label="AI status", options="Active\nPaused\nPaused (human)\nPaused (escalated)\nPaused (call booked)\nStopped", default="Active", insert_after="titan_section", in_standard_filter=1),
	dict(fieldname="titan_product_line", fieldtype="Link", label="Product line", options="Titan Spec Template", insert_after="titan_ai_status"),
	dict(fieldname="titan_spec_json", fieldtype="JSON", label="Captured requirement", insert_after="titan_product_line"),
	dict(fieldname="titan_spec_completeness", fieldtype="Percent", label="Requirement captured", read_only=1, insert_after="titan_spec_json"),
	dict(fieldname="titan_cb1", fieldtype="Column Break", insert_after="titan_spec_completeness"),
	dict(fieldname="titan_escalation_reason", fieldtype="Data", label="Escalation reason", insert_after="titan_cb1"),
	dict(fieldname="titan_ai_summary", fieldtype="Small Text", label="AI summary", insert_after="titan_escalation_reason"),
	dict(fieldname="titan_next_followup", fieldtype="Datetime", label="Next follow-up", insert_after="titan_ai_summary"),
	dict(fieldname="titan_followup_count", fieldtype="Int", label="Follow-ups sent", default="0", read_only=1, insert_after="titan_next_followup"),
	dict(fieldname="titan_last_inbound", fieldtype="Datetime", label="Last customer message", read_only=1, insert_after="titan_followup_count"),
	dict(fieldname="titan_zoho_id", fieldtype="Data", label="Zoho lead ID", read_only=1, unique=1, insert_after="titan_last_inbound"),
]

SPEC_TEMPLATES = {
	"Drilling tool": ["Tool type", "Diameter (mm)", "Rig model / max torque", "Soil condition", "Quantity", "Site location", "Required by"],
	"Forging": ["Component", "Material grade", "Dimensions or drawing", "Weight per piece", "Quantity", "Heat treatment & tests", "Required by"],
	"Flange": ["Type & size", "Material grade", "Pressure class", "Quantity", "Test certificate", "Delivery location", "Required by"],
	"Machining & fabrication": ["Drawing", "Material", "Tolerances", "Quantity", "Finish", "Delivery location", "Required by"],
}

ESCALATION_RULES = [
	("Price asked", "Keyword", "price\nrate\ncost\nquote\nquotation\ndiscount", "Asked for price", 10),
	("Delivery date asked", "Keyword", "delivery date\nhow soon\nby when\nlead time\ndispatch", "Asked for delivery date", 20),
	("Complaint", "Keyword", "complaint\ndefect\nproblem with\nnot working\nrejected", "Complaint", 5),
	("Drawing received", "Attachment received", None, "Drawing to review", 15),
	("Hot lead", "Lead temperature", None, "Hot lead", 30),
]


def after_install():
	after_migrate()


def after_migrate():
	ensure_roles()
	ensure_lead_fields()
	ensure_permissions()
	ensure_defaults()


# CRM access the desk roles need, added as Custom DocPerm (visible in Role Permission Manager).
CRM_PERMS = {
	"CRM Lead": {"Titan Sales User": dict(read=1, write=1, create=1, report=1, email=1, share=1),
		"Titan Sales Manager": dict(read=1, write=1, create=1, delete=1, report=1, export=1, email=1, share=1),
		"Titan Desk Admin": dict(read=1, write=1, create=1, report=1, export=1)},
	"CRM Lead Status": {r: dict(read=1) for r in ROLES},
	"CRM Lead Source": {r: dict(read=1) for r in ROLES},
	"WhatsApp Message": {r: dict(read=1, create=1) for r in ROLES},
	"WhatsApp Templates": {r: dict(read=1) for r in ROLES},
}


def ensure_permissions():
	from frappe.permissions import add_permission, update_permission_property
	for doctype, roles in CRM_PERMS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		for role, props in roles.items():
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
				add_permission(doctype, role, 0)
			for k, v in props.items():
				update_permission_property(doctype, role, 0, k, v, validate=False)


def ensure_roles():
	for role, desc in ROLES.items():
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1, "description": desc}).insert(ignore_permissions=True)


def ensure_lead_fields():
	if frappe.db.exists("DocType", "CRM Lead"):
		create_custom_fields({"CRM Lead": LEAD_FIELDS}, update=True)


def ensure_defaults():
	for line, labels in SPEC_TEMPLATES.items():
		if not frappe.db.exists("Titan Spec Template", line):
			frappe.get_doc({
				"doctype": "Titan Spec Template", "product_line": line, "enabled": 1,
				"fields": [{"fieldname": clean(l), "label": l, "required": 1, "ask_order": i + 1} for i, l in enumerate(labels)],
			}).insert(ignore_permissions=True)
	for name, trigger, kw, reason, prio in ESCALATION_RULES:
		if not frappe.db.exists("Titan Escalation Rule", name):
			frappe.get_doc({
				"doctype": "Titan Escalation Rule", "rule_name": name, "trigger": trigger, "keywords": kw,
				"temperature": "Hot" if trigger == "Lead temperature" else None, "reason_label": reason, "priority": prio,
				"action_assign": 1, "action_notify": 1, "action_pause_ai": 1,
			}).insert(ignore_permissions=True)
	for row in frappe.get_all("Titan Spec Field", fields=["name", "label", "fieldname"]):
		if row.fieldname != clean(row.label) and row.fieldname == frappe.scrub(row.label):
			frappe.db.set_value("Titan Spec Field", row.name, "fieldname", clean(row.label))
	s = frappe.get_single("Titan Desk Settings")
	changed = False
	for field, value in {"supervised_start": frappe.utils.today(), "zoho_mode": "Simulated", "whatsapp_mode": "Simulated"}.items():
		if not s.get(field):
			s.set(field, value)
			changed = True
	if changed:
		s.save(ignore_permissions=True)


def before_uninstall():
	"""Remove only Titan's own custom fields. CRM data stays."""
	for f in LEAD_FIELDS:
		name = f"CRM Lead-{f['fieldname']}"
		if frappe.db.exists("Custom Field", name):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True)


def clean(label):
	return re.sub(r"[^a-z0-9]+", "_", (label or "").lower()).strip("_")
