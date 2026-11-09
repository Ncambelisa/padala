# Architecture and API map

This describes the supplied implementation, not a proposed platform migration.

## Request path

```text
Desktop/mobile browser
  -> Next.js UI on :3000
  -> same-origin /api/v1/* request
  -> Next rewrite using server-only API_INTERNAL_URL
  -> FastAPI on 127.0.0.1:8000
  -> SQLAlchemy + SQLite; private upload directory
  -> optional Azure extraction / SMTP outbox
```

The browser sends cookies to its own origin. A separate CSRF token is kept in client memory for writes. Provider credentials live in the backend environment. The default launcher keeps Python bound to loopback even during the optional LAN demo.

## Source map

| File/directory | Responsibility |
|---|---|
| `frontend/app/page.tsx`, `layout.tsx`, `globals.css` | Next route, layout and styling |
| `frontend/components/PadalaApp.tsx` | Current application screens and workflows |
| `frontend/lib/api.ts` | Fetch helper, CSRF header, error handling, money parsing/formatting |
| `frontend/lib/types.ts` | Response contracts used by the UI |
| `frontend/next.config.ts` | Backend rewrite and response headers |
| `frontend/public/` | Icons, manifest and service worker |
| `frontend/tests/household.spec.ts` | Existing real-Next browser scenarios |
| `backend/app/main.py` | Routes, role/household boundaries and workflow orchestration |
| `backend/app/schemas.py` | Validated requests, exact sums and extra-field rejection |
| `backend/app/models.py` | SQLAlchemy entities and constraints |
| `backend/app/security.py` | Sessions, password hashing, CSRF and local rate limiting |
| `backend/app/services.py` | File inspection, Azure calls, email outbox and notifications |
| `backend/app/presenters.py` | Public serialization and totals |
| `backend/app/config.py` | Environment variable definitions and defaults |
| `backend/app/cli.py` | Initialize, seed, reset password, purge abandoned uploads |
| `backend/alembic/` | Versioned schema migration |
| `backend/tests/` | Regression and mocked-provider tests |

## Data relationships

A household has users and remittances. A remittance has allocations, each assigned to a user. An evidence record belongs to one remittance and may have one upload plus several allocation lines. Those lines must reference the same remittance and sum exactly to the evidence amount.

Uploads have a household, owner, content hash, MIME type, size and private storage name. Notification, audit, session, invitation, reset-token and email-outbox records support the surrounding workflow.

Evidence includes versioned review state; caller-provided `expected_version` protects transitions. Monetary input is integer centavos. Source-currency metadata is not a foreign-exchange ledger.

## API contract

The supplied OpenAPI export has **28 paths and 30 operations**. Use `docs/openapi.json` or the local API's `/openapi.json`, not a guessed endpoint list. `docs/API-GUIDE.md` explains the groups, authentication, amounts and errors.

| Group | Representative endpoints, relative to `/api/v1` |
|---|---|
| Authentication | `/auth/register`, `/auth/login`, `/auth/me`, `/auth/logout`, `/auth/password` |
| Household | `/household`, `/invitations`, `/invitations/accept` |
| Remittances | `/remittances`, `/remittances/{rid}`, `/remittances/{rid}/confirm` |
| Receipt files | `/uploads`, `/uploads/{upload_id}/download`, `/uploads/{upload_id}/extract` |
| Evidence | `/evidence`, `/evidence/{eid}/review`, `/evidence/{eid}/respond`, `/evidence/{eid}/void` |
| Notifications/reports | `/notifications`, `/notifications/read`, `/activity`, `/export` |

Successful sign-in returns CSRF information and sets the HTTP-only session cookie. Cookie-authenticated writes require `X-CSRF-Token`; requests also pass the origin check. Preserve cookies in separate API clients. Unauthorized requests must not leak a different household's records.

Supported review requests use `status: accepted` or `status: clarification`, plus `expected_version`. Response and void use a note and version. Refresh on HTTP 409 rather than silently overwriting another review. Uploaded draft files are not financial events until linked to submitted evidence.

### Representative remittance request

Replace the user IDs with real IDs from the fictional household. This is a request template, not a complete authentication script.

```json
{
  "title": "Monthly household support",
  "amount_minor": 3000000,
  "received_on": "2026-11-03",
  "recipient_id": "MEMBER_ID",
  "source_currency": "PHP",
  "source_amount": "",
  "allocations": [
    {"name": "Rent", "kind": "expense", "amount_minor": 1000000, "assigned_to": "MEMBER_ID"},
    {"name": "Groceries", "kind": "expense", "amount_minor": 700000, "assigned_to": "MEMBER_ID"},
    {"name": "School", "kind": "expense", "amount_minor": 500000, "assigned_to": "MEMBER_ID"},
    {"name": "Utilities", "kind": "expense", "amount_minor": 300000, "assigned_to": "MEMBER_ID"},
    {"name": "Savings", "kind": "savings", "amount_minor": 500000, "assigned_to": "MEMBER_ID"}
  ]
}
```

Use current test dates when exercising date checks. Do not place these placeholder identifiers in a deployed environment.

## Change discipline

Keep requests, response types, server serializers, tests and the OpenAPI export consistent. Add a migration for schema changes. Refactor the large frontend component only after the real baseline builds; preserve behavior and accessible labels. Do not introduce PostgreSQL/Redis/queues solely because they appear in a generic architecture template: first select a task with a demonstrated need.
