# Padala — product and implementation requirements

**Baseline: November 3, 2026.** This brief restates the owner's requested product and adds explicitly labeled engineering requirements for continuing the existing code. The implementation status is separately maintained in `handoff/CURRENT_STATUS.md`.

## 1. Product goal

Give an overseas Filipino worker and their adult family members a shared, per-remittance record of the allocation plan, submitted supporting evidence, review decisions, and outstanding explanations.

Core journey:

**Record remittance → allocate → acknowledge receipt of funds → submit supporting evidence → run available checks → notify OFW → review/clarify → compile history and reports.**

The owner's long-term aspiration includes automatic authentication of evidence. The implementable promise must remain narrower: extraction and consistency checks now; independent confirmation only for supported transactions through an authorized provider integration. A receipt photograph alone is not conclusive verification.

## 2. Users and current access model

- **Sender / OFW:** creates the household and remittances, assigns allocations, invites family, reviews evidence, and reads reports.
- **Member:** joins by invitation, acknowledges a remittance when designated recipient, submits evidence to assigned allocations, and responds to clarification.
- **Local operator:** uses CLI administration for setup/password recovery. There is no administrator web console.

Current scope: one household per user; submitted household records are visible to active members. Draft uploads are private to their uploader. A sender can revoke and later restore a member's access; revocation signs the member out and blocks future assignments but preserves shared history. Private per-person ledgers, shared-record erasure, several households under one account, and child accounts are not implemented. Do not promise these as existing features.

## 3. Functional requirements

“Preserve” means current source contains the feature. “Future” means work still needs design and implementation.

| ID | Requirement | Scope/status |
|---|---|---|
| AUTH-01 | Household registration, password sign-in/out, revocable sessions and CSRF protection | Preserve |
| AUTH-02 | Single-use, email-bound member invitations and role checks | Preserve; email identity itself is not independently verified |
| AUTH-03 | Password change and SMTP reset flow; local CLI recovery without SMTP | Preserve; live mail needs validation |
| AUTH-04 | Production verified-email gate with expiring, one-time link and privacy-preserving resend response | Implemented; real SMTP delivery still needs validation |
| AUTH-05 | Sender-controlled member access revocation/restoration with session invalidation | Implemented; preserves shared history and is not deletion/export |
| PAD-01 | A separate record for each remittance, with title, amount received in PHP, date and recipient | Preserve |
| PAD-02 | Optional original currency/amount metadata; no assumed exchange-rate conversion | Preserve |
| PAD-03 | Recipient acknowledgment distinct from paying an obligation | Preserve |
| ALC-01 | Rent, groceries, school, utilities, savings and custom names; expense/savings kinds | Preserve |
| ALC-02 | Exact allocation total equals remittance; assignees belong to the household | Preserve |
| ALC-03 | Reallocation, partial-refund adjustments and carry-forward with history | Future; do not overwrite original plan silently |
| EVD-01 | Upload JPEG, PNG, WebP or PDF up to the configured 5 MB limit | Preserve; HEIC conversion not implemented |
| EVD-02 | Record merchant/payee, amount, date, reference, explanation and allocation splits | Preserve |
| EVD-03 | Split one receipt across distinct allocations within the same remittance, with an exact total | Preserve |
| EVD-04 | Permit explained purchases without a receipt and label them accordingly | Preserve |
| CHK-01 | Detect identical submitted file bytes; flag reference reuse, unusual dates and amounts | Preserve; edited duplicates can evade exact hashes |
| CHK-02 | Optional Azure field extraction after explicit uploader consent; manual fallback | Adapter exists; live validation outstanding |
| CHK-03 | Preserve independent provider confirmation as `not_connected` | Preserve until an authorized integration passes its acceptance gate |
| RVW-01 | OFW accepts or requests clarification; uploader responds; optimistic versions prevent stale changes | Preserve |
| RVW-02 | Void with reason and history, exclude from totals | Preserve; not a full refund/correction ledger |
| NTF-01 | Persist household event notifications; poll while interface is open | Preserve |
| NTF-02 | Optional SMTP notifications/invitation/reset email with bounded retry | Adapter exists; live validation outstanding |
| NTF-03 | Background push or SMS | Future; no provider selected |
| REP-01 | Remittance history, receipt listing, CSV summary and JSON metadata export | Preserve |
| REP-02 | Full user export including original files, deletion/retention and privacy erasure | Future; required design before a broader real-data pilot |
| MOB-01 | Responsive desktop/mobile web and included PWA shell | Preserve; verify actual Next build and physical devices |
| MOB-02 | Native Android/iOS binaries and store publication | Future, not required for the first milestone |
| SAV-01 | Separate recorded savings contributions from household spending | Preserve |
| SAV-02 | Live savings balance and subsequent withdrawals/reversals | Future; requires consented provider access and timestamped reporting |

## 4. Money and accounting rules

Use positive integer minor units. **PHP 30,000 = 3,000,000 centavos.** Reject floating-point API money inputs, negative amounts, zero allocations, and totals that do not match.

A reference acceptance plan:

| Allocation | PHP | Integer centavos | Kind |
|---|---:|---:|---|
| Rent | 10,000 | 1,000,000 | expense |
| Groceries | 7,000 | 700,000 | expense |
| School | 5,000 | 500,000 | expense |
| Utilities | 3,000 | 300,000 | expense |
| Savings | 5,000 | 500,000 | savings |
| Total | 30,000 | 3,000,000 | |

Track submitted and accepted records distinctly. A receipt's evidence lines must not multiply its financial amount. An uploaded draft does not count as expenditure. Voiding removes a record from current totals while preserving its history and file association.

Savings contributions are not purchases and are not a current account balance. The original remittance source amount may not imply any particular exchange rate.

Allocations organize records; they do not create segregated bank balances. Matching a receipt to a remittance is household attribution, not tracing individual pesos after money is mixed. “Unaccounted for” must not be described as “misused.”

## 5. Evidence and review vocabulary

| Label | Allowed meaning |
|---|---|
| Submitted / pending | A file or explanation was supplied |
| Checks completed / needs clarification | Specific metadata/file checks have run; do not imply authenticity |
| OFW accepted | A household review decision |
| Provider: not connected | No independent transaction source is available |
| Provider-confirmed, future | Only after a trusted server-side match with source/status/timestamp and supported scope |

Existing review states: `pending`, `clarification`, `accepted`, `voided`. Preserve these existing API values unless a selected change includes a migration and compatibility plan.

Extraction confidence measures extracted fields, not authenticity. A genuine deposit record does not establish that the deposit remains saved. Avoid “fraud detected” conclusions based on file appearance or missing data.

## 6. Nonfunctional requirements

- **Authorization:** every household-owned identifier and file must be checked server-side. UI hiding is not authorization.
- **Security:** preserve HTTP-only cookies, origin/CSRF checks, upload controls, password hashing, token expiry, and safe exports. Never accept a client-supplied verification flag.
- **Privacy:** collect only necessary evidence, explain external extraction, minimize notifications, and design retention/deletion before real-data rollout. This brief is not a legal-compliance certification.
- **Reliability:** use transactions for related writes, optimistic concurrency for reviews, and readable error states. Preserve histories when records are changed through supported workflows.
- **Mobile usability:** no horizontal scrolling at 360px for normal screens; readable inputs; accessible labels, keyboard dialog handling, and clear retry paths.
- **Accessibility:** test keyboard flow, focus, validation messages, and contrast; no conformance claim until audited.
- **Performance:** first measure using representative fictional workloads; no capacity or latency guarantee is established by this handoff.
- **Data safety:** local database/files are not application-encrypted. Back up both consistently and test restoration. Do not treat JSON metadata export as a full backup.
- **Offline behavior:** no caching of private financial responses or receipts without a separate security design. The included service worker does not provide an offline ledger.

## 7. Technical baseline

Frontend: Next.js App Router, TypeScript, React, native fetch, responsive CSS. Backend: Python FastAPI, Pydantic, SQLAlchemy, Alembic. Database: SQLite for the local milestone. Provider adapter: Azure Document Intelligence for extraction only. Email: optional SMTP outbox.

Runtime prerequisites are Python 3.11+ and Node 22+ as declared by the project. Exact package declarations live in `frontend/package.json`, `backend/requirements.txt`, and `backend/requirements-dev.txt`. The frontend has no supplied lockfile; validate dependency resolution before relying on it.

Architecture and API references: `handoff/ARCHITECTURE_AND_API.md`, `docs/API-GUIDE.md`, and `docs/openapi.json`.

## 8. Non-goals and decisions still needed

Not in the first task: holding or moving money, automatic bank-account access, biometric identity verification, lending, guarantees about family behavior, or native app-store distribution.

The owner must select and approve any bank/payment integration, real hosting, paid provider usage, billing provider, data-retention policy, and broader privacy/access design. No provider contract, legal approval, production budget, or credential is included.

Xendit has been selected for the proposed monthly household subscription. The
owner selected Padala Basic at PHP 99/month for up to four active household
members and Padala Family at PHP 149/month for up to eight, with one free month
for a household's first completed enrollment. The code has a disabled-by-default
hosted-checkout, signed-webhook, cancellation, and entitlement path; it does not
contain tax treatment, business identity, refund policy, live Xendit account, or
live provider validation. Do not set `BILLING_ENABLED=true` or represent the
plan as available until those release checks are complete.

The first definition of done is in `handoff/ACCEPTANCE_TESTS.md`: a real local Next/Python build and two-account workflow with truthful evidence labels. Production readiness is a separate milestone.
