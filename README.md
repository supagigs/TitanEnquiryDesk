# Titan Enquiry Desk (`titan_desk`)

Enquiry inbox, WhatsApp chat and follow-up workspace for Titan Steel & Engineers, built on Frappe 16, Frappe CRM and `frappe_whatsapp`.

- Plan: [docs/PLAN.md](docs/PLAN.md) · Audit: [docs/AUDIT.md](docs/AUDIT.md)
- Required apps: `frappe` 16.x. Optional at runtime: `crm` (CRM Lead), `frappe_whatsapp`.
- Zoho CRM sync is **simulated** in this release (`Titan Desk Settings → Zoho mode = Simulated`); live sync will come from FlowForge.

```bash
bench get-app https://github.com/supagigs/TitanEnquiryDesk.git
bench --site <site> install-app titan_desk
```
