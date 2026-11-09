# Test report — Padala Next.js / Python rebuild

Prepared November 3, 2026. Tests were performed in the authoring container, not on the user's computer.

## Executed

**Python backend: 59 tests passed.**

Command: `pytest -q --disable-warnings`

Coverage includes account creation, duplicate email handling, password checks and whitespace preservation, session cookies/logout, CSRF, disallowed write origins, per-household isolation, role restrictions, email-bound single-use invitations, recipient acknowledgment, integer money and exact allocation totals, file validation/limits, protected downloads, exact duplicates, receipt splits, clarification/respond/accept transitions, stale review prevention, void accounting, reference/date/amount flags, exports, CSV injection escaping, password-reset token consumption, configuration honesty, and rate limiting.

The Azure adapter was exercised using an HTTP mock for submit/poll/result parsing and rejecting a foreign operation host. SMTP outbox delivery was exercised with a mocked SMTP connection and token-content redaction after sending. **Neither test contacted a real provider.**

The backend suite ran with the initial Alembic migration; each isolated test app initialized a fresh schema.

**TypeScript/TSX syntax transpilation: passed.** This is a syntax/transformation check with the installed TypeScript compiler, not a full dependency-aware `tsc --noEmit` check.

**Browser UI harness: passed.** The source client was transpiled to JavaScript and rendered in Chromium using an available React 16 runtime (with a fragment shim), rather than the requested React 19/Next.js build. An explicit Python/httpx bridge forwarded UI fetch calls to the actual running FastAPI API because direct browser navigation to localhost was blocked. This tested real database mutations and API response handling, but not Next rewrites, hydration, the installed React 19 runtime, or real browser cookie propagation through Next.

Observed workflows: sign-in; dashboard; remittance detail; receipt declaration submission; OFW acceptance; creation of a new allocated padala; creation of a family invitation; sign-out; and a separate family sign-in. No unhandled browser errors occurred in the recorded run.

Horizontal-overflow checks passed at widths **360, 390, 430, 768, 1024, and 1440 px**. The mobile upload dialog also passed its overflow check. Preview screenshots were captured from this harness. See `browser-harness-results.json`.

## Not executed / not established

- npm installation or a generated npm lockfile: registry DNS could not be resolved here.
- Full Next.js/React 19 dependency-aware typechecking, dev startup, production build, hydration, or reverse-proxy cookie tests.
- The included Playwright tests against an actual Next server. Run them on your device after installing dependencies.
- Docker builds or Compose startup; Docker was unavailable in this environment.
- Physical Android/iPhone installation, camera capture, mobile notifications, or app-store packaging.
- Live Azure requests, regional receipt performance, API billing, SMTP authentication/deliverability, bank confirmation, or subscription charging.
- Independent security, accessibility, legal/privacy, load, penetration, backup-restoration, or production-readiness audits.

## Required local acceptance checks

1. `python run_local.py --demo` (or `py -3` / `python3` as appropriate).
2. In frontend: `npm run typecheck`, `npm run build`, `npm audit`.
3. With the two real servers running: `npx playwright install chromium` then `npm run test:e2e`.
4. Try sender and family accounts in separate browser profiles; verify uploads, CSRF, receipt review, downloads, and refresh persistence through Next's `/api/v1` proxy.
5. Configure and test external adapters separately using synthetic documents and your own credentials.

This report deliberately does not describe the application as production-certified or installed on the user's device.
