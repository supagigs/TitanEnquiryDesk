"""Zoho CRM access behind one interface.

Release 1 ships only the simulator. FlowForge will later provide the live
Zoho (India DC) sync and call the same `upsert_lead_from_zoho` entry point.
"""

import json
import random
import re

import frappe
from frappe.utils import add_to_date, now_datetime


PUSHED_FIELDS = ["status", "lead_owner", "lead_temperature", "titan_ai_status", "titan_escalation_reason", "titan_ai_summary", "titan_spec_completeness"]


class ZohoClient:
	def list_leads(self, created_from, created_to):
		raise NotImplementedError

	def list_modified_since(self, since):
		raise NotImplementedError

	def push_lead(self, zoho_id, values):
		raise NotImplementedError


class SimulatedZohoClient(ZohoClient):
	"""Reads and writes `Titan Zoho Sim Record`, which stands in for Zoho Leads."""

	FIELDS = ["zoho_id", "company", "contact_name", "mobile", "email", "lead_source", "description", "zoho_owner", "lead_status", "created_time", "modified_time"]

	def list_leads(self, created_from, created_to):
		return frappe.get_all("Titan Zoho Sim Record", filters={"created_time": ["between", [created_from, created_to]]}, fields=self.FIELDS, order_by="created_time asc")

	def list_modified_since(self, since):
		return frappe.get_all("Titan Zoho Sim Record", filters={"modified_time": [">", since]}, fields=self.FIELDS, order_by="modified_time asc")

	def push_lead(self, zoho_id, values):
		rec = frappe.get_doc("Titan Zoho Sim Record", zoho_id)
		current = json.loads(rec.desk_fields or "{}")
		current.update(values)
		rec.desk_fields = json.dumps(current, default=str)
		rec.save(ignore_permissions=True)


def get_client():
	mode = frappe.db.get_single_value("Titan Desk Settings", "zoho_mode") or "Simulated"
	if mode == "Simulated":
		return SimulatedZohoClient()
	return None


def _split_name(full):
	parts = (full or "").strip().split(" ", 1)
	return parts[0] or "Unknown", parts[1] if len(parts) > 1 else ""


def upsert_lead_from_zoho(z, direction="Pull"):
	"""Idempotent on Zoho ID. Returns (lead_name, 'created'|'updated'|'skipped')."""
	if not frappe.db.exists("DocType", "CRM Lead"):
		frappe.throw("Frappe CRM is not installed on this site.")
	existing = frappe.db.get_value("CRM Lead", {"titan_zoho_id": z["zoho_id"]}, "name")
	first, last = _split_name(z.get("contact_name"))
	values = {
		"first_name": first, "last_name": last, "organization": z.get("company"),
		"mobile_no": z.get("mobile"), "email": z.get("email"),
	}
	try:
		if existing:
			doc = frappe.get_doc("CRM Lead", existing)
			changed = [k for k, v in values.items() if v and doc.get(k) != v]
			if not changed:
				_log(direction, "Skipped", z["zoho_id"], existing)
				return existing, "skipped"
			doc.update({k: values[k] for k in changed})
			doc.flags.titan_from_zoho = True
			doc.save(ignore_permissions=True)
			_log(direction, "Success", z["zoho_id"], existing, changed)
			return existing, "updated"
		doc = frappe.get_doc({"doctype": "CRM Lead", **values, "titan_zoho_id": z["zoho_id"], "titan_ai_status": "Active"})
		if z.get("lead_source") and frappe.db.exists("CRM Lead Source", z["lead_source"]):
			doc.source = z["lead_source"]
		doc.flags.titan_from_zoho = True
		doc.insert(ignore_permissions=True)
		if z.get("description"):
			frappe.get_doc({"doctype": "FCRM Note", "title": "Enquiry (from Zoho)", "content": z["description"], "reference_doctype": "CRM Lead", "reference_docname": doc.name}).insert(ignore_permissions=True) if frappe.db.exists("DocType", "FCRM Note") else None
		_log(direction, "Success", z["zoho_id"], doc.name, list(values))
		return doc.name, "created"
	except Exception as e:
		_log(direction, "Failed", z["zoho_id"], existing, error=str(e))
		raise


def _log(direction, status, zoho_id, lead=None, changed=None, error=None):
	frappe.get_doc({"doctype": "Titan Zoho Sync Log", "direction": direction, "status": status, "zoho_id": zoho_id, "lead": lead,
		"fields_changed": ", ".join(changed or []), "error": error}).insert(ignore_permissions=True)


def run_import(import_name):
	imp = frappe.get_doc("Titan Zoho Import", import_name)
	client = get_client()
	imp.db_set("status", "Running")
	counts = {"created": 0, "updated": 0, "skipped": 0}
	try:
		rows = client.list_leads(f"{imp.from_date} 00:00:00", f"{imp.to_date} 23:59:59")
		imp.db_set("total", len(rows))
		for z in rows:
			_, result = upsert_lead_from_zoho(z, "Import")
			counts[result] += 1
		imp.db_set({"status": "Completed", "created_count": counts["created"], "updated_count": counts["updated"], "skipped_count": counts["skipped"]})
	except Exception as e:
		imp.db_set({"status": "Failed", "error": str(e)[:500]})
		raise
	return counts


def scheduled_pull():
	s = frappe.get_single("Titan Desk Settings")
	if s.zoho_mode != "Simulated" or not s.zoho_auto_pull:
		return
	since = s.zoho_last_pull or add_to_date(now_datetime(), days=-1)
	for z in get_client().list_modified_since(since):
		upsert_lead_from_zoho(z)
	frappe.db.set_single_value("Titan Desk Settings", "zoho_last_pull", now_datetime())


def push_lead(lead):
	"""Send desk fields back to Zoho (simulated). Called after desk actions."""
	zid = frappe.db.get_value("CRM Lead", lead, "titan_zoho_id")
	client = get_client()
	if not zid or not client:
		return
	values = frappe.db.get_value("CRM Lead", lead, PUSHED_FIELDS, as_dict=True)
	try:
		client.push_lead(zid, values)
		_log("Push", "Success", zid, lead, PUSHED_FIELDS)
	except Exception as e:
		_log("Push", "Failed", zid, lead, error=str(e))


SAMPLE = [
	("Shreeji Foundations", "Raj Patil", "Pune", "IndiaMART", "Need 1200 dia clay bucket for our rig, 2 nos. What is the rate?"),
	("Vardhan Valves", "Amit Shah", "Ahmedabad", "IndiaMART", "Requirement of WN flanges 12 inch A105, 40 nos with 3.1 cert"),
	("Konkan Infra Piling", "Sameer Desai", "Ratnagiri", "Google Ads", "Core barrel 900mm for rock"),
	("Petrochem Engineering Works", "N. Iyer", "Vadodara", "Email", "Please quote 6 nos forged rings F51 as per attached drawing. UT + IGC test required."),
	("Gearline Industries", "Pooja Kulkarni", "Nashik", "IndiaMART", "4140 round bar 300 dia required"),
	("Deccan Piling Co.", "Ravi Reddy", "Hyderabad", "IndiaMART", "CFA 600 mm 3 nos. Can you deliver in 2 weeks?"),
	("Sai Pharma Equipments", "Kiran Joshi", "Thane", "Website", "SO flange 2 inch 316L 150# 200 nos"),
	("R. Kulkarni", "R. Kulkarni", "Mumbai", "Google Ads", "I am a student, need info on forging process for project"),
]


@frappe.whitelist()
def seed_simulated_zoho(days=30):
	"""Create sample Zoho leads in the simulator (Admin only). Never touches real Zoho."""
	from titan_desk.permissions import require_manager
	require_manager()
	if "Titan Desk Admin" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
		frappe.throw("Only a Titan Desk Admin can seed the Zoho simulator.", frappe.PermissionError)
	now = now_datetime()
	made = 0
	for i, (company, contact, city, src, desc) in enumerate(SAMPLE):
		zid = f"ZSIM-{4000 + i}"
		if frappe.db.exists("Titan Zoho Sim Record", zid):
			continue
		created = add_to_date(now, days=-random.randint(0, int(days)), hours=-random.randint(0, 23))
		frappe.get_doc({"doctype": "Titan Zoho Sim Record", "zoho_id": zid, "company": company, "contact_name": contact,
			"mobile": f"+91 98{random.randint(10000000, 99999999)}", "email": f"{re.sub(r'[^a-z0-9]+', '.', contact.lower()).strip('.')}@example.com",
			"lead_source": src, "description": f"{desc} ({city})", "zoho_owner": "Mirza", "lead_status": "New",
			"created_time": created, "modified_time": created}).insert(ignore_permissions=True)
		made += 1
	return made
