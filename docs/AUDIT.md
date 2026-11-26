# Section 1 — Discovery and technical audit

Date: 26 Nov 2026 · Author: Renocrew (Claude) · Status: complete, pending client review

## 1. Production (read-only, as reported by Titan — not accessed)

Site: https://titansteelengineers.frappe.cloud (Frappe Cloud)

| App | Version |
|---|---|
| frappe | 16.61.0 |
| erpnext | 16.61.0 |
| crm | 16.4.0 |
| frappe_whatsapp | 1.0.12 |
| whatsapp_chat | 0.0.1 |
| frappe_whatsapp_chatbot | 0.0.1 |

Nothing was run against production.

## 2. Staging used for development

| | |
|---|---|
| Type | Local disposable bench in Renocrew's build sandbox (not Frappe Cloud) |
| Bench | `/home/claude/staging-bench` |
| Frappe | v16.61.0 (tag), Python 3.14, Node 24, MariaDB 10.11, Redis |
| Site | `titan-staging.localhost`, port 8000, own database |
| Data | Synthetic only. No production backup was used (none was provided). |

Limitation: ERPNext and crm are installed only if they install cleanly on this sandbox; the desk does not depend on ERPNext.

## 3. Source review findings

### frappe_whatsapp (shridarpatil/frappe_whatsapp, default branch)
- DocTypes: `WhatsApp Account`, `WhatsApp Message`, `WhatsApp Templates`, `WhatsApp Flow`, `WhatsApp Notification`, `WhatsApp Profiles`, `WhatsApp Settings`, `Bulk WhatsApp Message`, `WhatsApp Recipient List`.
- **Sending**: inserting a `WhatsApp Message` with `type = "Outgoing"` sends it to Meta in `before_insert` (`send_outgoing`). Templates: `use_template = 1`, `template`, `message_type = "Template"`. Whitelisted helper `send_template(to, reference_doctype, reference_name, template)`.
- **Receiving**: Meta webhook `/api/method/frappe_whatsapp.utils.webhook.webhook` creates `WhatsApp Message` with `type = "Incoming"`.
- Linking: `reference_doctype` / `reference_name` on each message.
- Not submittable. Status is a Data field updated from Meta status webhooks.

### crm 16.4.0 (tag v16.4.0)
- Uses `frappe_whatsapp` (`WhatsApp Message`), not `frappe/whatsapp`. `doc_events` on `WhatsApp Message` (`crm.api.whatsapp.validate`, `on_update`, `crm.automation.events.on_whatsapp_message`) already link messages to `CRM Lead`.
- `CRM Lead` already has `lead_temperature` (Cold / Warm / Hot), `status` (Link `CRM Lead Status`), `source` (Link `CRM Lead Source`), `lead_owner`, `mobile_no`, SLA fields. **Decision:** reuse `lead_temperature` for AI class; do not add a duplicate field.

### whatsapp_chat, frappe_whatsapp_chatbot (0.0.1)
- Sources not located/reviewed in this sandbox. **Risk:** a chatbot may auto-reply to the same incoming messages. **Mitigation in the desk:** `Titan Desk Settings → Other auto-replies present` warning and a per-lead `ai_status`; the desk never auto-replies on its own. To verify on a Frappe Cloud staging copy before go-live.

## 4. Zoho

No Zoho access. Per client instruction, Zoho behaviour is **simulated**:
- `Titan Desk Settings.zoho_mode = Simulated` (only option enabled in 1.0; `Live` reserved for FlowForge).
- A simulated Zoho store (`Titan Zoho Sim Record`) holds sample Zoho leads; bulk import by date range, incremental pull and push all go through a `ZohoClient` interface so FlowForge (or a live client) can replace the simulator without changing the desk.

## 5. Spec templates (draft from Titan catalogues — needs Titan sign-off)

| Product line | Required fields (ask order) |
|---|---|
| Drilling tool | Tool type · Diameter (mm) · Rig model / max torque (STD ≤190 kN, HD 200–250, XHD ≥260) · Soil condition · Quantity · Site location · Required by |
| Forging | Component (flange, ring, round bar, custom) · Material grade · Dimensions or drawing · Weight per piece · Quantity · Heat treatment & tests · Required by |
| Flange | Type & size (½"–60") · Material grade · Pressure class · Quantity · Test certificate · Delivery location · Required by |
| Machining & fabrication | Drawing · Material · Tolerances · Quantity · Finish · Delivery location · Required by |

## 6. Decisions

1. Target `frappe_whatsapp` DocTypes; send by inserting Outgoing `WhatsApp Message` through a server wrapper.
2. Reuse `CRM Lead.lead_temperature`; add only Titan-specific custom fields (prefix `titan_`).
3. Zoho simulated behind an interface; real sync left to FlowForge.
4. All desk APIs under `titan_desk.api.*` with role and record checks.
5. 90-day retention applies to Titan's own logs/approvals/sync logs; WhatsApp messages are not purged by the desk (owned by another app) unless Titan asks.
