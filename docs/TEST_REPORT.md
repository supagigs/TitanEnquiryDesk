# Test report — titan_desk 1.0.0rc1 (26 Nov 2026)

## Environment
- Isolated local bench in the build sandbox, site `titan-staging.localhost` (DB `_696bdebf5c69277e`), served by `bench serve --port 8000`. Production (titansteelengineers.frappe.cloud) was never contacted.
- frappe 16.61.0 · crm 16.4.0 · frappe_whatsapp 1.0.12 · Python 3.14.6 · Node 24.22 · MariaDB 10.11 · Chrome (headless) via Playwright.
- Zoho mode and WhatsApp mode: Simulated. Synthetic data only.
- Backups taken before each install/migrate (`sites/titan-staging.localhost/private/backups`).

## Results (observed)
| Suite | Command | Result |
|---|---|---|
| Unit/integration (23) | `bench --site titan-staging.localhost run-tests --app titan_desk` | **23/23 OK** |
| HTTP/API (12) | `python3 tests/e2e/http_test.py` | **12/12 passed** — guest redirect and 403, CSRF enforced, role and lead-ownership checks, demo seed, reply |
| Browser (20) | `python3 tests/e2e/ui_test.py` | **20/20 passed** — tour, Getting started, all 7 pages at 1440×900 and 390×844, sending a reply, no console errors |
| Install/uninstall | install → uninstall → reinstall | CRM leads kept; Titan custom fields removed and recreated |
| Static check | `ruff check titan_desk --select E9,F` | clean |
| Scripts | `bash -n scripts/*.sh`; update.sh refuses to run with local changes | see PR description for the run |

## Covered by tests
Roles and permissions per role · take over / assign / pause · keyword and temperature escalation · 24-hour WhatsApp rule · simulated incoming and outgoing messages · spec completeness · follow-up scheduler in supervised mode (approval created once, count incremented) · approve/reject (reason required) · call booking pauses follow-ups and shows on calendar · stage validation · per-user follow-up preference validation · 90-day retention purge · simulated Zoho import idempotency and push · supervised mode expiry.

## Not tested / unverified
- Live Meta WhatsApp sending and webhooks (Meta business not verified; Live mode code path calls frappe_whatsapp's normal insert).
- Real Zoho (no access; simulated by design).
- Email sending through info@titansteel.in (no mail server in sandbox; `frappe.sendmail` queued only).
- `whatsapp_chat` and `frappe_whatsapp_chatbot` interaction (not installed on staging).
- Frappe Cloud deployment and `scripts/init.sh` end to end on a fresh bench.
- Load test (p95 target) not run.
- Titan user acceptance testing.
