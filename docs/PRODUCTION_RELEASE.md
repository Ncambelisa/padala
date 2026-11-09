# Production release guide

Padala is a household allocation-and-evidence record. It is **not** a payment,
remittance, bank-verification, or savings-account product. Do not publish claims
that exceed that boundary.

This guide describes the code-level deployment path added for the production
hardening milestone. It is not a legal, security, privacy, payment, or service
provider certification.

## 1. Do not launch until the owner approves these decisions

1. **Data policy:** complete and approve `docs/PRIVACY_NOTICE_DRAFT.md`, then set
   every `PRIVACY_*` publication field. The API will refuse production startup
   until it can serve a notice at `/privacy` with the controller identity,
   privacy contact, lawful basis, retention period, and processor information.
   Separately approve the deletion process, full export process, backup
   retention, shared-record and member-departure policy, incident response
   owner, and a support contact. The code can revoke a member's access, but it
   does not erase their existing shared records.
2. **Commercial model:** Xendit is selected in the code, but the owner must still
   approve the final price, whether a trial exists (the current implementation
   has no trial), cancellation/refund policy, tax treatment, support process,
   merchant/account identity, and eligible recurring payment channels. Do not
   enable Xendit checkout until those details appear in the public `/terms` page
   and a separate Xendit test-mode acceptance run passes.
3. **Product boundary:** the public copy must state that recipient confirmation is
   self-reported, evidence is not authentic-bank proof, provider confirmation is
   not connected, and savings contributions are not account balances.
4. **Service providers:** contracts/settings for hosting, PostgreSQL, Redis, SMTP,
   private malware scanning, backups, and optional Azure extraction. Do not enter
   credentials in source code or chat.
5. **Independent review:** penetration/security review, accessibility review, and
   Philippine privacy/legal advice before handling real household data. Obtain
   specialist advice before adding payments, funds custody, bank access, or
   provider confirmation.

## 2. Required runtime architecture

Use separate production resources:

- HTTPS reverse proxy/load balancer in front of the Next.js web process.
- Next.js web process, configured with `API_INTERNAL_URL` pointing to the private
  FastAPI API address. Configure that exact address as `INTERNAL_PROXY_ORIGINS`
  and only the Next.js private CIDR as `TRUSTED_PROXY_NETWORKS`. The browser must
  use one public HTTPS origin.
- FastAPI API process, not publicly reachable except through the web proxy.
- Managed PostgreSQL database with encrypted backups and restoration testing.
- Managed TLS Redis endpoint for shared rate limiting.
- A private, authenticated network path to a ClamAV-compatible `clamd` scanner.
  Keep `clamd` TCP private: its protocol itself does not add TLS or authentication.
  Configure its `StreamMaxLength` to at least 5 MB.
- One dedicated `python -m app.worker` outbox worker. Do not run an email worker
  inside every API process.
- Persistent encrypted receipt storage mounted only by the API process. This
  implementation uses the configured server filesystem; use one API instance
  until object storage is implemented, or replace the storage adapter before
  horizontal scaling.
- A public HTTPS route at
  `/api/v1/billing/xendit/webhook`, proxied to the otherwise private FastAPI
  process only for Xendit. It must be protected by the Xendit callback token;
  do not add browser CSRF/origin exemptions to any other route.

The scanner sends receipt bytes via clamd's framed `INSTREAM` protocol and fails
closed when a required scanner cannot be reached. ClamAV documents that TCP clamd
connections should not be exposed to untrusted networks and that `INSTREAM` is
the appropriate protocol for sending bytes to a remote daemon. [ClamAV clamd
protocol documentation](https://docs.clamav.net/manual/Usage/ClamdProtocol.html)

## 3. Production configuration

1. Copy `backend/.env.production.example` into your hosting secret manager and
   set the matching internal value in `frontend/.env.production.example`.
2. Replace every example host and credential with the selected provider value.
3. Set `PADALA_ENV=production`. The API will refuse to start with unsafe local
   settings: SQLite, HTTP origins, insecure cookies, wildcard hosts, local rate
   limiting, an untrusted internal proxy, absent malware scanning, non-TLS SMTP,
   or a background email worker inside the API process.
4. From the backend environment, run:

   ```bash
   python -m app.cli check-production
   ```

   This validates configuration shape only; it does not test provider credentials
   or make a deployment safe by itself.
5. Set `API_INTERNAL_URL` **before** `npm run build`. Next.js compiles its API
   rewrite into the production artifact, so changing only the running container
   environment is not enough. Do not expose this internal address to the browser.
6. Install production dependencies, including `psycopg` and `redis`, then apply
   Alembic migrations through the application startup process in a controlled
   release job. Back up the database first.
7. If and only if the paid plans are approved, set the complete `BILLING_*` and
   `XENDIT_*` values in the secret manager. The selected catalogue is
   `BILLING_BASIC_PRICE_MINOR=9900` (up to four active household members) and
   `BILLING_FAMILY_PRICE_MINOR=14900` (up to eight), with
   `BILLING_TRIAL_MONTHS=1`. The application refuses production startup when
   `BILLING_ENABLED=true` without this valid catalogue, published terms, HTTPS
   origins, server-only Xendit credentials/callback token, the official Xendit
   API base, and `BILLING_ENFORCEMENT_ENABLED=true`.

Do not point production at the local demo database or `backend/demo-data`.

## 4. Deployment and verification checklist

- [ ] Use a new database; never migrate or overwrite demo/pilot data blindly.
- [ ] Verify HTTPS, the public hostname, `APP_URL`, `ALLOWED_ORIGINS`, and
  `ALLOWED_HOSTS` with the actual browser origin.
- [ ] Start exactly one outbox worker and confirm a synthetic invitation and
  password-reset/verified-email link arrive from the verified sender domain.
- [ ] Register a synthetic household. Confirm it cannot sign in until it uses the
  one-time email-verification link, then confirm the resend path and expired-link
  behavior.
- [ ] Visit `/privacy` while signed out. Confirm the legal controller, contact,
  version, purpose/lawful-basis, retention, and current processor details are
  correct. A new registration and invitation acceptance must require the current
  notice acknowledgement; after changing the notice version in a non-production
  test, a signed-in test user must be blocked from household data until it
  acknowledges the new version.
- [ ] Confirm the browser receives a nonce-based Content-Security-Policy and no
  `unsafe-eval` policy in production.
- [ ] Confirm a clean synthetic PNG uploads; confirm the scanner-unavailable path
  rejects uploads; have the security operator validate a safe test signature in a
  non-production environment.
- [ ] Restore a PostgreSQL backup and the corresponding uploads into an isolated
  environment; sign in and download a test file.
- [ ] Test household isolation, session logout/revocation, CSRF failure, rate-limit
  failure, failed SMTP, scanner failure, and database failover.
- [ ] In a synthetic household, revoke a member, confirm their existing session
  and new login are denied, confirm an inactive member cannot receive a new
  assignment, then restore access and confirm they can sign in again. Confirm
  historical records remain unchanged throughout.
- [ ] Run backend tests, frontend typecheck/build, dependency audit, and production
  browser tests for the exact deployment artifact.
- [ ] Before enabling billing, use Xendit **test mode** with a fictional customer
  to complete hosted checkout for both plans, verify the signed
  `recurring.plan.activated` callback starts the one-month trial, and verify a
  signed `recurring.cycle.succeeded` callback is required to retain access after
  trial end. Cancel a pending checkout and active plan, exercise a failed/retried
  cycle, send duplicate and out-of-order callbacks, and confirm a bad callback
  token cannot change access. Verify staff can reconcile the provider dashboard
  with the local provider reference and can follow the published support/refund
  process. Do not make a live charge during this step.
- [ ] Visit `/terms` while signed out. Confirm both exact prices, household-member
  limits, one-month trial wording, effective/version date, support email,
  cancellation, refund, and tax wording.
  Confirm Xendit appears in the published privacy processor/transfer disclosure
  before any customer payment details are sent to checkout.
- [ ] Test real supported phones/browsers, slow networks, keyboard navigation, and
  screen-reader flows with non-sensitive test data.
- [ ] Enable error monitoring, uptime alerts, database/Redis/scanner health alerts,
  log redaction, on-call ownership, and an incident runbook.
- [ ] Remove all demo users/data; do not expose development documentation or any
  invitation/reset token in logs.

## 5. Explicitly still outside this code release

- Live Xendit merchant activation/contracting, payment-channel approval, live
  checkout validation, invoice/tax-document issuance, refund execution,
  chargeback/dispute operations, reconciliation operations, and staffed customer
  billing support. The code has a disabled hosted-checkout/webhook/cancellation
  path only; it is not an operational payment launch.
- Actual money movement, bank account access, independent bank/provider
  confirmation, or live savings balances.
- Full user binary export and user-account deletion/retention implementation.
  Access revocation is implemented, but privacy erasure and a complete
  member-departure workflow still require the owner-approved shared-record policy.
- Object-storage adapter and multi-instance receipt synchronization.
- Native iOS/Android builds, push notifications, and an app-store release.

These are deliberate release gates, not settings that should be bypassed.
