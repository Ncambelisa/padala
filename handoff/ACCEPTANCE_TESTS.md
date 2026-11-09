# Acceptance checklist

Use fictional data in a separate development database. Record exact results in `LOCAL_VALIDATION_RESULTS.md`; this checklist is not itself a test result.

## Gate A — reproducible local software

| ID | Action | Expected result |
|---|---|---|
| A01 | Run preflight and inspect manifest versions | Compatible Python/Node; clear missing-tool/port diagnostics |
| A02 | Install dependencies normally | Successful installation; genuine npm lockfile; no bypassed peer/security checks |
| A03 | Run backend pytest | Baseline cases pass; new fixes have regressions |
| A04 | Run `npm run typecheck` and `npm run build` | Actual dependency-aware checks pass; no harness substitution |
| A05 | Start production frontend plus API locally | Page loads and routes through Next to Python |
| A06 | Run `npm audit` | Findings recorded and triaged; do not assume zero vulnerabilities |
| A07 | Run real-server Playwright | Desktop and mobile-emulation scenarios pass |

## Gate B — full two-person acceptance story

Use the fictional demo for exploratory testing, then a new test household for a clean proof of the following flow.

1. Create a sender household. Invite a distinct member. Accept the invitation in a separate browser context. Verify that an expired/used invitation cannot be reused.
2. As sender, create a **PHP 30,000 / 3,000,000-centavo** remittance. Allocate Rent 10,000, Groceries 7,000, School 5,000, Utilities 3,000, Savings 5,000 to the invited member. Confirm the total is exact.
3. As the designated member, acknowledge receipt. As a different unauthorized member/context, verify the acknowledgment is denied where applicable.
4. Upload a synthetic grocery receipt for PHP 2,000. Confirm the fields manually, submit to Groceries, and verify the assigned remittance retains the record after refresh.
5. As sender, see an in-app notification. Open the record, request clarification and supply a reason. As uploader, respond. As sender, accept the updated record using the current version.
6. Verify the UI distinguishes OFW acceptance from independent confirmation. The provider label remains **not connected**.
7. Submit a synthetic PHP 5,000 savings deposit record. It appears as a recorded contribution, not a confirmed live balance.
8. Create another remittance. Verify each record remains attributable to its own remittance and no expense is silently duplicated across cycles.
9. Export CSV and JSON. Confirm totals, status/history and separation of savings. The export does not expose another household or session secrets; JSON does not claim to contain the uploaded binaries.
10. Sign out, close/reopen browser sessions, sign back in and verify persistence. Restart local servers without clearing the database and confirm records remain.

## Gate C — money, files and permissions

| ID | Test | Expected result |
|---|---|---|
| C01 | Submit allocations off by one centavo | Validation error; no partially created remittance |
| C02 | Submit float, negative/zero or invalid money | Rejected according to the defined schema |
| C03 | Submit receipt splits that do not total the receipt | Rejected |
| C04 | Include another remittance's allocation in a receipt | Rejected |
| C05 | Member targets an allocation not assigned to them | Permission denied |
| C06 | Upload the exact same file and attempt a second expense | Existing draft returned or duplicate submission prevented as appropriate |
| C07 | Submit a reused reference or over-allocation | Clear clarification/check flag, not an unsupported fraud verdict |
| C08 | Submit unsupported/empty/oversized file | Clear rejection; no arbitrary code execution or public file exposure |
| C09 | Submit a no-receipt record without required explanation | Validation error; with explanation it stays a declaration |
| C10 | Use a different household's record/file ID | Denied without data leakage |
| C11 | Omit CSRF or use an unapproved origin on writes | Denied; reads do not bypass record permissions |
| C12 | Review with stale `expected_version` | HTTP 409; refresh instead of silent overwrite |
| C13 | Attempt client-supplied `provider_confirmation` or similar flag | Unknown/untrusted property rejected; no fake confirmation |
| C14 | Void with a reason | Removed from active totals, retained in history, not counted again as a new purchase |
| C15 | Export malicious-looking merchant text such as a spreadsheet formula | Safe export behavior, no formula execution from unescaped text |

The backend already has relevant coverage for many cases. Expand through actual browser flows where needed; do not assume the frontend is covered by API tests.

## Gate D — optional services

- Unconfigured Azure: manual entry remains available; extraction is explicitly unavailable.
- Mock Azure: exercise submit/poll/success/failure and foreign polling-origin rejection; confirm no credential leak.
- Approved live Azure: use a synthetic sample; review output, costs and failure behavior. Keep provider confirmation unchanged.
- Unconfigured SMTP: no false “delivered” claim. Manual invitation-copy/local password recovery remains documented.
- Mailpit test: invitation/reset emails can be read locally, not described as internet delivery.
- Approved live SMTP: verify expiry, delivery, reset/session revocation, opt-in updates and secret redaction.

## Gate E — web/mobile and recovery

Check 360, 390, 768 and 1440px widths, then actual target devices when available. Forms/dialogs must fit, inputs have labels, keyboard focus must be usable, and error states must explain the next action. Mobile emulation does not prove physical installation or camera behavior.

Verify refresh/sign-out does not expose a previous user's household. Test unavailable backend and failed upload behavior without accidentally counting a draft as a payment. Review service-worker behavior: private records and receipt files must not be cached for offline access without an approved design.

Stop writes, back up database and uploads together, restore into an isolated location, then test sign-in, exact totals and file downloads. Do not test restoration by overwriting the only copy of family data.

## Gates explicitly outside the local milestone

No production certification, real bank coverage, live balance guarantee, actual money transfer, subscription charging, native-app release, or legal/privacy compliance claim follows from these tests. Those need the separate implementation/review gates in `IMPLEMENTATION_PLAN.md`.
