# Padala privacy notice for a closed pilot

**Status:** complete the owner fields below and obtain Philippines privacy/legal
review before publishing this notice or collecting real household data.

**Public location:** the application serves the approved notice at `/privacy`.
In production, the API refuses to start while any required `PRIVACY_*`
configuration is blank. The values are public notice content, not secrets.
The app records the version a new registrant or invited member acknowledges. If
the published version changes, existing users must acknowledge the new version
before household records are shown.

## Controller and contact

- **Selected personal information controller:** Nico Cambelisa
- **Production configuration field:** `PRIVACY_CONTROLLER_NAME=Nico Cambelisa`
- **Business address:** `PRIVACY_CONTROLLER_ADDRESS`
- **Privacy contact:** `PRIVACY_CONTACT_EMAIL`
- **Notice version:** `PRIVACY_NOTICE_VERSION`
- **Effective date:** `PRIVACY_NOTICE_EFFECTIVE_DATE`

Confirm the final legal form or registered business name before launch. The
public notice will use the deployment configuration, not this draft alone.

## Scope

Padala is a shared household allocation-and-evidence record. It is not a bank,
wallet, payment, remittance, receipt-authentication, or savings-account
service. It does not hold or transfer money, connect to a financial provider,
or show a live savings balance.

The notice covers adult members of an invited household pilot. Do not market it
as a public financial service or permit children to register until the product,
support, and legal design have been expanded and reviewed.

## Information processed

The service processes:

- account information: name, email address, password hash, household role and
  access state, email-verification state, notification preference,
  session/security data;
- shared-household information: household name, remittance plan, PHP amounts,
  dates, allocations, member assignment, recipient acknowledgement, reviews,
  notifications, and activity history;
- evidence information: merchant or payee, date, amount, optional reference and
  explanation, and an optional receipt/payment-record file with its name, type,
  size, and SHA-256 file hash; and
- operational/security records needed to maintain the service and investigate a
  suspected misuse or incident.

Users must not upload passwords, full bank or card numbers, government-ID or
passport images, health/medical records, school identifiers, or other sensitive
information that is not necessary for the stated household record.

## Purpose and legal basis

Set `PRIVACY_LEGAL_BASIS_SUMMARY` to the written, reviewed basis for this exact
deployment. It must say how processing is lawful for account creation, shared
household records, security, support, email, and any optional provider. Do not
use a vague statement such as “by using the app you consent.”

The published notice also states that Padala does not use data for targeted
advertising or automated decisions that create legal or similarly significant
effects.

The Philippine National Privacy Commission describes the applicable principles
as transparency, legitimate purpose, and proportionality, and says the privacy
notice should explain the controller, processing, purposes, recipients, and
data-subject rights. [NPC Data Privacy Act IRR](https://privacy.gov.ph/implementing-rules-regulations-data-privacy-act-2012/)

## Household sharing and service providers

Submitted evidence, its attachment, and the member directory are visible to
people with active access in the same household. Unsubmitted upload drafts are
visible only to the uploader. The household owner can remove a member's access,
which immediately signs that person out and prevents future assignments. It does
not erase that person's existing assignments, submitted records, or activity
history from the shared household record. This build has no private sub-ledgers
or granular sharing controls. A household owner must share these limits before
inviting a member.

Set `PRIVACY_PROCESSORS_SUMMARY` to the named current hosting, database,
backup, email, malware-scanning, and optional document-extraction providers.
For each one, include the service purpose, processing location, and any
cross-border transfer safeguard relevant to the deployment. Update the public
notice before adding or replacing a provider.

Optional Azure Document Intelligence extraction is separate: the uploader must
choose it for a specific draft before bytes are sent to Azure. It returns field
suggestions only and never authenticates a receipt or transaction.

## Security and retention

The code includes password hashing, HTTP-only sessions, CSRF and origin checks,
household authorization, upload bounds/type checks, private file downloads, and
activity records. Production mode also requires email verification and a
malware scanner before an upload is stored. These controls do not make a file
or transaction authentic, and they do not remove all security risk.

Set `PRIVACY_RETENTION_SUMMARY` to the approved schedule for active records,
access revocation, account closure, legal/dispute holds, backups, and pilot
closure. The current product does not provide self-service account deletion or
a complete export of uploaded files. The operating team must have a manual
rights-request and deletion process before real data is accepted.

## Rights, incidents, and changes

Subject to applicable law, users may request information about processing,
access or correction, object or withdraw consent where consent is the basis,
request erasure/blocking where applicable, seek portability, or raise a
concern. Requests go to `PRIVACY_CONTACT_EMAIL` and may require reasonable
identity verification and a review of the shared-household effect.

For a qualifying personal-data breach, the operator must follow the applicable
notification process. The NPC says notification can be required within 72 hours
of knowledge or reasonable belief of a breach in the circumstances described by
the law. [NPC breach-reporting guidance](https://privacy.gov.ph/pips-and-pics/breach-reporting/)

Update the notice version and effective date before materially changing the
processing described here. Give affected users notice as required by the
approved policy and applicable law.

## Before a pilot can use real data

1. Replace every example `PRIVACY_*` value in the production secret manager.
2. Have a qualified Philippines privacy/legal reviewer approve the controller,
   legal basis, retention/deletion process, processor list, and rights-request
   process.
3. Start a test production configuration and visit `/privacy` from a signed-out
   browser to confirm all business details appear correctly.
4. Set a written incident owner and a monitored privacy mailbox before inviting
   any real household.
