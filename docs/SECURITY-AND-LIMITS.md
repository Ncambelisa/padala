# Security, verification, and deployment boundaries

## Evidence vocabulary

- **Submitted evidence:** a family member supplied a file or declaration.
- **Checks completed:** the implementation checked entered/extracted metadata, exact-byte file reuse, repeated references, and amounts. The document may still be fabricated.
- **OFW accepted:** the OFW accepted the explanation. This is not bank, merchant, school, or government authentication.
- **Provider confirmation: not connected:** no independent transaction confirmation exists in this codebase. Clients cannot submit a “verified” flag.
- **Savings contributions:** amounts assigned to savings evidence. This is neither a live account balance nor proof funds remain in the account.

Allocation attribution is household bookkeeping, not tracing fungible funds after they are mixed. Actual bank accounts are not segregated, controlled, or locked by this app. The record of an outbound remittance and the record of a completed bill are different events.

## Implemented technical protections

Argon2 password hashing; HTTP-only SameSite session cookies; hashed session/invitation/reset tokens in the database; server-side CSRF checking; an explicit write-origin allowlist; household scoping; upload ownership checks; recipient-only acknowledgment; sender-only review and invitations; sender-controlled member access revocation with immediate session invalidation and controlled restoration; invitation expiry and single-use consumption; password-reset expiry and session revocation; a recorded acknowledgement of the current published privacy-notice version before household data is exposed; positive integer centavos; exact sum validation; optimistic version checking for receipt decisions; exact-file reuse prevention; MIME inspection for supported images/PDF signatures; private authenticated file downloads; bounded request size; no-store API responses; CSV formula escaping; and an event history.

The event history is an application audit log, **not** tamper-proof storage. A local/database administrator can change it. Files are original bytes, not signed attestations. Exact hashes do not catch resized, cropped, rephotographed, or edited duplicates.

## Local-development limitations

1. SQLite and a single application/email worker are the validated local architecture. API rate limiting is process-local. Distributed deployment needs a shared limiter, a proper work queue, measured performance, and concurrency testing. Email is at-least-once and may duplicate after a crash.
2. Stored receipts and the SQLite database are not application-level encrypted. Use device encryption/access controls, appropriate encrypted hosting/storage, and secure backups for a real pilot. Never include runtime data in your source ZIP.
3. Uploaded PDFs are signature-checked, not fully parsed or malware-scanned. They are download-only. Do not open untrusted PDFs without appropriate endpoint protections. Image formats are limited to PNG, JPEG, and WebP; HEIC conversion is not implemented.
4. Production mode requires a one-time verified-email link before a newly registered or invited user can sign in; development can keep this off for local demos. This proves control of the email inbox, not a person's legal identity. There is still no bot protection, formal identity assurance, or protection against a recipient voluntarily sharing an invitation link. Protect or disable public registration until bot-abuse controls and support operations are ready.
5. Everyone with active access in a household can see its submitted records and member directory. Unsubmitted upload drafts are visible only to the uploader. A sender can revoke and later restore a member's access; revocation signs the member out, blocks sign-in and future assignments, and preserves existing shared records and audit history. It is not account deletion, record erasure, or a private sub-ledger. There is no child account, multiple-household role, granular financial permission, or administrator UI.
6. There is no automatic refund/reversal synchronization, carry-forward ledger, or approved reallocation workflow. A void excludes the record from totals but preserves its history/file association. Do not reuse the same receipt as a new purchase after voiding it. Corrected underlying financial events require a designed adjustment workflow.
7. Files are not cached offline. In-app notifications refresh while the app is visible; background push/SMS is not implemented.
8. User-driven account deletion/export of every binary file is not implemented. The JSON export contains evidence metadata and history, not uploaded binaries, credentials, or a database restore image. Design retention, access requests, deletion, shared-record erasure, and backup retention before real-data use.
9. The API has developer OpenAPI endpoints. Restrict documentation in public deployments as appropriate. Disable access logging of invitation/reset tokens and never log provider secrets or receipt contents.
10. No commercial service-level, tax, licensing, or compliance assurance is claimed. The code contains a disabled Xendit hosted-subscription path for PHP 99/149 household plans and a first-enrollment trial. It stores no card, bank, or wallet credentials; it has no live merchant configuration, commercial terms, charge, refund, or provider validation. Bank access remains unimplemented.

## Deployment checklist

- Run the real Next.js typecheck, production build, dependency audit, and supplied E2E tests on your development machine; these could not be completed in the authoring environment.
- Review dependencies and lockfiles. Review generated code and permission boundaries independently.
- Remove demo users and sample data. Use separate production secrets and an isolated database.
- Deploy behind HTTPS, set `SECURE_COOKIES=true`, set `APP_URL` to the actual origin, restrict `ALLOWED_ORIGINS`, and configure trusted proxies deliberately.
- Add a reviewed Content Security Policy compatible with the built Next application. Frame protection is present, but a complete CSP has not been deployed in this local build.
- Add malware scanning, file quotas, cost limits for OCR, failed-job administration, monitoring, and a durable production worker.
- Document the purpose and legal basis for processing receipts. Obtain appropriate notices/consent and provider agreements. Avoid collecting passport numbers, medical details, school identifiers, or full account numbers unnecessarily.
- Review accessibility and readability; the UI has keyboard dialogs and labels but no formal WCAG conformance assessment.
- Back up and restore both the database and uploads consistently. Do not copy a live SQLite file without SQLite backup tooling or stopping writes.
- Test receipt extraction on representative documents and real SMTP delivery on your provider; mocked tests do not establish either.
- Implement financial-provider confirmation only with documented authorization, supported accounts, idempotent webhook handling, signatures, reversal handling, timestamps, and auditability.

## Safe backup of the local pilot

Stop the launcher before copying `backend/data/` or `backend/demo-data/`, including the database and uploads directory. Use device encryption and restricted access. Restore to a separate environment and test sign-in, record totals, and file downloads before trusting a backup. Container users must back up the named volume through an appropriate stopped-service or database-aware workflow. Never delete or replace the previous starter database with this application's schema.
