# Titan Enquiry Desk — Delivery Plan v0.2 (for approval)

| | |
|---|---|
| App | `titan_desk` — Frappe app with a Vue 3 + frappe-ui SPA at `/titan-desk` |
| Repo | https://github.com/supagigs/TitanEnquiryDesk (empty at time of writing: LICENSE only, `main`) |
| Client | Titan Steel & Engineers · built by Renocrew Solutions LLP |
| Stage | **Plan.** Prototype approved (Titan Enquiry Desk HTML). No code, installs or migrations yet. |
| Production | https://titansteelengineers.frappe.cloud — **read-only. Never a test target.** |

## 0. Decisions from setup answers (26 Nov 2026)

| # | Topic | Decision |
|---|---|---|
| 1 | System of record | **Zoho CRM** (India DC). The desk works on Frappe `CRM Lead` records kept in **two-way sync** with Zoho. |
| 2 | Versions (production, as reported) | frappe 16.61.0 · erpnext 16.61.0 · crm 16.4.0 · frappe_whatsapp 1.0.12 · whatsapp_chat 0.0.1 · frappe_whatsapp_chatbot 0.0.1 |
| 3 | Hosting | Frappe Cloud. Staging = a separate Frappe Cloud site (or a local bench) restored from a production backup; to be created in Section 1. |
| 4 | FlowForge | Separate, **not installed**. Build the desk first; expose clean hooks so FlowForge can plug in later. No FlowForge code in this app. |
| 5 | Repo | `supagigs/TitanEnquiryDesk` |
| 6 | Quotations | **Out of scope.** Communications and lead management only. |
| 7 | Roles | Defined as Frappe Roles + DocPerms, managed in **Users & Permissions** (Role Permission Manager, Role Profiles). |
| 8 | WhatsApp | Use the installed `frappe_whatsapp` app. Meta business **not yet verified** → staging uses Meta's test number. |
| 9 | IndiaMART | Already flows into **Zoho**; reaches the desk through Zoho sync (no direct IndiaMART integration). |
| 10 | Website / Google Ads | Not yet; deferred (reach Zoho first if added later). |
| 11 | Email | `info@titansteel.in` (GoDaddy) as a Frappe Email Account. |
| 12 | AI spend | Decided in FlowForge later; not in this app. |
| 13 | Supervised mode | On, **5 weeks by default, configurable**. |
| 14 | Follow-up cadence | **Configurable per user** (with a site default). |
| 15 | Escalation rules | **Configurable** (rule table). |
| 16 | Spec templates | Unknown → Renocrew drafts from Titan's drilling-tool and forging catalogues; Titan signs off. |
| 17 | Language | English only. |
| 18 | Historical data | **Bulk import from Zoho for a chosen date range.** |
| 19 | Retention | **90 days** for chats and desk logs (configurable, purge job). |
| 20 | Scope | **All 10 sections.** |

### Important findings to resolve in Section 1

- **WhatsApp app difference.** The prototype was written against `frappe/whatsapp` (`WA Message`, `WA Template`). The site has **`frappe_whatsapp`** (shridarpatil), whose DocTypes are `WhatsApp Account`, `WhatsApp Templates`, `WhatsApp Message`, `WhatsApp Flow`, `WhatsApp Recipient List`; webhook `/api/method/frappe_whatsapp.utils.webhook.webhook`. The desk will target `frappe_whatsapp`. Its outbound API is not documented on its README → read the installed source on staging.
- **Two extra WhatsApp apps** (`whatsapp_chat`, `frappe_whatsapp_chatbot`, both 0.0.1) are installed. They may already create or reply to `WhatsApp Message`s. Must confirm they won't double-reply alongside the desk/FlowForge.
- **CRM app 16.4.0** already has its own WhatsApp tab when `frappe_whatsapp` is installed. The desk must not conflict with CRM's own Lead page.
- **Zoho ↔ Frappe CRM.** Need Zoho API access (OAuth client, India DC), field list, and who wins on conflicts.

## 1. Architecture

```
IndiaMART ─► Zoho CRM (system of record, India DC)
                  ▲│  two-way sync (titan_desk.zoho): webhooks/notifications + scheduled delta pull,
                  │▼  push of desk fields (status, owner, AI class, notes, call tasks)
             Frappe CRM Lead  ◄──────────────  Titan Desk SPA (/titan-desk, Vue 3 + frappe-ui)
                  ▲   ▲                              │ titan_desk.api.* (whitelisted, permission-checked)
 info@titansteel.in   │                              │
 (Email Account) ─────┘                              │
                      └── frappe_whatsapp (WhatsApp Message / Templates) ◄── Meta Cloud API
                                                     │
              FlowForge (later) ─► hooks: titan_desk events, Titan Reply Approval queue, escalation rules
```

### Data ownership

| Data | Owner | Desk role |
|---|---|---|
| Lead master (name, contact, company, source, Zoho owner) | Zoho | Mirrored into `CRM Lead`; edits flow back |
| Desk fields (stage on desk, AI class, spec, escalation, follow-up) | `titan_desk` (custom fields on `CRM Lead`) | Pushed to Zoho custom fields |
| WhatsApp messages/templates | `frappe_whatsapp` | Read/sent through server wrappers |
| Emails | Frappe `Communication` | Linked to `CRM Lead` |
| Calls | Frappe `Event` + `ToDo`, pushed as Zoho Tasks/Calls | Created from Calendar |
| Approvals of AI replies | `Titan Reply Approval` (titan_desk) | Filled by FlowForge later; reviewable now |

### New DocTypes (`titan_desk`)

| DocType | Purpose |
|---|---|
| `Titan Desk Settings` (single) | Business hours, supervised mode (on/off, start date, weeks = 5), retention days = 90, Zoho connection, default follow-up cadence |
| `Titan Follow-up Preference` | Per-user cadence (intervals, max follow-ups, quiet hours) |
| `Titan Escalation Rule` | Configurable rules: trigger (keyword/intent/class/value/no reply), action (assign/notify/pause AI), priority |
| `Titan Spec Template` + child `Titan Spec Field` | Required details per product line |
| `Titan Reply Approval` | Draft reply, lead, channel, status (Pending/Approved/Rejected/Sent), decided by/at |
| `Titan Zoho Sync Log` | Each pull/push: direction, record, result, error, retry count |
| `Titan Zoho Import` | Bulk import job: date range, filters, counts, status |
| `Titan Desk Event` | Audit/event stream for FlowForge and reporting (90-day retention) |

### Roles (Users & Permissions)

| Role | Can |
|---|---|
| Titan Sales User | Use desk; read/reply/assign own and unassigned leads; approve replies on own leads; book calls |
| Titan Sales Manager | All leads; reassign; approve any reply; edit escalation rules and cadences; view reports |
| Titan Desk Admin | Settings, Zoho connection, bulk import, spec templates, retention |

Shipped as fixtures (`Role`, `Custom DocPerm` via Role Permission Manager-compatible records, optional `Role Profile`). Server APIs check roles and record-level access on every call.

## 2. Sections

### Section 1 — Discovery, staging and technical audit
- Create an isolated staging site from a production backup (Frappe Cloud staging site or local bench with frappe 16.61 / crm 16.4 / frappe_whatsapp 1.0.12); verify host, port, site name; mask customer phone numbers/emails.
- Inspect installed source: `frappe_whatsapp` send API and hooks, `whatsapp_chat`, `frappe_whatsapp_chatbot` behaviour, CRM Lead schema and CRM's WhatsApp integration.
- Zoho: create OAuth client (India DC), list Lead fields and custom fields, decide field map and conflict rules, check API limits.
- Draft spec templates from catalogues for Titan sign-off.
- **Done when:** staging verified as not production; version matrix recorded; WhatsApp send path known; Zoho field map + conflict rules agreed; spec templates drafted. Deliverable `docs/AUDIT.md`.

### Section 2 — App scaffold, data model and roles
- `bench new-app titan_desk`; DocTypes above; custom fields on `CRM Lead` (fixtures); roles and permissions; settings defaults (supervised 5 weeks, retention 90 days).
- Whitelisted API skeleton with role checks; unit tests for validation and permissions.
- **Done when:** installs/migrates/uninstalls cleanly on staging without touching CRM data; permission tests pass for each role.

### Section 3 — Design system and app shell (Vue 3 + frappe-ui)
- Vite SPA served at `/titan-desk`; session auth; sidebar (groups, collapse to icon rail, tooltips), app switcher (CRM, Helpdesk, Desk, ERPNext; FlowForge when installed), Titan logo, light/dark, Getting started panel, guided tour, toasts; loading/empty/error/permission states.
- **Done when:** desk loads for Sales User, guests redirected; dark mode and collapse persist; accessibility checks pass on the shell.

### Section 4 — Zoho sync and bulk import
- OAuth connection in settings (tokens in Password fields).
- Bulk import from Zoho for a chosen **date range** (background job, resumable, idempotent on Zoho ID, progress UI).
- Incremental pull (Zoho notifications/webhook if allowed + scheduled `modified_since` pull) and push of desk fields, notes, calls; conflict rule per field; retries with backoff; sync log.
- **Done when:** importing a date range twice creates no duplicates; a change in Zoho appears in the desk and a desk change appears in Zoho within the agreed time; failures are logged and retried.

### Section 5 — Inbox: WhatsApp and email
- WhatsApp-style chat list and conversation over `WhatsApp Message` + `Communication` for the lead; 24-hour window indicator (free text vs approved template); template picker from `WhatsApp Templates`; take over / pause AI / assign; requirement sheet from spec template; realtime updates.
- Guard against double replies from `whatsapp_chat` / `frappe_whatsapp_chatbot` (config decided in Section 1).
- **Done when:** Sales User reads and replies on staging with Meta's test number; outside 24 h only templates can be sent; replies pause the AI flag; email replies thread on the lead; unauthorised users are refused by the server.

### Section 6 — Today, Pipeline and reporting
- Today brief (response time, weekly goals, today's list, follow-ups due, setup progress); Pipeline board with server-validated stage moves (synced to Zoho); counts by source/product line; manager view per salesperson.
- **Done when:** figures match SQL checks on seeded data; moves are permission-checked and reach Zoho.

### Section 7 — Calendar and per-user follow-ups
- Week/month calendar; calls to schedule; drag to book (Event + ToDo, pushed to Zoho as call/task); per-user follow-up preferences; reschedule/cancel; Asia/Kolkata.
- **Done when:** booking creates linked records in Frappe and Zoho; follow-up reminders respect each user's cadence and business hours.

### Section 8 — Automation-ready layer (for FlowForge later)
- Supervised mode (5 weeks, configurable) with the `Titan Reply Approval` queue and approve/reject UI; configurable escalation rules engine (keywords, class, no-reply time, value) with actions (assign, notify, pause AI); `Titan Desk Event` stream and documented hook points/APIs for FlowForge; manual-mode fallbacks so the desk is useful without AI.
- **Done when:** rules fire correctly on test leads; approvals send/reject correctly; supervised mode ends automatically after the configured period; integration contract documented in `docs/FLOWFORGE_CONTRACT.md`.

### Section 9 — Security, retention, QA, performance and deployment
- Permission matrix tests; Zoho/Meta secrets only in Password fields; PII masked in logs; 90-day retention purge (desk logs, approvals, sync logs; WhatsApp message purge only if Titan confirms — it is another app's data); rate limits; load test; backup/restore drill on staging; Frappe Cloud deployment notes (add app from GitHub to the bench); init/update scripts for local benches.
- **Done when:** all permission tests pass; purge verified on staging; p95 API < 500 ms on seeded data; scripts tested on a disposable bench.

### Section 10 — End-to-end validation, packaging and handover
- Fresh install + upgrade tests; full journeys (Zoho import → WhatsApp chat → escalation → call → Zoho update); dark/responsive checks; real screenshots; admin and user guides (Markdown); release notes; 1.0.0 ZIP + manifest.
- **Done when:** all acceptance criteria pass on staging with evidence and Titan UAT is signed off. Production install on Frappe Cloud is a separate, client-approved step.

## 3. Environment, backup and rollback
- Work only on staging; verify host/port/site before every HTTP test.
- Backup before each migration (`bench --site <staging> backup --with-files`).
- Rollback: restore backup; `uninstall-app titan_desk` removes only Titan DocTypes/fields.
- Git: branch per section (`section/NN-name`), tag `v0.NN.0` when shipped; no force-push.

## 4. Packaging
- `titan_desk-<version>.zip`: source, built assets, fixtures, `MANIFEST.md`, `docs/`, `scripts/init.sh`, `scripts/update.sh` (detect local changes, back up, migrate, build, health check, print rollback).

## 5. Still open (non-blocking unless marked)
1. **Blocking S1:** staging target — new Frappe Cloud site, or local bench?
2. **Blocking S4:** Zoho OAuth client + admin to authorise; which Zoho modules (Leads only, or Contacts/Deals/Calls/Tasks too)?
3. **Blocking S5:** Are `whatsapp_chat` and `frappe_whatsapp_chatbot` in active use? Can the chatbot be disabled for desk-managed numbers?
4. Who signs off spec templates at Titan?
5. Push access to the repo for Renocrew's build account.
