import frappe

DESK_ROLES = {"Titan Sales User", "Titan Sales Manager", "Titan Desk Admin", "System Manager"}
MANAGER_ROLES = {"Titan Sales Manager", "Titan Desk Admin", "System Manager"}


def roles(user=None):
	return set(frappe.get_roles(user or frappe.session.user))


def has_app_permission(user=None):
	return bool(roles(user) & DESK_ROLES)


def is_manager(user=None):
	return bool(roles(user) & MANAGER_ROLES)


def require_desk_user():
	if frappe.session.user == "Guest" or not has_app_permission():
		frappe.throw("You need a Titan desk role to use the Enquiry Desk.", frappe.PermissionError)


def require_manager():
	require_desk_user()
	if not is_manager():
		frappe.throw("Only a Titan Sales Manager can do this.", frappe.PermissionError)


def can_act_on_lead(lead_owner, user=None):
	"""Sales users act on their own and unassigned leads; managers on all."""
	user = user or frappe.session.user
	return is_manager(user) or not lead_owner or lead_owner == user


def require_lead_access(lead):
	require_desk_user()
	owner = frappe.db.get_value("CRM Lead", lead, "lead_owner")
	if owner is None and not frappe.db.exists("CRM Lead", lead):
		frappe.throw("Lead not found.", frappe.DoesNotExistError)
	if not can_act_on_lead(owner):
		frappe.throw("This lead belongs to another salesperson.", frappe.PermissionError)
