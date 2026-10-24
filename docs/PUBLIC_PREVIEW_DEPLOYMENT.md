# Public reviewer preview deployment — SupportPulse AI

## Scope / trust boundary

This service is a **public read-only static visualization** of two synthetic SupportPulse AI local test scenarios. It reuses the actual dashboard theme and source-linked synthetic case evidence but **does NOT expose the running Python/PostgreSQL application**. The three browser buttons switch a local timeline only; no database, token, AI model or writable API exists on this deployment.

**Not production-ready; not a live CRM product; not an operational cloud backend.** It must not be advertised as such. The real FastAPI/PostgreSQL/Grafana/on-call system stays isolated on the owner's Mac.

This separation is deliberate: the existing backend uses publicly documented **local demo tokens** and mutable APIs. Pointing that backend directly at the internet would be unsafe. Real customer integrations, robust authentication/authorization and a fully writable hosted demo are separate engineering work.

## Build and verify

```bash
python3 scripts/build_public_preview.py
python3 -m http.server 18082 --bind 127.0.0.1 --directory dist/public-preview
# Visit http://127.0.0.1:18082 on this Mac
```

The builder copies **exactly five** allowlisted files:
`index.html`, `preview.js`, `preview.css`, `cases.json`, `style.css`.
It validates case #1 against original `fixtures/initial.json` / `fixtures/followup.json`, checks mathematical delay values, and refuses the build if secret/API patterns are present. Case #2 is a manually reconstructed synthetic record from the owner's local 007A test, not real user data.

Chromium CI opens both cases, switches states, and confirms that **no /api/** calls occur and all loaded assets originate from the static origin. Backend CI/Postgres integration/browser tests still run separately.

## Render deployment (free static site)

- Git repository: `https://github.com/butomaya12-wq/supportpulse-ai`
- Branch: `main`
- Service type: **Static Site**, plan **free**.
- Build command: `python3 scripts/build_public_preview.py`
- Publish directory: `dist/public-preview`
- Auto-deploy from GitHub: **enabled**.
- No build/runtime environment variables, DB, webhook credentials, private tokens, on-call agent or Render Postgres instance.

After the first Render deploy is actually live, open the exact URL from the Render service response and verify:
1. HTML loads over HTTPS.
2. Both synthetic cases can be opened, three phases work.
3. Browser Network shows only five allowlisted static assets, **no /api/**.
4. `/cases.json` contains only synthetic fixed data, no tokens.
5. README and course matrix link to public URL only after actual external verification.

**Deployment criterion caveat:** a publicly accessible, navigable synthetic showcase **is a deployed demo frontend**, but it is **not a deployment of the working backend**. A peer reviewer may award fewer deployment points than for a fully deployed working API, and this must be disclosed. The official course rubric explicitly permits a publicly reachable application URL *or a clear demo with deployment*, so provide evidence and let reviewers decide.

## CD and future gates

Render static-site auto-deploy from `main` is **continuous deployment for the public preview only**; a public commit triggers a build and deploy after linking the repository. The existing GitHub Actions CI independently tests all code and the public output. **A CI-pass prerequisite for Render builds is not yet configured**; do not represent this as CI-gated CD unless confirmed in Render service settings and real deploy history.

For the full 3-point CI/CD criterion later:
- Development preview should deploy automatically **after green CI** on a `develop`/staging environment.
- Production publication should have a **human approval gate**, separate credentials and rollback documented and tested.
- Capture Render deploy URL, commit SHA, build timestamp, and recovery proof after intentional rollback.
- Never deploy the synthetic fault injection or on-call secret into this public static site.

## Security

- No forms, cookies, tokens, APIs or analytics.
- Static browser Content-Security-Policy restricts scripts/styles/assets to the same origin and `connect-src 'self'` (no arbitrary outbound connections).
- External evidence/documentation links are regular links opened by the visitor. No third-party script is loaded.
- Explicit `STATIC PREVIEW`, `SYNTHETIC`, financial-impact-unknown and no-delivery-confirmation labels throughout.
- No existing Mac compose.yaml, ports, Docker volumes, Postgres cases or oncall audit modified.
