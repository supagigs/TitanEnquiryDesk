import frappe
from frappe.tests import IntegrationTestCase

from titan_desk import api, zoho
from titan_desk.escalation import evaluate_message, match_keywords


def make_user(email, roles):
	if not frappe.db.exists("User", email):
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
		u.insert(ignore_permissions=True)
	u = frappe.get_doc("User", email)
	u.roles = []
	u.add_roles(*roles)
	return email


class TestTitanDesk(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.sales = make_user("titan.sales@example.com", ["Titan Sales User"])
		cls.sales2 = make_user("titan.sales2@example.com", ["Titan Sales User"])
		cls.manager = make_user("titan.mgr@example.com", ["Titan Sales Manager"])
		cls.admin = make_user("titan.admin@example.com", ["Titan Desk Admin", "Titan Sales Manager"])
		cls.outsider = make_user("titan.none@example.com", [])

	def tearDown(self):
		frappe.set_user("Administrator")

	def lead(self, owner=None):
		d = frappe.get_doc({"doctype": "CRM Lead", "first_name": "Test", "organization": "Test Co", "lead_owner": owner})
		d.insert(ignore_permissions=True)
		return d.name

	def test_install_created_roles_fields_and_defaults(self):
		for r in ("Titan Sales User", "Titan Sales Manager", "Titan Desk Admin"):
			self.assertTrue(frappe.db.exists("Role", r))
		self.assertTrue(frappe.db.exists("Custom Field", "CRM Lead-titan_ai_status"))
		self.assertTrue(frappe.db.exists("Titan Spec Template", "Flange"))
		self.assertTrue(frappe.db.exists("Titan Escalation Rule", "Price asked"))
		s = frappe.get_single("Titan Desk Settings")
		self.assertEqual(s.supervised_weeks, 5)
		self.assertEqual(s.retention_days, 90)

	def test_outsider_is_refused(self):
		frappe.set_user(self.outsider)
		self.assertRaises(frappe.PermissionError, api.get_boot)

	def test_sales_user_can_take_over_unassigned_but_not_others(self):
		free = self.lead()
		mine_not = self.lead(owner=self.sales2)
		frappe.set_user(self.sales)
		st = api.take_over(free)
		self.assertEqual(st.lead_owner, self.sales)
		self.assertEqual(st.titan_ai_status, "Paused (human)")
		self.assertRaises(frappe.PermissionError, api.take_over, mine_not)

	def test_only_manager_assigns_to_others(self):
		free = self.lead()
		frappe.set_user(self.sales)
		self.assertRaises(frappe.PermissionError, api.assign, free, self.sales2)
		frappe.set_user(self.manager)
		self.assertEqual(api.assign(free, self.sales2).lead_owner, self.sales2)

	def test_toggle_ai(self):
		l = self.lead()
		frappe.set_user(self.manager)
		self.assertEqual(api.toggle_ai(l).titan_ai_status, "Paused")
		self.assertEqual(api.toggle_ai(l).titan_ai_status, "Active")

	def test_keyword_escalation(self):
		self.assertTrue(match_keywords("What is the RATE please", "price\nrate"))
		l = self.lead()
		rule = evaluate_message(l, "Please send your best price")
		self.assertEqual(rule, "Price asked")
		self.assertEqual(frappe.db.get_value("CRM Lead", l, "titan_ai_status"), "Paused (escalated)")
		self.assertIsNone(evaluate_message(self.lead(), "We need 40 flanges"))

	def test_supervised_mode_expires(self):
		s = frappe.get_single("Titan Desk Settings")
		s.supervised_mode, s.supervised_weeks, s.supervised_start = 1, 5, frappe.utils.add_days(frappe.utils.today(), -10)
		s.save()
		self.assertTrue(api.supervised_mode_active())
		s.supervised_start = frappe.utils.add_days(frappe.utils.today(), -40)
		s.save()
		self.assertFalse(api.supervised_mode_active())

	def test_simulated_zoho_import_is_idempotent(self):
		frappe.set_user(self.admin)
		zoho.seed_simulated_zoho(days=10)
		frappe.set_user("Administrator")
		imp = frappe.get_doc({"doctype": "Titan Zoho Import", "from_date": frappe.utils.add_days(frappe.utils.today(), -11), "to_date": frappe.utils.today()}).insert()
		first = zoho.run_import(imp.name)
		expected = frappe.db.count("Titan Zoho Sim Record", {"created_time": ["between", [f"{imp.from_date} 00:00:00", f"{imp.to_date} 23:59:59"]]})
		self.assertGreaterEqual(expected, 1)
		self.assertEqual(sum(first.values()), expected)
		imp2 = frappe.get_doc({"doctype": "Titan Zoho Import", "from_date": imp.from_date, "to_date": imp.to_date}).insert()
		second = zoho.run_import(imp2.name)
		self.assertEqual(second["created"], 0)
		self.assertEqual(second["skipped"] + second["updated"], expected)

	def test_push_writes_desk_fields_to_simulator(self):
		frappe.set_user(self.admin)
		zoho.seed_simulated_zoho(days=1)
		frappe.set_user("Administrator")
		zid = frappe.get_all("Titan Zoho Sim Record", pluck="name", limit=1)[0]
		lead, _ = zoho.upsert_lead_from_zoho(frappe.get_all("Titan Zoho Sim Record", filters={"name": zid}, fields=zoho.SimulatedZohoClient.FIELDS)[0])
		frappe.set_user(self.manager)
		api.toggle_ai(lead)
		self.assertIn("titan_ai_status", frappe.db.get_value("Titan Zoho Sim Record", zid, "desk_fields"))

	def test_seed_requires_admin(self):
		frappe.set_user(self.manager)
		self.assertRaises(frappe.PermissionError, zoho.seed_simulated_zoho)
