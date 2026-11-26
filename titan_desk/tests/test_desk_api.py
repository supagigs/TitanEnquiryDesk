import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_to_date, now_datetime

from titan_desk import desk, followups, retention
from titan_desk.tests.test_desk import make_user


class TestDeskApi(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.sales = make_user("titan.sales@example.com", ["Titan Sales User"])
		cls.sales2 = make_user("titan.sales2@example.com", ["Titan Sales User"])
		cls.manager = make_user("titan.mgr@example.com", ["Titan Sales Manager"])
		s = frappe.get_single("Titan Desk Settings")
		s.whatsapp_mode, s.zoho_mode, s.supervised_mode = "Simulated", "Simulated", 1
		s.supervised_start, s.supervised_weeks = frappe.utils.today(), 5
		s.business_hours_start, s.business_hours_end, s.working_days = "00:00:00", "23:59:59", "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
		s.save()

	def tearDown(self):
		frappe.set_user("Administrator")

	def lead(self, owner=None, mobile="+919800000001", **kw):
		d = frappe.get_doc({"doctype": "CRM Lead", "first_name": "Asha", "organization": "Test Forge", "mobile_no": mobile, "email": "asha@example.com", "lead_owner": owner, **kw})
		d.insert(ignore_permissions=True)
		return d.name

	def test_new_lead_is_active_and_due(self):
		l = self.lead()
		v = frappe.db.get_value("CRM Lead", l, ["titan_ai_status", "titan_next_followup"], as_dict=True)
		self.assertEqual(v.titan_ai_status, "Active")
		self.assertIsNotNone(v.titan_next_followup)

	def test_reply_requires_24h_window(self):
		l = self.lead()
		frappe.set_user(self.sales)
		self.assertRaises(frappe.ValidationError, desk.send_reply, l, "Hello")
		frappe.set_user(self.manager)
		desk.simulate_incoming(l, "Need 40 flanges")
		frappe.set_user(self.sales)
		c = desk.send_reply(l, "Which pressure class?")
		self.assertTrue(c["in_window"])
		self.assertEqual([m["out"] for m in c["messages"]], [False, True])
		self.assertEqual(frappe.db.get_value("CRM Lead", l, "titan_ai_status"), "Paused (human)")

	def test_incoming_price_question_escalates(self):
		l = self.lead()
		frappe.set_user(self.manager)
		desk.simulate_incoming(l, "What is your rate for 2 buckets?")
		v = frappe.db.get_value("CRM Lead", l, ["titan_escalation_reason", "titan_ai_status"], as_dict=True)
		self.assertEqual(v.titan_escalation_reason, "Asked for price")
		self.assertEqual(v.titan_ai_status, "Paused (escalated)")
		self.assertIn(l, [x.name for x in desk.get_inbox("Needs human")])

	def test_simulate_incoming_is_manager_only(self):
		l = self.lead()
		frappe.set_user(self.sales)
		self.assertRaises(frappe.PermissionError, desk.simulate_incoming, l, "hi")

	def test_sales_user_cannot_read_others_conversation(self):
		l = self.lead(owner=self.sales2)
		frappe.set_user(self.sales)
		self.assertRaises(frappe.PermissionError, desk.get_conversation, l)
		self.assertNotIn(l, [x.name for x in desk.get_inbox("All")])

	def test_spec_completeness(self):
		l = self.lead()
		frappe.set_user(self.sales)
		c = desk.update_spec(l, "Flange", {"type_size": "WN 12\"", "material_grade": "A105", "quantity": "40"})
		self.assertEqual(c["completeness"], 43)
		self.assertIn("Pressure class", desk.missing_fields("Flange", json.loads(frappe.db.get_value("CRM Lead", l, "titan_spec_json"))))

	def test_followup_creates_approval_in_supervised_mode(self):
		l = self.lead()
		frappe.db.set_value("CRM Lead", l, {"titan_product_line": "Flange", "titan_next_followup": add_to_date(now_datetime(), minutes=-5)})
		followups.run()
		a = frappe.get_all("Titan Reply Approval", filters={"lead": l, "status": "Pending"}, fields=["name", "draft"])
		self.assertEqual(len(a), 1)
		self.assertIn("type & size", a[0].draft.lower())
		self.assertEqual(frappe.db.get_value("CRM Lead", l, "titan_followup_count"), 1)
		followups.run()
		self.assertEqual(frappe.db.count("Titan Reply Approval", {"lead": l, "status": "Pending"}), 1)

	def test_approve_sends_and_reject_needs_reason(self):
		l = self.lead()
		frappe.set_user(self.manager)
		desk.simulate_incoming(l, "Need flanges")
		a = frappe.get_doc({"doctype": "Titan Reply Approval", "lead": l, "channel": "WhatsApp", "draft": "Which class?"}).insert(ignore_permissions=True)
		r = desk.decide_approval(a.name, "Approved")
		self.assertEqual(r["status"], "Sent")
		self.assertTrue(frappe.db.exists("WhatsApp Message", r["sent_message"]))
		b = frappe.get_doc({"doctype": "Titan Reply Approval", "lead": l, "channel": "WhatsApp", "draft": "x"}).insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, desk.decide_approval, b.name, "Rejected")
		self.assertEqual(desk.decide_approval(b.name, "Rejected", "Wrong tone")["status"], "Rejected")

	def test_book_call_pauses_followups_and_appears_on_calendar(self):
		l = self.lead()
		frappe.db.set_value("CRM Lead", l, "titan_escalation_reason", "Asked for price")
		frappe.set_user(self.sales)
		start = f"{add_days(frappe.utils.today(), 1)} 11:00:00"
		self.assertIn(l, [x["lead"] for x in desk.get_calendar(frappe.utils.today(), add_days(frappe.utils.today(), 7))["to_schedule"]])
		desk.book_call(l, start)
		self.assertEqual(frappe.db.get_value("CRM Lead", l, "titan_ai_status"), "Paused (call booked)")
		cal = desk.get_calendar(frappe.utils.today(), add_days(frappe.utils.today(), 7))
		self.assertIn(l, [e["lead"] for e in cal["events"] if e["kind"] == "call"])
		self.assertNotIn(l, [x["lead"] for x in cal["to_schedule"]])

	def test_move_stage_validates_status(self):
		l = self.lead()
		frappe.set_user(self.sales)
		self.assertRaises(frappe.ValidationError, desk.move_stage, l, "Nonexistent")
		st = frappe.get_all("CRM Lead Status", pluck="name", order_by="position asc")[1]
		self.assertEqual(desk.move_stage(l, st)["status"], st)

	def test_followup_preference_validation(self):
		frappe.set_user(self.sales)
		self.assertRaises(frappe.ValidationError, desk.set_my_followup_preference, "4,abc")
		p = desk.set_my_followup_preference("2,6", 3)
		self.assertEqual(p["followup_hours"], "2,6")

	def test_retention_purges_old_logs_only(self):
		e = frappe.get_doc({"doctype": "Titan Desk Event", "event": "Zoho sync"}).insert(ignore_permissions=True)
		frappe.db.set_value("Titan Desk Event", e.name, "creation", add_days(now_datetime(), -120), update_modified=False)
		new = frappe.get_doc({"doctype": "Titan Desk Event", "event": "Zoho sync"}).insert(ignore_permissions=True)
		retention.purge_old_records()
		self.assertFalse(frappe.db.exists("Titan Desk Event", e.name))
		self.assertTrue(frappe.db.exists("Titan Desk Event", new.name))

	def test_today_and_setup_load(self):
		self.lead()
		frappe.set_user(self.sales)
		t = desk.get_today()
		self.assertIn("needs", t)
		self.assertEqual(t["setup"]["total"], 8)
