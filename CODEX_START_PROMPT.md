# Paste the text below into Codex from this repository

You are continuing my existing Padala application. Read `AGENTS.md`, `START_HERE.md`, `REQUIREMENTS.md`, `handoff/CURRENT_STATUS.md`, and `handoff/LOCAL_SETUP.md` before making changes. This package contains the source code: extend and repair it rather than starting over.

My product is an OFW family remittance allocation and evidence-record system. An OFW records money received by the family and allocates it to expenses or savings. Family members upload receipts against those allocations. The app extracts supported fields when configured, checks available information, notifies the OFW, supports review/clarification, and keeps the history for each remittance. Do not claim arbitrary receipts are authentic: independent provider verification is not connected. Savings records are contributions, not current balances.

Use Next.js App Router, TypeScript and React for the responsive web/PWA interface, and Python FastAPI for the backend. Retain SQLite for the local milestone. Keep existing account, session, CSRF, household isolation, money-validation, file-upload, review, and notification protections.

Complete this first milestone: validate and repair the existing app so it runs locally through the actual Next.js frontend and Python API.

1. Inspect source, Git status, manifests, environment examples, and known gaps. Run the read-only preflight. Summarize a short plan and proceed with reversible local work.
2. Check the declared package versions for availability and compatibility. Install Python dependencies in `.venv` and JavaScript dependencies in `frontend`. Preserve existing environment files. Generate the real npm lockfile. Explain any necessary dependency changes; do not bypass errors using unsafe flags.
3. Start the fictional demo. Run the Python regression suite, TypeScript typecheck, Next production build, and dependency audit. Fix application errors and add tests without weakening authorization or deleting coverage. Report environmental or network blockers explicitly.
4. Exercise the supplied Playwright tests against actual Next.js and FastAPI servers. Add a two-role test covering invitation/member sign-in, remittance allocation, receipt upload, notification, clarification/response, OFW acceptance, and refresh persistence. Add negative checks for household isolation and forged verification flags where appropriate.
5. Check 360px, 390px, 768px, and 1440px layouts; ensure dialogs and receipt forms are usable with keyboard and mobile widths. Use synthetic sample receipts only. Clearly distinguish emulation from physical-device testing.
6. Keep Azure and SMTP optional. Confirm disabled states and mocked adapters first. Ask me to enter credentials privately in `backend/.env` and obtain approval before real API calls, charges, or emails. Do not ask me to paste keys into chat.
7. Update documentation only to reflect work actually done. Create `handoff/LOCAL_VALIDATION_RESULTS.md` with environment versions, commands, outcomes, changed files, and outstanding blockers. Give me exact start/stop instructions.

Do not begin bank integrations, remittance processing, subscription billing, public deployment, destructive data migrations, or a native-mobile rewrite in this first task. The future plan is in `handoff/IMPLEMENTATION_PLAN.md`; propose the next milestone after the existing local build works. Do not mark this application production-ready based only on local tests.
