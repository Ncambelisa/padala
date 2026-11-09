# API guide

The application defines **38 operations across 36 API paths**, plus FastAPI's developer documentation.

Local interactive specification: `http://localhost:8000/docs`

Machine-readable specification: `http://localhost:8000/openapi.json`

An exported copy is included as `docs/openapi.json`; import it into your API client. Responses are documented further by `frontend/lib/types.ts` and the API tests. The request models appear in OpenAPI.

## Authentication

Use the web UI or `POST /api/v1/auth/login` with a JSON email/password. A successful response sets an HTTP-only session cookie and returns a separate `csrf` value. Send that value as `X-CSRF-Token` for authenticated POST/PATCH requests. `/auth/me` can refresh the CSRF value for the existing session. Tokens are not kept in browser local storage.

When a published privacy-notice version has not been acknowledged, `/auth/me`
still returns the session and marks acknowledgement as required, but household
data endpoints return HTTP 428. Submit the displayed version to
`POST /auth/privacy-notice`, with the session and CSRF header, after the user
has read the notice. New registration and invitation-acceptance requests carry
the same `privacy_notice_version` field.

The server checks write origins against `ALLOWED_ORIGINS`. Do not disable CSRF to fix an incorrectly configured hostname; correct the origin configuration instead. Unauthenticated login/register/reset endpoints are rate-limited and origin-checked. They do not require a pre-login CSRF token.

A sender can revoke a member's household access with `POST
/household/members/{member_id}/revoke` and restore that existing account with
`POST /household/members/{member_id}/restore`. Revocation deletes all active
sessions and blocks sign-in and future assignments immediately. It deliberately
does not erase shared remittance, evidence, or audit history; a privacy erasure
request remains a separate operator process.

When `BILLING_ENFORCEMENT_ENABLED=true`, a household without an entitled Xendit
subscription receives HTTP 402 from household-record endpoints. A signed plan
activation starts the selected plan's one-month first-enrollment trial. After
the trial end, access continues only after a signed successful recurring cycle.
A `cancellation_pending` household keeps its existing access only until the
signed inactivation callback arrives. `/auth/*` and `/billing/*` remain
reachable so a signed-in user can manage account or subscription access. A
browser return from checkout never activates the plan; the callback at
`/billing/xendit/webhook` is intentionally unauthenticated by cookie/CSRF but
verifies Xendit's `x-callback-token`, checks the provider
reference/amount/currency/session or plan IDs, and records a payload digest to
reject duplicate delivery.

## Groups

| Group | Operations |
|---|---|
| System | `GET /health`, `GET /config` |
| Accounts | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`, `POST /auth/password`, `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/resend-verification`, `POST /auth/verify-email`, `POST /auth/privacy-notice`, `PATCH /auth/preferences` |
| Billing | `GET /billing/subscription`, `POST /billing/checkout`, `POST /billing/cancel` |
| Household | `GET /household`, `POST /household/members/{member_id}/revoke`, `POST /household/members/{member_id}/restore`, `POST /invitations`, `GET /invitations/{token}`, `POST /invitations/accept` |
| Padala | `GET /remittances`, `POST /remittances`, `GET /remittances/{id}`, `POST /remittances/{id}/confirm` |
| Uploads | `POST /uploads` (multipart field `file`), `GET /uploads/{id}/download`, `POST /uploads/{id}/extract` |
| Evidence | `GET /evidence`, `POST /evidence`, `POST /evidence/{id}/review`, `POST /evidence/{id}/respond`, `POST /evidence/{id}/void` |
| Notifications | `GET /notifications`, `POST /notifications/read` |
| Reports | `GET /activity`, `GET /export?format=json`, `GET /export?format=csv` |

All paths in the table are relative to **`/api/v1`**. Format variants share one export operation.

## Amounts and evidence

API amounts use **positive integer centavos**: `amount_minor: 12345` means PHP 123.45. Decimal/float/string amounts are rejected for financial fields. Optional `source_amount` is a decimal string for original-currency metadata; no automatic exchange-rate conversion occurs.

Each allocation belongs to one remittance. Receipt line splits must use distinct allocations from that same remittance and total the receipt amount exactly. A family member may submit only to their assigned allocations. A sender can submit records as well; the subsequent acceptance remains an OFW judgment, never provider confirmation.

Uploaded files are separate drafts. Submitting a receipt links one draft to one evidence record. Identical file bytes cannot produce a second expense; a duplicated unsubmitted draft by the same uploader returns the existing upload identifier. A deliberately altered image may evade exact-hash comparison. References and overruns produce clarification flags, not fraud conclusions.

Review/respond/void requests include the current `expected_version` from the evidence response. A stale version returns HTTP 409. Refresh the receipt before resubmitting; do not silently overwrite another person's review.

## Status meanings

`pending → accepted` or `pending → clarification → pending → accepted`.

`voided` records remain in history but are excluded from totals. The original supporting file remains associated with that record. This is not a complete accounting adjustment/refund subsystem.

`provider_confirmation` is always `not_connected`. The backend forbids unknown input properties, so a caller cannot create a verified flag. Azure supplies extraction suggestions only.

## Error handling

400: invalid action or context; 401: sign-in required; 402: a configured paid-access rule requires an active subscription; 403: role/CSRF/origin restriction; 404: unavailable or out-of-household record; 409: duplicate or stale record; 413: file/body too large; 422: validation or document extraction issue; 428: current privacy notice must be acknowledged before household data is shown; 429: local rate limit; 502/503/504: external provider unavailable, unconfigured, or timed out.

The core JSON API is used by the Next client. The interactive docs are a developer convenience, not an end-user authentication UI. For cookie-authenticated writes from a separate API client, preserve its cookie jar and supply the CSRF header.
