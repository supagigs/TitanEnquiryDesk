"""Follow-up scheduler (runs every 15 minutes).

Without FlowForge there is no AI writer, so follow-ups use the message in
Titan Desk Settings, filled with the lead's missing requirement fields.
In supervised mode each follow-up waits in Titan Reply Approval.
"""

import json

import frappe
from frappe.utils import add_to_date, cint, get_datetime, get_time, now_datetime

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def cadence(user):
	s = frappe.get_cached_doc("Titan Desk Settings")
	hours, max_n = s.default_followup_hours, s.default_max_followups
	p = frappe.db.get_value("Titan Follow-up Preference", user, ["followup_hours", "max_followups", "enabled", "quiet_start", "quiet_end"], as_dict=True) if user else None
	if p and p.enabled:
		hours = p.followup_hours or hours
		max_n = p.max_followups or max_n
	return [int(h) for h in str(hours or "24").split(",") if h.strip()], cint(max_n) or 4, p


def in_business_hours(dt=None, pref=None):
	s = frappe.get_cached_doc("Titan Desk Settings")
	dt = get_datetime(dt or now_datetime())
	days = [d.strip() for d in (s.working_days or "Mon,Tue,Wed,Thu,Fri,Sat").split(",")]
	if DAYS[dt.weekday()] not in days:
		return False
	t = dt.time()
	if s.business_hours_start and s.business_hours_end and not (get_time(s.business_hours_start) <= t <= get_time(s.business_hours_end)):
		return False
	if pref and pref.quiet_start and pref.quiet_end and get_time(pref.quiet_start) <= t <= get_time(pref.quiet_end):
		return False
	return True


def schedule_next(lead, from_time=None):
	owner, count = frappe.db.get_value("CRM Lead", lead, ["lead_owner", "titan_followup_count"])
	hours, max_n, _ = cadence(owner)
	count = cint(count)
	nxt = None if count >= max_n else add_to_date(from_time or now_datetime(), hours=hours[min(count, len(hours) - 1)])
	frappe.db.set_value("CRM Lead", lead, "titan_next_followup", nxt, update_modified=False)
	return nxt


def draft_for(lead):
	from titan_desk.desk import missing_fields
	l = frappe.db.get_value("CRM Lead", lead, ["first_name", "titan_product_line", "titan_spec_json"], as_dict=True)
	spec = json.loads(l.titan_spec_json or "{}") if l.titan_spec_json else {}
	missing = missing_fields(l.titan_product_line, spec)[:2]
	msg = frappe.db.get_single_value("Titan Desk Settings", "followup_message") or "Hello {first_name}, following up on your enquiry. Could you share {missing}?"
	return msg.format(first_name=l.first_name or "there", missing=" and ".join(m.lower() for m in missing) or "a few more details")


def run():
	from titan_desk.api import supervised_mode_active
	from titan_desk.desk import _insert_whatsapp, in_session_window
	now = now_datetime()
	due = frappe.get_all("CRM Lead", filters={"titan_ai_status": "Active", "titan_next_followup": ["<=", now]}, fields=["name", "lead_owner", "titan_followup_count"], limit=200)
	supervised = supervised_mode_active()
	for l in due:
		_, max_n, pref = cadence(l.lead_owner)
		if cint(l.titan_followup_count) >= max_n:
			frappe.db.set_value("CRM Lead", l.name, "titan_next_followup", None, update_modified=False)
			continue
		if not in_business_hours(now, pref):
			continue
		if frappe.db.exists("Titan Reply Approval", {"lead": l.name, "status": "Pending"}):
			continue
		text = draft_for(l.name)
		if supervised:
			frappe.get_doc({"doctype": "Titan Reply Approval", "lead": l.name, "channel": "WhatsApp", "draft": text, "source": "Follow-up scheduler"}).insert(ignore_permissions=True)
		else:
			tpl = None if in_session_window(l.name) else frappe.db.get_single_value("Titan Desk Settings", "followup_template")
			if not in_session_window(l.name) and not tpl:
				continue
			_insert_whatsapp(l.name, text=None if tpl else text, template=tpl)
		frappe.db.set_value("CRM Lead", l.name, {"titan_followup_count": cint(l.titan_followup_count) + 1}, update_modified=False)
		schedule_next(l.name, now)
