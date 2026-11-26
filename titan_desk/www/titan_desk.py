import json

import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/titan-desk"
		raise frappe.Redirect
	from titan_desk.permissions import has_app_permission
	if not has_app_permission():
		frappe.throw("You need a Titan desk role to open the Enquiry Desk.", frappe.PermissionError)
	frappe.db.commit()
	context.csrf_token = frappe.sessions.get_csrf_token()
	from titan_desk.api import get_boot
	context.boot = json.dumps(get_boot())
	return context
