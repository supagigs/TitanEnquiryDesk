# Release notes — 1.0.0rc1 (release candidate)

Not production-ready until the items under "Before 1.0.0" are done.

## What's in it
- Vue 3 SPA at `/titan-desk`: Today, Calendar, Inbox (WhatsApp-style, WhatsApp + email), Pipeline, Approvals, WhatsApp, Settings; collapsible sidebar, app switcher, light/dark, guided tour, Getting started.
- Data model: 10 DocTypes, 12 CRM Lead fields, 3 roles with CRM permissions.
- Simulated Zoho (import by date range, 15-min pull, push of desk fields) behind a `ZohoClient` interface for FlowForge.
- WhatsApp via `frappe_whatsapp`, with a Simulated mode until Meta verification; 24-hour rule enforced.
- Configurable escalation rules, per-user follow-up cadence, supervised mode (5 weeks), 90-day retention.
- Install/update scripts, user and admin guides, FlowForge contract, tests and screenshots.

## Before 1.0.0
1. Titan signs off spec templates and escalation rules.
2. Test on a Frappe Cloud staging copy of production with `whatsapp_chat` / `frappe_whatsapp_chatbot` present.
3. Meta verification, then Live WhatsApp test with a real number.
4. Titan UAT sign-off.
