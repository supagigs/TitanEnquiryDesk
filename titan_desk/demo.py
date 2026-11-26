"""Demo data for staging: simulated Zoho leads plus WhatsApp conversations (simulated mode only)."""

import json

import frappe

from titan_desk import zoho
from titan_desk.permissions import require_manager

SPECS = {
	"Shreeji Foundations": ("Drilling tool", {"tool_type": "Bucket for clay, double bottom", "diameter_mm": "1200", "rig_model_max_torque": "220 kN (HD)", "soil_condition": "Soft, watery clay", "quantity": "2", "site_location": "Hinjewadi, Pune"}, "Hot"),
	"Vardhan Valves": ("Flange", {"type_size": 'Weld-neck, 12"', "material_grade": "ASTM A105", "quantity": "40", "test_certificate": "EN 10204 3.1", "delivery_location": "Ahmedabad"}, "Hot"),
	"Konkan Infra Piling": ("Drilling tool", {"tool_type": "Core barrel for rock", "diameter_mm": "900", "soil_condition": "Hard rock", "quantity": "1"}, "Warm"),
	"Gearline Industries": ("Forging", {"component": "Round bar / gear blanks", "material_grade": "AISI 4140", "dimensions_or_drawing": "Ø300"}, "Warm"),
	"Sai Pharma Equipments": ("Flange", {"type_size": 'Slip-on, 2"', "material_grade": "SS 316L", "pressure_class": "150#", "quantity": "200"}, "Warm"),
}


@frappe.whitelist(methods=["POST"])
def seed_demo():
	require_manager()
	s = frappe.get_single("Titan Desk Settings")
	if s.whatsapp_mode != "Simulated" or s.zoho_mode != "Simulated":
		frappe.throw("Demo data can only be loaded when Zoho and WhatsApp are both in Simulated mode.")
	frappe.flags.in_titan_seed = True
	roles = frappe.get_roles()
	if "Titan Desk Admin" not in roles and "System Manager" not in roles:
		frappe.throw("Only a Titan Desk Admin can load demo data.", frappe.PermissionError)
	for src in ("IndiaMART", "Google Ads", "Website", "Email"):
		if frappe.db.exists("DocType", "CRM Lead Source") and not frappe.db.exists("CRM Lead Source", src):
			frappe.get_doc({"doctype": "CRM Lead Source", "source_name": src}).insert(ignore_permissions=True)
	zoho.seed_simulated_zoho(days=14)
	for z in frappe.get_all("Titan Zoho Sim Record", fields=zoho.SimulatedZohoClient.FIELDS):
		lead, result = zoho.upsert_lead_from_zoho(z, "Import")
		if result != "created":
			continue
		if z["company"] in SPECS:
			line, spec, temp = SPECS[z["company"]]
			from titan_desk.desk import completeness
			frappe.db.set_value("CRM Lead", lead, {"titan_product_line": line, "titan_spec_json": json.dumps(spec), "titan_spec_completeness": completeness(line, spec), "lead_temperature": temp})
		if frappe.db.exists("DocType", "WhatsApp Message"):
			from titan_desk.desk import _insert_whatsapp
			_insert_whatsapp(lead, text=(z.get("description") or "").rsplit(" (", 1)[0], incoming=True)
	return frappe.db.count("CRM Lead", {"titan_zoho_id": ["is", "set"]})
