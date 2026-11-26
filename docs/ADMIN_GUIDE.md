# Titan Enquiry Desk — admin guide

## Install / update
- Fresh install: `scripts/init.sh <bench> <site> [ref]` (backs up first).
- Update: `scripts/update.sh <bench> <site> <tag>` (refuses to run over local changes; backs up; migrates; prints rollback).
- Frappe Cloud: add `https://github.com/supagigs/TitanEnquiryDesk` to the bench, deploy, then install the app on a **staging** site first.
- Requires frappe 16 and crm. WhatsApp features use `frappe_whatsapp`.

## Roles (Users & Permissions)
| Role | Access |
|---|---|
| Titan Sales User | Desk; own and unassigned leads; reply, take over, book calls, approve on own leads |
| Titan Sales Manager | All leads; assign to others; all approvals; simulate test messages |
| Titan Desk Admin | Settings, Zoho import, spec templates, demo data |
The app adds Custom DocPerms on CRM Lead, CRM Lead Status/Source, WhatsApp Message and WhatsApp Templates for these roles. Adjust them in Role Permission Manager.

## Titan Desk Settings (/app/titan-desk-settings)
- Business hours and working days (follow-ups only go out inside them).
- **Supervised mode** + start date + weeks (default 5): follow-ups wait in Approvals; turns off automatically after the period.
- Follow-up intervals, max follow-ups, follow-up message (`{first_name}`, `{missing}`), follow-up template for messages outside 24 h.
- **Zoho mode**: Simulated (until FlowForge provides live sync) or Off.
- **WhatsApp mode**: Simulated (stores messages, does not call Meta) or Live (uses the WhatsApp Account; needs a verified Meta business).
- Retention days (default 90) for desk events, sync logs and decided approvals.
- Weekly goals shown on Today.

## Zoho import (simulated)
Create a **Titan Zoho Import** with a date range, or call `titan_desk.api.start_zoho_import`. Re-running a range never creates duplicates (matched on Zoho ID). Sync results are in **Titan Zoho Sync Log**.

## Escalation rules and spec templates
Edit **Titan Escalation Rule** (keyword, lead temperature, attachment, no-reply) and **Titan Spec Template** (fields per product line). Defaults are drafts for Titan to review.

## Scheduled jobs
- Every 15 min: simulated Zoho pull, follow-up scheduler.
- Daily: retention purge.

## Known limitations (1.0)
- Zoho live sync and AI-written replies are not in this app; FlowForge will provide them (see FLOWFORGE_CONTRACT.md).
- `whatsapp_chat` / `frappe_whatsapp_chatbot` may also auto-reply on the same number; tick “Another app may auto-reply” and check before going live.
- WhatsApp Flows and media download depend on `frappe_whatsapp`.
