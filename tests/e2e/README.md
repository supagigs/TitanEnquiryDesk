# End-to-end checks (staging only)

Run against an isolated staging site served at http://127.0.0.1:8000 (`bench use <staging-site>` then `bench serve --port 8000`).
Create the two synthetic users first (`mirza@titan.test` manager+admin, `sales@titan.test` sales user, password `Titan@12345`), with Zoho and WhatsApp in Simulated mode.

```bash
python3 tests/e2e/http_test.py   # API, permissions, CSRF, guest access
python3 tests/e2e/ui_test.py     # browser journeys + screenshots (needs playwright + chromium)
```
Never point these at production.
