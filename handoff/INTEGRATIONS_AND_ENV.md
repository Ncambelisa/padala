# Configuration, integrations, and security

## 1. Configuration ownership

The launcher copies example files only when the real files are absent. Do not overwrite the owner's `.env` files. Do not print their contents during Codex sessions. Credentials are entered locally, never embedded in this handoff.

| Variable | File | Purpose / local default |
|---|---|---|
| `APP_URL` | `backend/.env` | User-facing origin; `http://localhost:3000` |
| `ALLOWED_ORIGINS` | `backend/.env` | Explicit permitted origins; use the actual app origin |
| `SECURE_COOKIES` | `backend/.env` | `false` for local HTTP; secure-cookie deployment needs HTTPS |
| `REGISTRATION_ENABLED` | `backend/.env` | `true` for demo/E2E; protect or disable before public exposure |
| `EMAIL_VERIFICATION_REQUIRED` | `backend/.env` | `false` for local demo; `true` is required in production and needs working SMTP |
| `EMAIL_WORKER_ENABLED` | `backend/.env` | Enables local outbox worker |
| `DATA_DIR` | `backend/.env` or process env | Optional data directory; default `backend/data` |
| `DATABASE_URL` | `backend/.env` or process env | Optional override; SQLite is the tested baseline |
| `AZURE_DOCUMENT_ENDPOINT` | `backend/.env` | Optional extraction-resource HTTPS endpoint |
| `AZURE_DOCUMENT_KEY` | `backend/.env` | Optional secret extraction key |
| `SMTP_HOST`, `SMTP_PORT` | `backend/.env` | Optional mail transport; port 1025 default is for local testing |
| `SMTP_USER`, `SMTP_PASSWORD` | `backend/.env` | Optional provider credentials |
| `SMTP_STARTTLS` | `backend/.env` | Local sink default false; use true with a compatible real provider |
| `EMAIL_FROM` | `backend/.env` | Sender identity accepted by your provider |
| `BILLING_*` | `backend/.env` | Public plan price (integer centavos), paid-access switch, and customer-facing terms; all default to disabled/blank |
| `XENDIT_SECRET_KEY` | `backend/.env` or secret manager | Server-only Xendit API key; never a `NEXT_PUBLIC_*` value |
| `XENDIT_WEBHOOK_TOKEN` | `backend/.env` or secret manager | Server-only token used to authenticate Xendit callbacks |
| `XENDIT_API_BASE` | `backend/.env` | Official API base; production only accepts `https://api.xendit.co` |
| `API_INTERNAL_URL` | `frontend/.env.local` | Server-to-server API URL; `http://127.0.0.1:8000` |

There is no runtime `OPENAI_API_KEY`, JWT secret, bank password, or OTP requirement in this application. Codex's own authentication is separate from the application configuration.

## 2. Azure extraction — optional implemented adapter

The current adapter submits original uploaded bytes to the configured Azure Document Intelligence `prebuilt-receipt` model using API version `2024-11-30`, then polls its result. These are descriptions of the shipped code, not a promise of current resource/region compatibility. Verify your provider's current service documentation when enabling it.

```dotenv
AZURE_DOCUMENT_ENDPOINT=https://YOUR-RESOURCE.cognitiveservices.azure.com
AZURE_DOCUMENT_KEY=ENTER_LOCALLY_NOT_IN_CHAT
```

Restart the backend after changing configuration. The user must consent before extraction. It suggests merchant, date and total and keeps manual review available. The code checks the returned polling URL's HTTPS origin so it does not send the key to a foreign host.

Before a live test: obtain owner approval, configure a limited development resource, set cost limits through the provider, and use a synthetic document. Test unconfigured credentials, rejected requests, timeout/failure, malformed responses and unsupported documents. A configured indicator does not mean a call succeeded. Do not promise all Philippine receipts or bank slips are supported.

**OCR does not authenticate the receipt, the transaction, or a savings balance.** Keep the label as extraction. Never alter `provider_confirmation` because extraction succeeded.

## 3. SMTP — optional implemented adapter

For a real provider supporting STARTTLS, use its documented settings. An illustrative configuration is:

```dotenv
SMTP_HOST=YOUR_SMTP_HOST
SMTP_PORT=587
SMTP_USER=YOUR_USERNAME
SMTP_PASSWORD=ENTER_LOCALLY_NOT_IN_CHAT
SMTP_STARTTLS=true
EMAIL_FROM=Padala <no-reply@YOUR_VERIFIED_DOMAIN>
```

The current adapter supports ordinary SMTP/STARTTLS; implicit TLS port 465 is not implemented. Do not simply change to port 465 and claim compatibility. The local Compose service supplies Mailpit, which captures messages without sending real email.

Household update emails are optional and avoid receipt amounts/details. Invitation/reset links are sensitive. The current worker uses bounded retries and at-least-once delivery; production deduplication and durable worker operations need separate review. Do not send real emails without explicit approval.

## 4. Xendit monthly subscriptions — selected, disabled until launch configuration

Padala has a server-side Xendit Subscription Session integration for two monthly
PHP household plans: Padala Basic at PHP 99/month for up to four active members,
and Padala Family at PHP 149/month for up to eight. It creates `POST /sessions` with
`session_type: SUBSCRIPTION` and `mode: PAYMENT_LINK`, then redirects the user
to Xendit's hosted checkout. Padala does not render payment fields or collect a
payment token. It stores only reconciliation identifiers, status, and a
short-lived checkout URL; it does not store raw webhooks, card, bank, or
e-wallet credentials.

The Xendit webhook path is `/api/v1/billing/xendit/webhook`. It must be made
reachable through the public HTTPS application proxy, while the FastAPI process
itself remains private. The callback skips browser-origin/CSRF checks because it
is not a browser request, but requires the Xendit `x-callback-token`, limits the
body to 128 KB, verifies reference/amount/currency/provider IDs, and stores a
SHA-256 digest for duplicate suppression. Access begins after
`recurring.plan.activated` (the code also accepts Xendit's documented
underscore event spelling for compatibility). For a household's first completed
enrollment, that starts a one-month free trial; after it ends, a signed
`recurring.cycle.succeeded` callback is required to retain access. A browser
redirect never grants access. Cancellation stops a pending hosted session or
asks Xendit to deactivate the recurring plan; the local state stays
`cancellation_pending` until the signed inactivation callback arrives.

Before any customer can check out, the operator must provide all of the
following in a secret manager and validate them with a separate **test-mode**
run using a fictional customer:

1. The selected catalogue: `BILLING_BASIC_PRICE_MINOR=9900` for Padala Basic
   (up to four active household members), `BILLING_FAMILY_PRICE_MINOR=14900`
   for Padala Family (up to eight), and `BILLING_TRIAL_MONTHS=1`. The first
   completed enrollment per household receives the trial; a re-enrollment is
   paid immediately. Validate the customer-visible wording in test mode.
2. Published `/terms` content: terms version/effective date, real support email,
   cancellation rule, refund rule, and tax treatment. Do not invent the business
   identity, address, tax, or refund wording in configuration.
3. Xendit Subscription product and eligible recurring payment channels enabled
   for the actual Philippine merchant account; confirm the current Xendit
   commercial agreement, fees, and channel availability directly with Xendit.
4. A server-only test `XENDIT_SECRET_KEY`, callback token, and a public HTTPS
   test webhook URL. Configure the webhook token in Xendit Dashboard, not in the
   frontend or repository.
5. Synthetic checkout, cancellation, failed/retried cycle, duplicate/out-of-order
   callback, customer-support, reconciliation, and refund-policy exercises.

Production refuses `BILLING_ENABLED=true` unless the configuration is complete
and `BILLING_ENFORCEMENT_ENABLED=true`; this prevents a deployment from taking
payment while leaving household access free. It does not prove account approval,
tax compliance, refund operations, live delivery, or Xendit availability.

## 5. Independent confirmation — not implemented

No provider has been selected or contracted. A future implementation needs supported account/transaction coverage, user authorization, a reliable transaction identifier, server-side provider responses, status/timestamp tracking, authenticated callbacks when used, replay/idempotency controls, mismatch handling, and refund/reversal logic.

Client uploads and a checkbox cannot create independent confirmation. Unsupported institutions must remain unsupported. Mocks must be visibly test-only. Confirming a deposit does not establish the account's later balance or that money cannot be withdrawn.

Do not add account scraping, credential collection, or fake API responses. Move forward only after the owner selects an authorized provider and its actual contract and documentation are available. Money movement is a separate scope decision.

## 6. Local security boundaries to preserve

Keep HTTP-only sessions, CSRF and origin validation, household authorization on every record/file, upload limits, strict request schemas, exact money totals, protected downloads, safe CSV output and versioned review checks. The existing application log is useful history, not tamper-proof audit storage.

Uploads are untrusted. The current PDF checks do not scan for malware. Exact byte hashes do not detect all edited duplicate images. The database and uploaded files are not application-encrypted. Everyone with active household access can see submitted records. A sender can revoke or restore a member's access, but revocation preserves the shared history; private sub-ledgers, privacy erasure, and full departure handling still need design.

Do not send real receipts, tokens or secrets to coding tools. If working with real data later, define allowed processing, retention, deletion, backups, access requests and third-party handling before launch. Independent security/privacy review remains outstanding; this file is not a legal opinion.

## 7. Production gate, not an implied feature

Before any real household pilot: finish actual frontend validation; test HTTPS/cookies and origin configuration; review credentials and dependencies; protect registration; add appropriate upload scanning/quotas, OCR cost controls, monitoring and backups; demonstrate restoration; approve and implement required export/deletion/privacy-erasure behavior; review consent notices and provider agreements; test physical devices and accessibility.

No automatic public deployment, API purchase, or subscription charging is authorized by this handoff. Xendit is a selected implementation path, not a live merchant-account approval.
