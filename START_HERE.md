# Padala — local Codex handoff

**Prepared: November 3, 2026.** One extracted folder contains the existing Next.js / TypeScript frontend, Python / FastAPI backend, setup files, requirements, API documentation, tests, and instructions for continuing development in Codex.

**This is a development handoff, not a production-certified financial application.** It has not been installed on your device. Application code is preserved from `Padala-NextJS-Python.zip`; the new files organize requirements and the remaining work.

## 1. Extract and open the correct folder

Extract `Padala-Codex-Handoff.zip`. Open **`padala-next-python`**, the folder containing `AGENTS.md`, `frontend`, `backend`, and `run_local.py`, as your Codex project/workspace. Do not work from inside the ZIP.

You do not need the earlier standalone HTML demo or the older starter ZIP. This package includes the latest supplied Next.js/Python source. No previous conversation is needed: the product brief is in `REQUIREMENTS.md`.

## 2. Requirements for your computer

| Requirement | Why it is needed |
|---|---|
| Node.js 22+ and npm | The frontend manifest and launcher require Node 22 or newer. Use a supported compatible release. |
| Python 3.11+ with `venv` and pip | Runs the API, database migrations, and launcher. Backend regression was rerun with Python 3.13.5. |
| Internet access for initial installation | Downloads Python and JavaScript dependencies; Codex and optional providers have their own network needs. |
| A working Codex sign-in | Needed to use Codex, separate from Padala's household sign-in. |
| Git, recommended | Lets you review and revert changes. No remote repository is required. |
| Docker, optional | An alternative local setup exists; Docker is not needed for the standard launcher. |

No bank account connection, OpenAI API key, Azure key, or paid email service is needed to run Padala's core fictional-data demo. **An Azure resource is optional for receipt text extraction, not receipt authentication.**

Do not install dependencies globally except tools you intentionally choose to install, such as Codex. Python application dependencies belong in `.venv`; frontend dependencies belong in `frontend/node_modules`.

## 3. Start Codex in this folder

Using an existing Codex desktop/editor installation: select the extracted folder as the local project, then paste the contents of `CODEX_START_PROMPT.md` into a new task.

Using the terminal:

```bash
cd path/to/padala-next-python
codex
```

When the CLI is not installed, the npm installation option is:

```bash
npm install -g @openai/codex
codex --version
```

Run `codex` in the project and complete its sign-in process. Keep approval and sandbox protections enabled. Allow needed package downloads deliberately; do not use bypass/unsafe modes simply to avoid prompts. See the official references in `handoff/SOURCES_AND_PROVENANCE.md`.

Then paste **the entire contents of `CODEX_START_PROMPT.md`**. The short equivalent is:

> Read AGENTS.md, START_HERE.md, REQUIREMENTS.md, and handoff/CURRENT_STATUS.md. Continue this existing Next.js/TypeScript and Python/FastAPI project. Follow CODEX_START_PROMPT.md: validate dependency versions, run and repair the local build and tests, and report exact results before adding new features. Preserve receipt-verification limits and do not use real family data or paid APIs without permission.

The files explain the context; do not paste secret keys or real receipts into the Codex conversation.

## 4. Run the application yourself

Open a terminal in the project root.

**Windows:**

```powershell
py -3 scripts/preflight.py
py -3 run_local.py --demo
```

**macOS / Linux:**

```bash
python3 scripts/preflight.py
python3 run_local.py --demo
```

The first launcher run installs dependencies, creates example environment files if missing, and starts the fictional household. A dependency installation error must be fixed, not bypassed. Manifest versions are inherited declarations, not a guarantee that every current registry can resolve them.

Open:

```text
Website:       http://localhost:3000
API reference: http://localhost:8000/docs
```

| Fictional role | Email | Password |
|---|---|---|
| OFW/sender | anna@padala.test | PadalaDemo!2026 |
| Family member | miguel@padala.test | PadalaDemo!2026 |

Use separate browser profiles or an incognito window to test both roles. Stop both servers with Ctrl+C. Do not expose the demo accounts publicly.

Detailed Windows/macOS/Linux commands, build/test commands, phone testing, and troubleshooting are in `handoff/LOCAL_SETUP.md`. The preserved original instructions are in `README.md`.

## 5. What Codex should work on first

The immediate milestone is **a locally validated full-stack application**, not a rewrite or an expansion into money transfer services:

1. Review the current source, dependencies, and honest implementation status.
2. Install compatible dependencies; generate a real frontend lockfile.
3. Pass Python tests, TypeScript typecheck, a real Next.js production build, and browser tests through Next's API proxy.
4. Validate the complete two-account receipt workflow and responsive layouts.
5. Document blockers. Configure Azure/SMTP only after you provide credentials privately and explicitly approve live testing.

After that milestone, use `handoff/IMPLEMENTATION_PLAN.md` to select further work. It separates requested core behavior, missing integrations, and proposed future enhancements.

## 6. Know these boundaries

- **59 Python tests passed again during packaging.** The actual Next.js installation/build, dependency-aware typecheck, and real Next.js Playwright run were not performed in this packaging task.
- Azure and SMTP code are present; live credentials and provider validation are not included.
- Provider/bank confirmation, actual money movement, subscriptions, and native app-store binaries are not implemented.
- An uploaded receipt, an OCR result, and OFW acceptance are not independent proof of authenticity.
- Savings evidence records a contribution, not the current balance or continued presence of money.
- Mobile currently means a responsive web application with PWA files. Physical-device installation still needs testing.

## 7. Files to read

| File | Purpose |
|---|---|
| `AGENTS.md` | Persistent project instructions for Codex |
| `CODEX_START_PROMPT.md` | The first task to paste into Codex |
| `REQUIREMENTS.md` | Product goals, rules, scope, and technical requirements |
| `handoff/CURRENT_STATUS.md` | Implemented, untested, missing, and future behavior |
| `handoff/LOCAL_SETUP.md` | Install, run, test, and troubleshoot |
| `handoff/ARCHITECTURE_AND_API.md` | Code map and API/data contracts |
| `handoff/INTEGRATIONS_AND_ENV.md` | Configuration, API credentials, and security boundaries |
| `handoff/IMPLEMENTATION_PLAN.md` | Ordered backlog and release gates |
| `handoff/ACCEPTANCE_TESTS.md` | Concrete conditions to verify |
| `docs/openapi.json` | Existing machine-readable API specification |
| `handoff/PACKAGING_REPORT.md` | Checks performed while preparing this ZIP |
| `FILE_MANIFEST.json` | File hashes for transfer-integrity checks |

Optional: before editing, run `python3 scripts/verify_bundle.py` (Windows: `py -3 scripts/verify_bundle.py`). Expected modifications made later by Codex will naturally differ from the original manifest.
