# Sections 1–2 report (26 Nov 2026)

## Environment (staging, verified isolated)
- Local disposable bench `/home/claude/staging-bench`, site `titan-staging.localhost` (own MariaDB 10.11 DB, port 8000 config, not served publicly). Production was not contacted.
- frappe v16.61.0 (Python 3.14.6, Node 24.22), crm 16.4.0, frappe_whatsapp 1.0.12 (master), titan_desk 0.2.0.
- Sandbox-only workaround: frappe's island toolchain pins `frappe-ui` to a GitHub tarball the sandbox could not download; it was pointed at a local git checkout of the same commit. Not part of this app.
- Backups taken before installing titan_desk and before the uninstall test (`sites/titan-staging.localhost/private/backups/`).

## Built (Section 2)
- DocTypes: Titan Desk Settings, Titan Follow-up Preference, Titan Escalation Rule, Titan Spec Template + Titan Spec Field, Titan Reply Approval, Titan Zoho Sync Log, Titan Zoho Import, Titan Desk Event, Titan Zoho Sim Record.
- Roles: Titan Sales User, Titan Sales Manager, Titan Desk Admin (created on install/migrate; manage in Users & Permissions).
- 12 custom fields on CRM Lead (incl. section and column break) (`titan_*`), reusing CRM's `lead_temperature` for Hot/Warm/Cold.
- Defaults: 4 spec templates (drilling tool, forging, flange, machining), 5 escalation rules, supervised mode 5 weeks, retention 90 days.
- Server: role/record permission helpers, APIs `get_boot`, `take_over`, `toggle_ai`, `assign`, `start_zoho_import`; escalation engine; WhatsApp Message / CRM Lead hooks; Zoho client interface with simulator, bulk import by date range, scheduled pull, push; 90-day purge job.

## Tests run (observed)
| Command | Result |
|---|---|
| `bench --site titan-staging.localhost run-tests --app titan_desk` | 10 tests, OK |
| install → uninstall → reinstall | CRM Lead rows kept (1 → 1); 12 Titan custom fields removed on uninstall and recreated on install |

## Not done / unverified
- No HTTP tests yet (no web server started; Section 3 adds the SPA).
- `whatsapp_chat`, `frappe_whatsapp_chatbot` not installed on staging; double-reply risk still to verify on a Frappe Cloud copy.
- Nothing committed or pushed (session has read-only repo access).
