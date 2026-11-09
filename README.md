# Padala — Next.js + TypeScript + Python

A local-first full-stack implementation of the OFW household workflow:

**Record a padala → allocate its amount → family submits evidence → automatic checks → OFW review → notifications → a shared per-remittance history.**

This is a runnable development project, not an installed application on your computer and not a production financial service. The interface is responsive for desktop and mobile browsers; PWA files are included. It is not an Android APK or an iOS native app.

For the code-level production hardening controls and the remaining owner/provider
release gates, read [docs/PRODUCTION_RELEASE.md](docs/PRODUCTION_RELEASE.md).

## What is implemented

| Area | Implementation |
|---|---|
| Frontend | Next.js App Router, TypeScript, React, custom responsive interface |
| Backend | Python FastAPI, validated request schemas, REST API and OpenAPI documentation |
| Persistence | SQLite via SQLAlchemy; versioned Alembic migrations; protected file storage |
| Accounts | OFW registration, production verified-email gate, password sign-in, HTTP-only session cookies, CSRF tokens, household permissions |
| Family | Single-use, email-bound invitation links; separate family sign-ins |
| Remittances | Amount received in PHP, original currency metadata, recipient acknowledgment, allocations that sum exactly |
| Evidence | Image/PDF upload, manual fields, declarations without a receipt, one receipt split across allocations |
| Checks | Exact-file duplicate prevention, reference reuse flags, date checks, allocation overruns, extracted-total mismatch |
| Reviews | OFW acceptance, clarification requests and responses, voiding with a reason, optimistic concurrency checks |
| Savings | Recorded contributions separated from spending; never displayed as a current bank balance |
| Notifications | Persisted in-app notifications; polling while the app is open; optional SMTP email outbox |
| Exports | Per-remittance JSON with evidence metadata and activity; CSV allocation summary |
| Extraction | Real Azure Document Intelligence REST adapter, disabled until server credentials are configured and the uploader consents |
| Recovery | Password change, SMTP password-reset and verified-email flows, local administrator password-reset command |

**Not implemented:** bank/merchant authentication, actual remittances, custody, live subscription operations, native store binaries, push/SMS delivery, automatic reversals/refunds, reallocation after creation, private per-member ledgers, multiple households per account, or import of the previous starter's database. A disabled Xendit hosted-subscription path implements PHP 99/149 plans and a one-month first-enrollment trial, but has no commercial terms, live account, or provider validation. The JSON export is not a complete database backup.

## Verification and build status — read first

The Python suite passed **59 tests** here. TypeScript/TSX syntax transpilation passed. A restricted browser harness exercised the client against the real Python API and checked six widths.

**A real `npm install`, complete React 19/Next.js typecheck, Next.js development/production build, Docker build, and native-device installation were NOT executed here.** The environment could not resolve the npm registry, and browser navigation to local servers was restricted. The UI harness used an available React 16 runtime with transpiled source and a Python HTTP bridge; it is not a substitute for the supplied Next.js Playwright tests. See `docs/TEST-REPORT.md`.

The Azure REST and SMTP adapters have mocked contract tests, not live provider certification. No API keys are supplied. Screenshots in `docs/` come from the disclosed browser harness.

## 1. Requirements

Install **Node.js 22 or newer** (with npm) and **Python 3.11 or newer**. Internet access is needed to install packages the first time. The Python backend was tested with Python 3.13.5.

The project is written for Windows, macOS, and Linux, but the supplied launchers were not executed on your operating system. You do not need a paid API or a bank account to use the core local workflow.

## 2. Start the fictional demo

Extract the ZIP. Open a terminal in the `padala-next-python` folder.

**Windows PowerShell / Command Prompt**

```powershell
py -3 run_local.py --demo
```

Or double-click `start-windows.bat` after installing Python and Node.

**macOS / Linux**

```bash
python3 run_local.py --demo
```

Or run `bash start-macos-linux.sh`.

The launcher creates a Python virtual environment, installs dependencies, copies example environment files when missing, prepares an isolated demo database, and starts the two local servers. It does not overwrite existing environment files or erase an existing demo.

Open:

```text
Web application:   http://localhost:3000
API documentation: http://localhost:8000/docs
API health:        http://localhost:8000/api/v1/health
```

Keep the terminal open. Press **Ctrl+C** to stop both processes.

| Fictional account | Email | Password |
|---|---|---|
| OFW | `anna@padala.test` | `PadalaDemo!2026` |
| Family | `miguel@padala.test` | `PadalaDemo!2026` |

The demo contains one ₱30,000 plan. Seed records are explicitly fictional declarations, not bank-confirmed receipts. Sample receipt images are in `samples/`. Use a private/incognito browser window for the second account.

On later runs, skip reinstallation:

```bash
python3 run_local.py --demo --no-install
```

On Windows substitute `py -3` for `python3`.

## 3. Create your own empty household

```bash
python3 run_local.py --no-install
```

Omit `--no-install` when dependencies are not installed yet. Choose **Create a household** on the login screen. The normal database lives in `backend/data`; fictional demo mode uses `backend/demo-data`. Do not use the known demo credentials for a real pilot.

Choose **My family → Invite family**, then copy the generated invitation or enable email. The link grants household membership; send it only to the intended person. A localhost link cannot be opened from another computer unless you configure a reachable address.

## 4. Try the complete core workflow

1. Sign in as the OFW. Select **New padala**. Enter the actual pesos received and allocate the total. Choose the family member as recipient and allocation assignee.
2. Sign in as the family member in another browser profile. Open the padala, acknowledge receiving the funds, and choose **Add evidence**.
3. Upload a synthetic sample receipt, confirm its fields, and assign it to an allocation. Split one receipt across multiple allocations when necessary; the split total must equal the receipt amount. Without a file, provide an explanation.
4. The system checks the available data and creates an in-app notification. The OFW can accept the record or request clarification.
5. The uploader responds to clarification. The OFW reviews again. Changes remain visible in the record history.
6. Open **Reports** for CSV and JSON exports. On mobile, Reports and Sign out are available in **Settings**.

Upload is a separate operation from submission. Abandoned uploads do not count as expenses. The administrator can purge unsubmitted uploads older than 24 hours:

```bash
# From backend/, using the virtual-environment Python:
../.venv/bin/python -m app.cli purge-unused-uploads
```

On Windows use `..\.venv\Scripts\python.exe`.

## 5. Optional: actual Azure receipt-extraction calls

Create your own supported Azure Document Intelligence resource. Put its endpoint and key in **`backend/.env`**, not in chat and not in the frontend:

```dotenv
AZURE_DOCUMENT_ENDPOINT=https://YOUR-RESOURCE.cognitiveservices.azure.com
AZURE_DOCUMENT_KEY=YOUR_PRIVATE_KEY
```

Restart the Python server. Upload a document, check the consent box, and select **Extract details**. The backend sends the original bytes to Azure's `prebuilt-receipt` model using REST API version `2024-11-30`, polls for the result, and suggests the merchant, date, and total. Its operation URL must remain on the configured HTTPS origin.

Review all extracted values. The prebuilt receipt model is not guaranteed to understand every Philippine bank slip, school record, transfer screenshot, or handwriting. Unsupported documents still permit manual entry. Check your Azure region, limits, privacy terms, and usage charges directly.

**OCR is extraction, not authenticity verification.** No endpoint in this build can upgrade an arbitrary upload to “bank confirmed.” A genuine deposit record also cannot prove that money remains in savings.

## 6. Optional email

For a real SMTP service, configure your provider's server-side settings in `backend/.env`:

```dotenv
SMTP_HOST=YOUR_SMTP_HOST
SMTP_PORT=587
SMTP_USER=YOUR_USERNAME
SMTP_PASSWORD=YOUR_PRIVATE_PASSWORD
SMTP_STARTTLS=true
EMAIL_FROM=Padala <no-reply@YOUR_VERIFIED_DOMAIN>
```

This adapter supports plain SMTP for a local sink and STARTTLS for a suitable real provider. It does not implement implicit TLS on port 465. Verify the sender with your provider. Do not disable TLS on an untrusted network.

Invitations and password resets use a database-backed outbox. A single background worker retries failures a bounded number of times. Household-update emails are opt-in in Settings and omit financial details. “Configured” in Settings means credentials are present, not that delivery has been verified.

Without SMTP, copy invitation links manually. Reset a forgotten local password from the backend folder:

```bash
../.venv/bin/python -m app.cli reset-password --email you@example.com
```

The command prompts privately for the new password and revokes active sessions.

## 7. Optional Docker setup

Docker Compose files are included but were **not built or run in this environment**. Install Docker Desktop or Docker Engine with Compose, then:

```bash
docker compose up --build
```

Open the website on port 3000. A local Mailpit inbox is exposed only on `http://localhost:8025`; it captures test emails and does **not** deliver them to real recipients. The API is on localhost port 8000.

Create fictional accounts after startup when desired:

```bash
docker compose exec api python -m app.cli seed
```

For Azure in Docker, put only the required variables in a root `.env` read by Compose. Do not commit it. The backend database and uploads persist in the named `padala-data` volume. `docker compose down` preserves that volume; `docker compose down -v` destroys it.

No PostgreSQL instance is included or certified. SQLite is the tested storage for this local implementation. A production database change requires appropriate drivers, migrations, concurrency tests, and backup validation.

## 8. Open it on a phone on the same Wi-Fi

First complete desktop setup. For a fictional-data demonstration, obtain your computer's private IPv4 address and run:

```bash
python3 run_local.py --demo --no-install --lan-ip 192.168.1.25
```

Replace the address with your own computer's address. Open `http://192.168.1.25:3000` on your phone. Allow the local port through your firewall only on a trusted private network. The API remains loopback-only; Next proxies API calls. Do not configure internet port forwarding.

This optional HTTP LAN mode is **not encrypted** and is for synthetic data only. A LAN IP is not the phone's own localhost. PWA installation and service-worker behavior need a secure context on real devices; use a properly configured HTTPS deployment for a real pilot. No physical phone test was performed here.

## 9. Manual developer startup

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

Terminal A:

```bash
cd backend
../.venv/bin/python -m app.cli init
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log
```

Terminal B:

```bash
cd frontend
npm install
npm run dev
```

For Windows, use `Copy-Item` instead of `cp` and `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

## 10. Tests and production-build check

```bash
# Backend, from backend/:
../.venv/bin/python -m pytest -q

# Frontend, from frontend/ after npm install:
npm run typecheck
npm run build
npm audit

# Real Next.js browser tests, with both servers running:
npx playwright install chromium
npm run test:e2e
```

The supplied E2E tests create fictional households. Run them only against a development database with registration enabled. Stop the development frontend before starting a production frontend on the same port:

```bash
npm run start
```

The first successful npm install creates a `package-lock.json`; keep and commit it. No lockfile was fabricated here. Once validated, use `npm ci` in your CI pipeline and pin reviewed package/container versions. Dependency vulnerability scans were not run here because the registry was unreachable.

## 11. Architecture and files

```text
frontend/
  app/                    Next App Router entry and global styling
  components/             TypeScript application and original SVG UI icons
  lib/                    API client, money parsing, shared types
  public/                 Manifest, icons, network-only service worker
  tests/                  Playwright tests for the real Next.js installation
backend/
  app/main.py             REST endpoints and request boundary checks
  app/models.py           SQLAlchemy data model
  app/schemas.py          Pydantic request validation
  app/security.py         Passwords, sessions, CSRF and local rate limiting
  app/services.py         Azure adapter, notification/email outbox, file checks
  app/presenters.py       Explicit public response serialization and totals
  app/cli.py              Initialize, seed, password reset, unused-file purge
  alembic/                Versioned schema migrations
  tests/                  API, authorization, workflow, and adapter tests
scripts/                  Running-system diagnostic
samples/                  Clearly fictional sample receipt images
docs/                     API spec, setup detail, boundaries, test report, previews
run_local.py              Cross-platform installer/launcher
compose.yaml              Optional local Docker + Mailpit setup
```

The browser sends authenticated requests to `/api/v1/*` on its own origin. Next proxies them to the Python API. Session tokens are HTTP-only cookies; the separate CSRF token stays in client memory. No bank password, OTP, or payment-provider secret belongs in the browser.

## 12. Before real household information

Read `docs/SECURITY-AND-LIMITS.md`. This application has not received an independent security, privacy, accessibility, or legal review. It has no automatic bank authentication, no payment custody, no live subscription operation, and no production support arrangement. Its disabled Xendit checkout code is not permission to charge customers. Keep records fictional until you have appropriate hosting, TLS, access controls, backup/restore tests, consent and retention rules, and a review of the intended live service.

Working name: Padala. Brand/trademark clearance has not been performed.
