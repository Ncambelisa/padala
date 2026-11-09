# Current status and known gaps

**As packaged: November 3, 2026.** Separate source presence, automated tests, and real-provider validation. This handoff adds instructions and diagnostics, not new financial capabilities.

## Evidence used

The supplied `Padala-NextJS-Python.zip` was inspected, including its manifests, API, schemas, services, launcher, tests, and documentation. Existing application files are preserved byte-for-byte. The Python suite was rerun during packaging: **59 passed** on Python 3.13.5. See `PACKAGING_REPORT.md` for the current run and `../docs/TEST-REPORT.md` for the historical build report.

## Present in the source

| Area | Current implementation | Validation boundary |
|---|---|---|
| Accounts | Registration, privacy-notice acknowledgement/version gate, production verified-email gate, login/logout, sessions, password changes, invitations, reset flow | Backend tests; no independent security audit or live-mail validation |
| Authorization | One household per account, sender/member roles, assigned allocations, sender-controlled access revocation/restoration | Backend isolation and access-lifecycle tests; test real proxy/cookies locally |
| Remittances | Exact integer-money allocations and recipient acknowledgment | Backend tests |
| Evidence | Private drafts, protected downloads, receipt splits, explanatory declarations | Backend tests; physical-phone camera/HEIC not validated |
| Checks | Exact-byte duplicates, references, dates, overrun and extraction mismatch flags | Not an authenticity service |
| Reviews | Pending/accepted/clarification, responses, version checks, void history | Backend tests |
| Notifications | Database records and frontend polling; optional SMTP outbox | SMTP adapter mocked, not live-validated |
| Reports | CSV/JSON metadata and activity | Not a full binary-file backup or data-subject export |
| Extraction | Azure submit/poll/normalize REST adapter | Mocked contract tests, no current live credentials |
| Frontend | Next/React/TypeScript source, responsive styles, browser test files, PWA assets | Local typecheck, production build, and browser tests passed; physical-device validation remains outstanding |
| Billing | Disabled Xendit hosted checkout for PHP 99/149 household plans, one-month first-enrollment trial, signed callbacks, cancellation request path, webhook idempotency ledger, paid-access gate, member limits, and public `/terms` shell | Unit/integration tests with a mocked provider response only; no Xendit account, credentials, callback, charge, fee, customer, or live provider validation |
| Local deployment | Launcher, Dockerfiles, Compose, Alembic | Local production-path validation passed; hosting/platform and Docker validation remain outstanding |

## Not implemented

Independent bank/merchant receipt authentication; payment initiation/custody; live savings balances; approved reallocation; carry-forward; automatic refund/reversal adjustments; background push/SMS; private member sub-ledgers; several households per account; full account deletion/export; native Android/iOS binaries; import from the previous HTML/Python starter database.

Subscription **billing operations are not live**: the selected Xendit code is
disabled by default. The owner selected PHP 99/149 plans and a one-month first
enrollment trial, but commercial terms, tax treatment, business identity,
merchant account, and provider validation are incomplete. Invoices, tax
documents, refund execution, chargeback handling, reconciliation operations,
and customer support operations are outside the current implementation.

Provider confirmation deliberately remains `not_connected`. Adding a green badge is not implementation of a provider integration.

## Important gaps to address

1. **External providers:** Azure and SMTP have code and mocks, not working account credentials or demonstrated live success.
2. **File safety:** PDF signature checks are not malware scanning. HEIC is unsupported. Exact hashes do not identify every edited/rephotographed duplicate.
3. **Privacy/access:** the production notice requires controller, contact, lawful-basis, retention, and processor fields and records version acknowledgement. A sender can revoke or restore household access without erasing shared history, but the owner still needs an approved deletion, retention, and privacy-erasure process. Submitted household records remain broadly shared within that household; there are no granular private ledgers. Public registration also lacks bot controls.
4. **Operations:** PostgreSQL/Redis/ClamAV/SMTP, monitoring, backups/restore testing, on-call ownership, independent security review, and a public HTTPS Xendit callback route remain unconfigured or unvalidated for production.
5. **Mobile:** responsive web/PWA files exist; no native application and no physical-device installation test. Offline private-data sync is not implemented.
6. **Accounting:** voiding is not a complete correction ledger. Refunds, reallocation, carry-forward and savings withdrawals need a designed model before implementation.

## Reporting rule

Use “source present,” “test passed,” “blocked,” “not run,” or “not implemented” precisely. A successful backend regression does not establish frontend production compatibility. A mocked API test does not establish provider availability. Local success does not establish regulatory or security certification.
