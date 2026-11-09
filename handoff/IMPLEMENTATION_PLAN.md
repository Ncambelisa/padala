# Implementation plan for local Codex

This backlog is newly organized from the existing code's disclosed gaps. It is not evidence that the features below are already implemented. Complete the first milestone before selecting further development.

## Milestone 1 — real local build and two-account workflow

| ID | Task | Completion evidence |
|---|---|---|
| LOCAL-01 | Inspect repo, preflight, manifests and current state; preserve user files | Version inventory and focused plan |
| LOCAL-02 | Verify compatible published dependency versions; install in local environments | Successful install, real npm lockfile, rationale for version changes |
| LOCAL-03 | Run backend regressions and fix genuine defects | Passing suite and added tests for fixes |
| LOCAL-04 | Run full TypeScript typecheck and real Next build; repair compatibility issues | Exact commands and successful build output |
| LOCAL-05 | Validate actual Next proxy, session cookies and CSRF | Signed-in two-role flow, protected writes/downloads |
| LOCAL-06 | Run supplied Playwright tests and add full separate-user scenario | Green real-server E2E, negative access tests |
| LOCAL-07 | Check mobile widths, dialogs, loading/errors and keyboard access | Documented observations; clearly labeled screenshots |
| LOCAL-08 | Record all results, remaining warnings and start/stop steps | `handoff/LOCAL_VALIDATION_RESULTS.md` |

Do not use a stub backend, fake providers or a different React runtime to declare this milestone passed. Network/provider blockers should be logged honestly. Dependencies need review, not forced installation at any cost.

## Milestone 2 — reliable optional services and usability

Proceed after milestone 1; obtain approval for real service calls.

| ID | Task | Completion evidence |
|---|---|---|
| SVC-01 | Harden extraction failure handling and manual correction; test current adapter live only with permission | Synthetic-document result, timeout/rejection paths, no false confirmation |
| SVC-02 | Test SMTP locally, then approved real delivery/reset/invitation flows | Delivery results, token expiry, opt-in behavior, redacted logs |
| SVC-03 | Validate photo uploads on actual target phones and HTTPS PWA behavior | Device/browser versions and reproducible results |
| SVC-04 | Add appropriate retry/error UI and test controls for failed jobs | No duplicate spending records, bounded retries, clear state |
| SVC-05 | Run accessibility review and fix barriers | Keyboard/focus/labels/contrast findings and fixes |

Native binaries, background push and offline private-data synchronization require separate selected tasks; do not smuggle them into a PWA test.

## Milestone 3 — proposed accounting and household changes

These require explicit product decisions and data migrations before coding.

- **LEDGER-01: Approved reallocation.** Record requested and approved moves, maintain allocation totals, require a reason, preserve previous versions, and handle evidence already assigned to an allocation.
- **LEDGER-02: Corrections/refunds.** Distinguish a mistaken document from a real refund/reversal. Define immutable adjustment links and tests; never erase the original event to make totals match.
- **LEDGER-03: Carry-forward.** Model unused allocations once, linking cycles without double-counting a new remittance.
- **ACCESS-01: Full member departure and privacy erasure.** Sender-controlled access revocation/restoration is implemented: it invalidates sessions and preserves shared history. Decide shared-record erasure, retention, data export, and any continuing responsibilities before treating departure as complete.
- **PRIVACY-01: Export/deletion/retention.** Cover original files, linked records and backups; preserve necessary shared records according to an approved policy.
- **ACCESS-02: Privacy/granular sharing.** Decide what members may see. Current broad household visibility must not be silently represented as selective sharing.

## Milestone 4 — independent provider confirmation

This is **blocked pending owner-selected provider, authorization, supported coverage and credentials**. Start by documenting the actual provider's API contract, not by inventing endpoints.

Implement server-side matching and a separate confirmation state, with source, provider reference, status and timestamps. Add authentication/signature controls as required, idempotency, replay resistance, mismatches, pending/failed/reversed cases, privacy controls and consent revocation. Do not call an unsupported screenshot confirmed.

A live savings balance is another capability requiring authorized up-to-date account data. It is not implied by a deposit match.

## Milestone 5 — commercial and production rollout

Xendit is selected and a disabled code path now covers hosted two-plan checkout,
signed callbacks, cancellation requests, one-time household trial entitlement,
and paid-access gating. Padala Basic is PHP 99/month for up to four active
household members; Padala Family is PHP 149/month for up to eight; a first
completed enrollment gets a one-month free trial. It remains a release gate, not
a live service. Before enabling it, complete a separate test-mode acceptance run
covering both plans, trial start/end, first paid cycle, cancellation,
failed/retried cycles, duplicate/out-of-order callbacks, refund/support handling,
and reconciliation. Finalize tax treatment, business identity/address, terms,
refund policy, support owner, Xendit merchant activation, eligible payment
channels, and public HTTPS callback routing. Then perform production
database/queue choice if justified, dependency/security reviews, HTTPS
deployment, observability, backups/restores, and device testing.

Do not collect payment card data in custom forms. The plan prices and trial are
owner decisions; tax treatment, jurisdictional compliance position, and launch
date are not finalized in this handoff.

## Result template for each task

Record: task ID; changed files; migrations/data impact; commands run; passed/failed/not-run results; screenshots or synthetic fixtures where useful; privacy/security implications; open blockers; owner decisions needed; next proposed task.

A blocked test is not a passed test. A documented future feature is not an implemented feature.
