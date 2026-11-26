"""Read and write APIs for the Titan Enquiry Desk SPA.

All functions are whitelisted, check the desk role on the server and, for
lead-level actions, whether the user may act on that lead.
"""

import json

import frappe
from frappe.utils import add_days, add_to_date, cint, get_datetime, getdate, now_datetime, nowdate, time_diff_in_hours

from titan_desk import zoho
from titan_desk.api import supervised_mode_active
from titan_desk.events import log_event
from titan_desk.permissions import can_act_on_lead, is_manager, require_desk_user, require_lead_access, require_manager

OPEN = ["New", "Contacted", "Nurture", "Qualified"]
WA = "WhatsApp Message"


# ---------------------------------------------------------------- helpers
def _has(doctype):
	return bool(frappe.db.exists("DocType", doctype))




def _leads(filters=None, fields=None, limit=200, order_by="modified desc"):
	f = fields or ["name", "lead_name", "first_name", "organization", "mobile_no", "email", "source", "status", "lead_owner",
		"lead_temperature", "titan_ai_status", "titan_product_line", "titan_spec_json", "titan_spec_completeness",
		"titan_escalation_reason", "titan_ai_summary", "titan_next_followup", "titan_last_inbound", "modified", "creation"]
	rows = frappe.get_all("CRM Lead", filters=filters or {}, fields=f, limit=limit, order_by=order_by)
	if is_manager():
		return rows
	u = frappe.session.user
	return [r for r in rows if not r.lead_owner or r.lead_owner == u]


def _spec(lead_row):
	try:
		return json.loads(lead_row.get("titan_spec_json") or "{}") or {}
	except Exception:
		return {}


def _template_fields(product_line):
	if not product_line or not frappe.db.exists("Titan Spec Template", product_line):
		return []
	return frappe.get_all("Titan Spec Field", filters={"parent": product_line, "parenttype": "Titan Spec Template"},
		fields=["fieldname", "label", "required"], order_by="ask_order asc, idx asc")


def completeness(product_line, spec):
	fields = [f for f in _template_fields(product_line) if f.required]
	if not fields:
		return 0
	have = sum(1 for f in fields if str(spec.get(f.fieldname) or "").strip())
	return round(100 * have / len(fields))


def missing_fields(product_line, spec):
	return [f.label for f in _template_fields(product_line) if f.required and not str(spec.get(f.fieldname) or "").strip()]


def _last_messages(lead_names):
	out = {}
	if not lead_names or not _has(WA):
		return out
	for m in frappe.get_all(WA, filters={"reference_doctype": "CRM Lead", "reference_name": ["in", lead_names]},
			fields=["reference_name", "type", "message", "creation", "owner"], order_by="creation desc", limit=len(lead_names) * 20):
		out.setdefault(m.reference_name, m)
	return out


def _settings():
	return frappe.get_cached_doc("Titan Desk Settings")


def in_session_window(lead):
	last = frappe.db.get_value("CRM Lead", lead, "titan_last_inbound")
	return bool(last) and time_diff_in_hours(now_datetime(), last) < 24


# ---------------------------------------------------------------- Today
@frappe.whitelist()
def get_today():
	require_desk_user()
	s = _settings()
	leads = _leads({"status": ["not in", ["Converted", "Lost", "Junk"]]} if _has("CRM Lead Status") else None)
	needs = [l for l in leads if (l.titan_ai_status or "").startswith("Paused (escalated)") or l.titan_escalation_reason]
	needs.sort(key=lambda l: ({"Hot": 0, "Warm": 1}.get(l.lead_temperature, 2), l.modified))
	ai_active = [l for l in leads if l.titan_ai_status == "Active"]
	week_start = getdate(add_days(nowdate(), -getdate(nowdate()).weekday()))
	week = []
	for i in range(7):
		d = add_days(week_start, i)
		week.append({"date": str(d), "count": frappe.db.count("CRM Lead", {"creation": ["between", [f"{d} 00:00:00", f"{d} 23:59:59"]]}) if getdate(d) <= getdate() else None})
	sources = {}
	for l in leads:
		sources[l.source or "Other"] = sources.get(l.source or "Other", 0) + 1
	lines = {}
	for l in leads:
		if l.titan_product_line:
			lines[l.titan_product_line] = lines.get(l.titan_product_line, 0) + 1
	week_from = f"{week_start} 00:00:00"
	goals = [
		{"label": "Hot leads called", "done": frappe.db.count("Event", {"creation": [">=", week_from], "subject": ["like", "Call%"]}), "target": s.goal_hot_calls},
		{"label": "Specs fully captured", "done": len([l for l in leads if (l.titan_spec_completeness or 0) >= 100]), "target": s.goal_specs_complete},
		{"label": "Follow-ups answered", "done": frappe.db.count("Titan Desk Event", {"event": "Message in", "creation": [">=", week_from]}), "target": s.goal_followups_answered},
	]
	pending = frappe.db.count("Titan Reply Approval", {"status": "Pending"})
	last = _last_messages([l.name for l in needs + ai_active])
	def card(l):
		spec = _spec(l)
		return {**l, "spec": spec, "missing": missing_fields(l.titan_product_line, spec), "last": last.get(l.name)}
	return {
		"date": nowdate(), "user": frappe.utils.get_fullname(), "needs": [card(l) for l in needs[:20]],
		"ai_active": [card(l) for l in ai_active[:20]], "open_count": len(leads), "hot_count": len([l for l in leads if l.lead_temperature == "Hot"]),
		"pending_approvals": pending, "week": week, "sources": sources, "lines": lines, "goals": goals,
		"response": _response_stats(), "supervised": supervised_mode_active(s), "setup": get_setup_progress(),
	}


def _response_stats():
	"""Median minutes from a lead's first inbound message to Titan's first outbound one, this week."""
	if not _has(WA):
		return {"median_minutes": None, "count": 0}
	since = add_days(nowdate(), -7)
	rows = frappe.db.sql(
		"""select i.reference_name, min(i.creation) first_in,
			(select min(o.creation) from `tabWhatsApp Message` o where o.reference_name=i.reference_name and o.type='Outgoing' and o.creation>=min(i.creation)) first_out
		from `tabWhatsApp Message` i where i.reference_doctype='CRM Lead' and i.type='Incoming' and i.creation>=%s group by i.reference_name""",
		since, as_dict=True)
	mins = sorted((get_datetime(r.first_out) - get_datetime(r.first_in)).total_seconds() / 60 for r in rows if r.first_out)
	return {"median_minutes": round(mins[len(mins) // 2], 1) if mins else None, "count": len(rows), "answered": len(mins)}


# ---------------------------------------------------------------- Inbox
@frappe.whitelist()
def get_inbox(view="Needs human", search=None):
	require_desk_user()
	filters = {}
	if view == "Needs human":
		filters["titan_escalation_reason"] = ["is", "set"]
	elif view == "AI active":
		filters["titan_ai_status"] = "Active"
	leads = _leads(filters, limit=300)
	if search:
		q = search.lower()
		leads = [l for l in leads if q in (l.lead_name or "").lower() or q in (l.organization or "").lower() or q in (l.mobile_no or "")]
	last = _last_messages([l.name for l in leads])
	for l in leads:
		l.last = last.get(l.name)
	leads.sort(key=lambda l: get_datetime((l.last or {}).get("creation") or l.modified), reverse=True)
	return leads


@frappe.whitelist()
def get_conversation(lead):
	require_lead_access(lead)
	l = frappe.get_doc("CRM Lead", lead)
	msgs = []
	if _has(WA):
		for m in frappe.get_all(WA, filters={"reference_doctype": "CRM Lead", "reference_name": lead},
				fields=["name", "type", "message", "status", "creation", "owner", "content_type", "attach", "use_template", "template"], order_by="creation asc"):
			msgs.append({"channel": "WhatsApp", "out": m.type == "Outgoing", "text": m.message or (m.template and f"[Template: {m.template}]") or "",
				"status": m.status, "at": m.creation, "by": frappe.utils.get_fullname(m.owner) if m.type == "Outgoing" else None, "attach": m.attach})
	for c in frappe.get_all("Communication", filters={"reference_doctype": "CRM Lead", "reference_name": lead, "communication_medium": "Email"},
			fields=["subject", "content", "sent_or_received", "creation", "sender_full_name"], order_by="creation asc"):
		msgs.append({"channel": "Email", "out": c.sent_or_received == "Sent", "text": frappe.utils.strip_html(c.content or "")[:2000], "subject": c.subject, "at": c.creation, "by": c.sender_full_name})
	msgs.sort(key=lambda m: get_datetime(m["at"]))
	spec = _spec(l.as_dict())
	tmpl = _template_fields(l.titan_product_line)
	return {
		"lead": {k: l.get(k) for k in ["name", "lead_name", "organization", "mobile_no", "email", "source", "status", "lead_owner", "lead_temperature",
			"titan_ai_status", "titan_product_line", "titan_escalation_reason", "titan_ai_summary", "titan_next_followup", "titan_zoho_id"]},
		"spec": [{"fieldname": f.fieldname, "label": f.label, "required": f.required, "value": spec.get(f.fieldname)} for f in tmpl],
		"completeness": completeness(l.titan_product_line, spec),
		"messages": msgs, "in_window": in_session_window(lead),
		"templates": frappe.get_all("WhatsApp Templates", filters={"status": "APPROVED"}, pluck="name") if _has("WhatsApp Templates") else [],
		"product_lines": frappe.get_all("Titan Spec Template", filters={"enabled": 1}, pluck="name"),
		"can_act": can_act_on_lead(l.lead_owner),
	}


@frappe.whitelist(methods=["POST"])
def update_spec(lead, product_line=None, values=None):
	require_lead_access(lead)
	spec = _spec(frappe.db.get_value("CRM Lead", lead, ["titan_spec_json"], as_dict=True))
	if isinstance(values, str):
		values = json.loads(values or "{}")
	spec.update({k: v for k, v in (values or {}).items() if k})
	product_line = product_line or frappe.db.get_value("CRM Lead", lead, "titan_product_line")
	if product_line and not frappe.db.exists("Titan Spec Template", product_line):
		frappe.throw("Unknown product line.")
	frappe.db.set_value("CRM Lead", lead, {"titan_product_line": product_line, "titan_spec_json": json.dumps(spec),
		"titan_spec_completeness": completeness(product_line, spec)})
	zoho.push_lead(lead)
	return get_conversation(lead)


def _wa_mode():
	return _settings().whatsapp_mode or "Simulated"


def _insert_whatsapp(lead, text=None, template=None, incoming=False):
	if not _has(WA):
		frappe.throw("The WhatsApp app is not installed on this site.")
	l = frappe.db.get_value("CRM Lead", lead, ["mobile_no", "lead_name"], as_dict=True)
	if not l.mobile_no:
		frappe.throw("This lead has no mobile number.")
	doc = frappe.get_doc({"doctype": WA, "type": "Incoming" if incoming else "Outgoing", "to": None if incoming else l.mobile_no,
		"from": l.mobile_no if incoming else None, "message": text, "content_type": "text",
		"reference_doctype": "CRM Lead", "reference_name": lead, "message_type": "Template" if template else "Manual",
		"use_template": 1 if template else 0, "template": template})
	s = _settings()
	if not incoming and s.whatsapp_account:
		doc.whatsapp_account = s.whatsapp_account
	if _wa_mode() == "Live":
		doc.insert(ignore_permissions=True)
	else:
		# Simulated: store the message exactly as frappe_whatsapp would, without calling Meta.
		doc.status = "received" if incoming else "Sent"
		doc.message_id = f"sim-{frappe.generate_hash(length=10)}"
		doc.db_insert()
		from titan_desk.events import on_whatsapp_message
		on_whatsapp_message(doc)
	return doc.name


@frappe.whitelist(methods=["POST"])
def send_reply(lead, text=None, channel="WhatsApp", template=None, subject=None):
	require_lead_access(lead)
	text = (text or "").strip()
	if channel == "Email":
		if not text:
			frappe.throw("Write a message first.")
		email = frappe.db.get_value("CRM Lead", lead, "email")
		if not email:
			frappe.throw("This lead has no email address.")
		frappe.sendmail(recipients=[email], subject=subject or "Your enquiry with Titan Steel & Engineers", content=text,
			reference_doctype="CRM Lead", reference_name=lead, now=False)
	else:
		if not template and not in_session_window(lead):
			frappe.throw("More than 24 hours since the customer's last message: WhatsApp only allows an approved template now.")
		if not template and not text:
			frappe.throw("Write a message first.")
		_insert_whatsapp(lead, text=text, template=template)
	frappe.db.set_value("CRM Lead", lead, {"titan_ai_status": "Paused (human)", "lead_owner": frappe.db.get_value("CRM Lead", lead, "lead_owner") or frappe.session.user})
	zoho.push_lead(lead)
	return get_conversation(lead)


@frappe.whitelist(methods=["POST"])
def resolve_escalation(lead):
	require_lead_access(lead)
	frappe.db.set_value("CRM Lead", lead, "titan_escalation_reason", None)
	log_event("AI resumed", lead, {"resolved": True})
	return get_conversation(lead)


@frappe.whitelist(methods=["POST"])
def simulate_incoming(lead, text):
	"""Testing aid while Meta is not verified: record a customer message (Simulated mode, managers only)."""
	require_manager()
	if _wa_mode() != "Simulated":
		frappe.throw("Only available in Simulated WhatsApp mode.")
	_insert_whatsapp(lead, text=text, incoming=True)
	return get_conversation(lead)


# ---------------------------------------------------------------- Pipeline
@frappe.whitelist()
def get_pipeline():
	require_desk_user()
	statuses = frappe.get_all("CRM Lead Status", fields=["name", "position"], order_by="position asc") if _has("CRM Lead Status") else []
	leads = _leads(limit=500)
	for l in leads:
		l.spec_pct = l.titan_spec_completeness or 0
	return {"stages": [s.name for s in statuses], "leads": leads}


@frappe.whitelist(methods=["POST"])
def move_stage(lead, status):
	require_lead_access(lead)
	if not frappe.db.exists("CRM Lead Status", status):
		frappe.throw("Unknown stage.")
	doc = frappe.get_doc("CRM Lead", lead)
	doc.status = status
	if status in ("Lost", "Junk", "Converted"):
		doc.titan_ai_status = "Stopped"
	doc.save(ignore_permissions=True)
	log_event("Stage changed", lead, {"to": status})
	zoho.push_lead(lead)
	return {"name": lead, "status": status}


# ---------------------------------------------------------------- Calendar
@frappe.whitelist()
def get_calendar(start, end):
	require_desk_user()
	start, end = f"{getdate(start)} 00:00:00", f"{getdate(end)} 23:59:59"
	ev = frappe.db.sql(
		"""select e.name, e.subject, e.starts_on, e.ends_on, e.all_day, e.owner, ep.reference_docname lead
		from `tabEvent` e join `tabEvent Participants` ep on ep.parent=e.name and ep.reference_doctype='CRM Lead'
		where e.starts_on between %s and %s and e.status!='Cancelled'""", (start, end), as_dict=True)
	events = [{"id": e.name, "title": e.subject, "start": e.starts_on, "end": e.ends_on, "all_day": e.all_day, "kind": "call", "lead": e.lead} for e in ev]
	for l in _leads({"titan_next_followup": ["between", [start, end]], "titan_ai_status": "Active"}):
		events.append({"id": f"fu-{l.name}", "title": f"Follow-up: {l.organization or l.lead_name}", "start": l.titan_next_followup, "kind": "followup", "lead": l.name})
	booked = {e.lead for e in ev}
	to_schedule = [{"lead": l.name, "title": f"Call {l.organization or l.lead_name}", "reason": l.titan_escalation_reason}
		for l in _leads({"titan_escalation_reason": ["is", "set"]}) if l.name not in booked]
	return {"events": events, "to_schedule": to_schedule}


@frappe.whitelist(methods=["POST"])
def book_call(lead, start, minutes=30):
	require_lead_access(lead)
	start = get_datetime(start)
	end = add_to_date(start, minutes=cint(minutes) or 30)
	clash = frappe.db.sql("""select e.name from `tabEvent` e where e.owner=%s and e.status!='Cancelled' and e.starts_on < %s and e.ends_on > %s""",
		(frappe.session.user, end, start))
	org = frappe.db.get_value("CRM Lead", lead, "organization") or frappe.db.get_value("CRM Lead", lead, "lead_name")
	ev = frappe.get_doc({"doctype": "Event", "subject": f"Call {org}", "starts_on": start, "ends_on": end, "event_type": "Private",
		"event_participants": [{"reference_doctype": "CRM Lead", "reference_docname": lead}]}).insert(ignore_permissions=True)
	from titan_desk.escalation import assign_internal as assign
	if not frappe.db.exists("ToDo", {"reference_type": "CRM Lead", "reference_name": lead, "allocated_to": frappe.session.user, "status": "Open"}):
		assign({"doctype": "CRM Lead", "name": lead, "assign_to": [frappe.session.user], "description": f"Call {org} at {start}", "date": getdate(start)})
	frappe.db.set_value("CRM Lead", lead, {"titan_ai_status": "Paused (call booked)", "lead_owner": frappe.db.get_value("CRM Lead", lead, "lead_owner") or frappe.session.user})
	log_event("Call booked", lead, {"event": ev.name, "start": start})
	zoho.push_lead(lead)
	return {"event": ev.name, "clash": bool(clash)}


@frappe.whitelist(methods=["POST"])
def cancel_call(event):
	require_desk_user()
	ev = frappe.get_doc("Event", event)
	if ev.owner != frappe.session.user and not is_manager():
		frappe.throw("You can only cancel your own calls.", frappe.PermissionError)
	ev.status = "Cancelled"
	ev.save(ignore_permissions=True)
	return True


# ---------------------------------------------------------------- Approvals (supervised mode)
@frappe.whitelist()
def get_approvals(status="Pending"):
	require_desk_user()
	rows = frappe.get_all("Titan Reply Approval", filters={"status": status}, fields=["name", "lead", "lead_name", "channel", "status", "draft", "source", "creation", "decided_by", "decided_on", "reject_reason"], order_by="creation desc", limit=100)
	if not is_manager():
		rows = [r for r in rows if can_act_on_lead(frappe.db.get_value("CRM Lead", r.lead, "lead_owner"))]
	return rows


@frappe.whitelist(methods=["POST"])
def decide_approval(name, decision, reason=None, text=None):
	doc = frappe.get_doc("Titan Reply Approval", name)
	require_lead_access(doc.lead)
	if doc.status != "Pending":
		frappe.throw("This reply was already decided.")
	if decision not in ("Approved", "Rejected"):
		frappe.throw("Decision must be Approved or Rejected.")
	if decision == "Rejected" and not (reason or "").strip():
		frappe.throw("Add a reason for rejecting.")
	doc.update({"status": decision, "decided_by": frappe.session.user, "decided_on": now_datetime(), "reject_reason": reason})
	if text:
		doc.draft = text
	if decision == "Approved":
		try:
			if doc.channel == "WhatsApp":
				if in_session_window(doc.lead):
					doc.sent_message = _insert_whatsapp(doc.lead, text=doc.draft)
				else:
					tpl = _settings().followup_template
					if not tpl:
						frappe.throw("Outside the 24-hour window and no follow-up template is set in Titan Desk Settings.")
					doc.sent_message = _insert_whatsapp(doc.lead, template=tpl)
			else:
				email = frappe.db.get_value("CRM Lead", doc.lead, "email")
				frappe.sendmail(recipients=[email], subject="Your enquiry with Titan Steel & Engineers", content=doc.draft, reference_doctype="CRM Lead", reference_name=doc.lead)
			doc.status = "Sent"
		except frappe.ValidationError:
			raise
		except Exception as e:
			doc.status = "Failed"
			doc.reject_reason = str(e)[:300]
	else:
		frappe.db.set_value("CRM Lead", doc.lead, {"titan_escalation_reason": "Reply rejected: " + reason[:100]})
	doc.save(ignore_permissions=True)
	log_event("Approval decided", doc.lead, {"approval": name, "decision": decision})
	return doc.as_dict()


# ---------------------------------------------------------------- Follow-ups
@frappe.whitelist()
def get_my_followup_preference():
	require_desk_user()
	s = _settings()
	p = frappe.db.get_value("Titan Follow-up Preference", frappe.session.user, ["followup_hours", "max_followups", "quiet_start", "quiet_end", "enabled"], as_dict=True) or {}
	return {"default_hours": s.default_followup_hours, "default_max": s.default_max_followups, **p}


@frappe.whitelist(methods=["POST"])
def set_my_followup_preference(followup_hours=None, max_followups=None, quiet_start=None, quiet_end=None, enabled=1):
	require_desk_user()
	if followup_hours:
		try:
			hrs = [int(x) for x in str(followup_hours).split(",") if x.strip()]
		except ValueError:
			frappe.throw("Intervals must be whole hours separated by commas, e.g. 4,24,72.")
		if not hrs or any(h <= 0 for h in hrs):
			frappe.throw("Intervals must be positive.")
	name = frappe.session.user
	doc = frappe.get_doc("Titan Follow-up Preference", name) if frappe.db.exists("Titan Follow-up Preference", name) else frappe.new_doc("Titan Follow-up Preference")
	doc.update({"user": name, "followup_hours": followup_hours, "max_followups": cint(max_followups) or None, "quiet_start": quiet_start or None, "quiet_end": quiet_end or None, "enabled": cint(enabled)})
	doc.save(ignore_permissions=True)
	return get_my_followup_preference()


# ---------------------------------------------------------------- WhatsApp page
@frappe.whitelist()
def get_whatsapp_status():
	require_desk_user()
	if not _has(WA):
		return {"installed": False}
	today = f"{nowdate()} 00:00:00"
	return {
		"installed": True, "mode": _wa_mode(),
		"accounts": frappe.get_all("WhatsApp Account", fields=["name", "account_name", "status", "phone_id", "is_default_outgoing"]) if _has("WhatsApp Account") else [],
		"templates": frappe.get_all("WhatsApp Templates", fields=["name", "template_name", "category", "status", "language_code"], limit=50) if _has("WhatsApp Templates") else [],
		"today": {"in": frappe.db.count(WA, {"type": "Incoming", "creation": [">=", today]}), "out": frappe.db.count(WA, {"type": "Outgoing", "creation": [">=", today]}),
			"failed": frappe.db.count(WA, {"status": ["in", ["failed", "Failed"]], "creation": [">=", today]})},
		"other_autoreply": _settings().other_autoreply_warning,
	}


# ---------------------------------------------------------------- Getting started
@frappe.whitelist()
def get_setup_progress():
	require_desk_user()
	s = _settings()
	steps = [
		("whatsapp", "Connect WhatsApp Business", "Add the Titan number as a WhatsApp Account", bool(_has("WhatsApp Account") and frappe.db.count("WhatsApp Account")), "/app/whatsapp-account"),
		("zoho", "Import enquiries from Zoho", "Run a Zoho import for a date range", bool(frappe.db.count("Titan Zoho Import", {"status": "Completed"})), "/app/titan-zoho-import/new"),
		("email", "Connect the sales inbox", "Set up info@titansteel.in as an Email Account", bool(frappe.db.count("Email Account", {"enable_incoming": 1})), "/app/email-account"),
		("spec", "Review spec templates", "Check what must be asked for each product line", bool(frappe.db.count("Titan Spec Template", {"modified_by": ["!=", "Administrator"]})), "/app/titan-spec-template"),
		("rules", "Review escalation rules", "Decide when the desk hands a lead to a person", bool(frappe.db.count("Titan Escalation Rule", {"modified_by": ["!=", "Administrator"]})), "/app/titan-escalation-rule"),
		("team", "Invite the sales team", "Give salespeople the Titan Sales User role", frappe.db.count("Has Role", {"role": "Titan Sales User", "parenttype": "User"}) > 0, "/app/user"),
		("templates", "Get WhatsApp templates approved", "At least one approved template for follow-ups", bool(_has("WhatsApp Templates") and frappe.db.count("WhatsApp Templates", {"status": "APPROVED"})), "/app/whatsapp-templates"),
		("followup", "Set your follow-up timing", "Choose how often leads are followed up", bool(frappe.db.exists("Titan Follow-up Preference", frappe.session.user)), "/titan-desk/settings"),
	]
	return {"steps": [{"key": k, "title": t, "description": d, "done": bool(done), "link": link} for k, t, d, done, link in steps],
		"done": sum(1 for s_ in steps if s_[3]), "total": len(steps), "supervised": supervised_mode_active(s)}


@frappe.whitelist()
def get_desk_users():
	require_desk_user()
	users = frappe.get_all("Has Role", filters={"role": ["in", ["Titan Sales User", "Titan Sales Manager"]], "parenttype": "User"}, pluck="parent", distinct=True)
	return frappe.get_all("User", filters={"name": ["in", users], "enabled": 1}, fields=["name", "full_name"]) if users else []
