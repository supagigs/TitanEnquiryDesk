app_name = "titan_desk"
app_title = "Titan Enquiry Desk"
app_publisher = "Renocrew Solutions LLP"
app_description = "Enquiry inbox, WhatsApp and follow-up workspace for Titan Steel & Engineers"
app_email = "hello@renocrew.com"
app_license = "mit"
required_apps = ["frappe"]

add_to_apps_screen = [
	{
		"name": "titan_desk",
		"logo": "/assets/titan_desk/logo.png",
		"title": "Titan Enquiry Desk",
		"route": "/titan-desk",
		"has_permission": "titan_desk.permissions.has_app_permission",
	}
]

after_install = "titan_desk.install.after_install"
after_migrate = "titan_desk.install.after_migrate"
before_uninstall = "titan_desk.install.before_uninstall"

website_route_rules = [{"from_route": "/titan-desk/<path:app_path>", "to_route": "titan-desk"}]

scheduler_events = {
	"daily": ["titan_desk.retention.purge_old_records"],
	"cron": {"*/15 * * * *": ["titan_desk.zoho.scheduled_pull", "titan_desk.followups.run"]},
}

doc_events = {
	"WhatsApp Message": {"after_insert": "titan_desk.events.on_whatsapp_message"},
	"CRM Lead": {"after_insert": "titan_desk.events.on_lead_insert", "on_update": "titan_desk.events.on_lead_update"},
}
