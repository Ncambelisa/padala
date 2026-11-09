# Local installation, tests, and troubleshooting

Run these commands inside the extracted repository. The new `scripts/preflight.py` is read-only: it checks tools and file presence without installing packages or showing secrets.

## 1. Windows

Install Python 3.11+ and Node.js 22+ with npm. Open a fresh PowerShell terminal in the folder that contains `run_local.py`.

```powershell
py -3 --version
node --version
npm.cmd --version
py -3 scripts/preflight.py
py -3 run_local.py --demo
```

`npm.cmd` avoids invoking a PowerShell script shim when local execution policy prevents it. Do not broadly disable PowerShell security controls. The provided `start-windows.bat` also launches the demo.

## 2. macOS / Linux

Install Python 3.11+ with venv/pip and Node.js 22+ with npm. From the repository root:

```bash
python3 --version
node --version
npm --version
python3 scripts/preflight.py
python3 run_local.py --demo
```

On Linux, install the appropriate distribution package for Python venv support when unavailable. Do not install application packages into the system Python to work around an environment error. Windows users choosing WSL should use Linux Python/Node inside WSL consistently, rather than mixing virtual environments across operating systems.

## 3. Startup behavior

The launcher creates `.venv`, copies `backend/.env.example` to `backend/.env` and `frontend/.env.local.example` to `frontend/.env.local` only when the targets do not exist, installs backend runtime dependencies and frontend packages, and initializes the selected database.

`--demo` uses `backend/demo-data` and seeds fictional accounts once. Normal mode uses `backend/data` unless the owner has supplied a different data/database setting. Review custom environment settings before assuming data isolation. Never supply a real database URL to a demo test.

Website: `http://localhost:3000`. API docs: `http://localhost:8000/docs`. Stop the launcher with Ctrl+C. It runs the development frontend, not the production frontend.

Use `anna@padala.test` or `miguel@padala.test` with `PadalaDemo!2026` only for fictional data. These are deliberately public sample credentials.

After a successful install:

```bash
python3 run_local.py --demo --no-install
```

Windows: replace `python3` with `py -3`. Omit `--demo` to start a separate empty household database. Do not delete existing data to change modes.

## 4. Backend regression

The launcher installs runtime dependencies, not pytest. Install developer requirements before running tests.

**Windows, from root:**

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
cd backend
..\.venv\Scripts\python.exe -m pytest -q
cd ..
```

**macOS / Linux, from root:**

```bash
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd backend
../.venv/bin/python -m pytest -q
cd ..
```

Use the included temporary-database tests; do not repoint them to a family database. The pre-handoff baseline is 59 passing cases. Add relevant regression coverage for changes.

## 5. Actual frontend validation

From root after dependency installation:

```bash
cd frontend
npm run typecheck
npm run build
npm audit
```

On PowerShell use `npm.cmd` where required. No `npm test` or lint script is defined in this baseline. Do not pretend missing commands succeeded.

The first verified `npm install` creates `package-lock.json`. Commit that real lockfile after review. Use `npm ci` for future reproducible installation only after it exists. A security audit can report issues even when compilation succeeds; record and triage them rather than applying forced upgrades automatically.

### Real-server browser tests

Keep the demo launcher running in Terminal A. In Terminal B, inside `frontend/`:

```bash
npx playwright install chromium
npm run test:e2e
```

These tests create fictional registered households and require registration to be enabled. There are desktop and mobile-emulation projects. Test traces can contain screenshots/records: keep them out of source archives, especially after any real-data testing.

### Test the production frontend separately

After a successful `npm run build`, stop the dev launcher to free ports. In Terminal A start only the backend using the same fictional data location:

**Windows, from root:**

```powershell
$env:DATA_DIR = Join-Path (Get-Location) 'backend\demo-data'
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

**macOS / Linux, from root:**

```bash
export DATA_DIR="$PWD/backend/demo-data"
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In Terminal B, inside `frontend/`:

```bash
npm run start
```

Open the same website and confirm session cookies, uploads, review and downloads through `/api/v1`. Stop both with Ctrl+C. Environment variables set in one terminal do not automatically configure the other terminal.

## 6. Common issues

| Problem | What to do |
|---|---|
| `node`/`npm` not found | Install supported Node with npm; reopen the terminal and rerun preflight. |
| `py`/`python3` not found | Install Python and use the available launcher. Verify its version. |
| npm `ETARGET`, incompatible peer packages, or registry failure | Distinguish unavailable versions from network/proxy failures. Have Codex verify actual compatible versions, document changes, and reinstall normally. Do not fabricate a lockfile. |
| Package downloads blocked in Codex | Approve the necessary network/install operation or run installation manually. Do not disable all sandbox protections. |
| Ports 3000/8000 in use | Stop your own previous server, or run with `--web-port 3001 --api-port 8001`. Do not terminate unrelated processes. |
| Sign-in works but writes return 403 | Check the actual browser origin, CSRF header, proxy and `ALLOWED_ORIGINS`. Do not disable CSRF. |
| Extraction disabled | Expected until Azure endpoint/key are privately configured. Manual entry must still work. |
| Invitations/password-reset emails do not arrive | Configure/test SMTP; Mailpit is local-only. Use the preserved CLI recovery instructions when needed. |
| Mobile upload rejects HEIC | Export a synthetic test image as JPEG/PNG/WebP. Do not rename a HEIC extension and expect conversion. |
| Database/schema error after changes | Back up first; inspect Alembic and data-path settings. Never delete a user's database to make startup succeed. |
| Current balance differs from savings records | The app tracks contributions, not a connected bank balance. Do not relabel it as a live balance. |

## 7. Phone and optional Docker

After local desktop validation, fictional same-Wi-Fi testing is supported by the launcher:

```bash
python3 run_local.py --demo --no-install --lan-ip 192.168.1.25
```

Use the computer's actual private address and open `http://THAT-ADDRESS:3000` on the phone. HTTP LAN testing is unencrypted; use fictional data and a trusted network only. Do not configure internet port forwarding. HTTPS and physical-device tests are separate prerequisites for a real mobile pilot.

Docker setup is optional: `docker compose up --build`. It includes a local Mailpit inbox on port 8025. It has not been executed as part of this handoff. Never run `docker compose down -v` on valuable data: it removes the named volume.

## 8. Backups and transfer

Stop writes before copying local database and upload directories together. A JSON report is not a restoration backup. Keep private backups separate from this source folder and protect them appropriately. The original data model is not compatible with a different starter database merely because both products are called Padala.

For source transfer, use the supplied ZIP with examples only. Do not add `.env`, `.venv`, `node_modules`, local databases, uploads, private test traces, or API keys.
