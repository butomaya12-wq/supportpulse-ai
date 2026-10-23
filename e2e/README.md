# Browser E2E — synthetic only

Run by the `browser-e2e` GitHub Actions job with an isolated ephemeral **PostgreSQL 16** service, Chromium and FastAPI bound to localhost. No Mac Docker volume, real account or production customer data is used.

The two tests cover:
- Browser: sign in, seed case, human review and assignment; **no verify button without matching provider proof**; import proof; verify; audit and database persistence after page reload.
- Browser + API: a quote from the **wrong manager** must not unlock verification; a later bounced quote also keeps correction blocked.

### Safety
The tests intentionally refuse to run without `SUPPORTPULSE_E2E_ISOLATED=YES`, a `DATABASE_URL` naming `supportpulse_e2e`, and an `E2E_BASE_URL` bound to localhost. Never point the suite at the regular `supportpulse` database. No personal/customer data.

### CI execution
See `.github/workflows/ci.yml`. Reproducible by manually creating a **separate disposable** local PostgreSQL DB named `supportpulse_e2e`, setting the documented E2E-only variables and running:

```bash
pip install -r requirements-e2e.txt
python -m playwright install --with-deps chromium
SUPPORTPULSE_E2E_ISOLATED=YES pytest -q e2e/ --junitxml=artifacts/browser-e2e/junit.xml
```

The app must already be running at the local `E2E_BASE_URL` using this **isolated test database**, not the Mac user's `supportpulse-ai_postgres_data` volume. On failures, traces and screenshots are saved under `artifacts/browser-e2e`, and uploaded from CI. Traces contain only synthetic payloads and CI demo tokens, but still should not be posted publicly as ordinary screenshots.

### Evidence
Do not claim browser automation PASS until the specific PR commit receives a green `browser-e2e` GitHub Actions job.
