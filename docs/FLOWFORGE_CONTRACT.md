# FlowForge integration contract

The desk works without FlowForge. FlowForge plugs in through documents and functions only; no desk code changes needed.

| FlowForge needs to… | Use |
|---|---|
| Create/update leads from live Zoho | `titan_desk.zoho.upsert_lead_from_zoho(z: dict, direction="Pull")` with keys `zoho_id, company, contact_name, mobile, email, lead_source, description`; idempotent on `zoho_id` |
| Replace the Zoho simulator | Implement `ZohoClient` (`list_leads`, `list_modified_since`, `push_lead`) and return it from `titan_desk.zoho.get_client()` when Zoho mode is Live |
| React to desk activity | DocType events on **Titan Desk Event** (`event`: Lead created, Message in/out, Taken over, AI paused/resumed, Assigned, Stage changed, Escalated, Approval decided, Call booked) |
| Propose an AI reply | Insert **Titan Reply Approval** (`lead`, `channel`, `draft`, `source` = run ID); the desk sends it when approved |
| Send directly (after supervised mode) | Insert an Outgoing **WhatsApp Message** linked to the CRM Lead; respect the 24 h rule (`titan_desk.desk.in_session_window(lead)`) |
| Write AI results | CRM Lead fields `lead_temperature`, `titan_product_line`, `titan_spec_json`, `titan_spec_completeness`, `titan_ai_summary`, `titan_escalation_reason` |
| Respect people | Only act when `titan_ai_status == "Active"`; any human reply or take over sets it to a Paused value |
