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

## Verified provider deployment metadata (2026-10-24)

- **Render service name:** `supportpulse-ai-review-demo`.
- **Service ID:** `srv-dbeg1vu7bikc738b6rsg`, [dashboard](https://dashboard.render.com/static/srv-dbeg1vu7bikc738b6rsg).
- **Public URL allocated:** https://supportpulse-ai-review-demo.onrender.com
- **Initial deploy ID:** `dep-dbeg2067bikc738b6t1g`.
- **Initial Git SHA:** `d38d753d0cdc671f0ffa52a204efb87895a017c2` (PR #20).
- **Deployment status:** Render reported **LIVE**, completed 2026-10-24 19:03:59 UTC, after running the exact build command `python3 scripts/build_public_preview.py`, publishing `dist/public-preview`.
- **Service configuration:** Static Site; GitHub `main`; autoDeploy=`yes` / trigger=`commit`; **zero configured environment secrets**, no persistent disk or Postgres.
- **Application verification:** 4/4 GitHub CI jobs passed on PR #20; CI launches Chromium against built static bundle, verifies 2 cases and 3 evidence stages, and blocks any backend `/api/` calls.
- **External end-user HTTP proof:** **PENDING**. Render control plane says LIVE but direct HTTPS retrieval via assistant's available external checking environments failed because DNS/request was inaccessible to those environments. Owner browser verification is needed before claiming a full external acceptance pass.
- **CD trigger proof:** Auto-deploy from GitHub main is enabled; the README update after the initial deploy should trigger a later Render deployment. Inspect actual subsequent deployment record and commit SHA before claiming tested CD.

