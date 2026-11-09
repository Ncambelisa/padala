import { connection } from 'next/server';
import type { Config, PrivacyNotice } from '@/lib/types';

function NoticeUnavailable() {
  return <main className="privacy-page"><a className="privacy-back" href="/">← Back to Padala</a><article className="privacy-card"><p className="privacy-kicker">PADALA PRIVACY</p><h1>Privacy notice not yet published</h1><p>This environment is for development or internal testing. The service operator must publish the controller identity, privacy contact, lawful basis, retention schedule, and processor list before collecting real household information.</p></article></main>;
}

function PublishedNotice({ notice }: { notice: PrivacyNotice }) {
  return <main className="privacy-page"><a className="privacy-back" href="/">← Back to Padala</a><article className="privacy-card"><header className="privacy-header"><p className="privacy-kicker">PADALA PRIVACY NOTICE</p><h1>How Padala handles household information</h1><p>Effective {notice.effective_date} · Version {notice.version}</p></header>

    <section><h2>Who is responsible</h2><p><strong>{notice.controller_name}</strong> controls the personal information processed through this Padala deployment.</p><address>{notice.controller_address}</address><p>For privacy questions or requests, email <a href={`mailto:${notice.contact_email}`}>{notice.contact_email}</a>.</p></section>

    <section><h2>What this service does</h2><p>Padala is a shared household allocation-and-evidence record. It helps adult household members record remittance plans, receipt files or written explanations, and reviews. It does not send or hold money, connect to a bank or remittance provider, authenticate receipts, or show a live savings-account balance.</p></section>

    <section><h2>Information we process</h2><ul><li>Account and household information: name, email address, encrypted-password hash, role, household name, verified-email status, notification preference, and account/session security records.</li><li>Household record information: remittance titles, amounts, dates, allocations, assigned household members, recipient acknowledgement, evidence status, review notes, activity history, and notifications.</li><li>Evidence information: merchant or payee, transaction date, amount, optional reference and notes, and a receipt or payment-record file if you choose to upload one. The service stores the file name, type, size, and a cryptographic file hash with the original file.</li><li>Technical and security information needed to operate and protect the service, such as rate-limit and session data, request-origin checks, and security/audit events.</li></ul><p>Do not upload passport or government ID images, medical records, school identifiers, full bank-account or card numbers, passwords, or other information that is not needed for a household record.</p></section>

    <section><h2>Why we process it</h2><p>{notice.legal_basis_summary}</p><p>We use the information to create accounts, provide shared household records, protect accounts and files, send account and optional update emails, respond to support or rights requests, and meet applicable legal obligations. Padala does not use this information for targeted advertising or automated decisions that produce legal or similarly significant effects.</p></section>

    <section><h2>Who can see it</h2><p>Submitted records, attached receipt files, and the member directory are visible to members of the same household. An unsubmitted upload draft is visible only to its uploader. Do not invite anyone unless you are comfortable sharing submitted household records with that person. This version does not provide private sub-ledgers, granular sharing controls, or a member-removal screen.</p><p>We also use service providers to operate the deployment. The current processor and transfer information for this deployment is: {notice.processors_summary}</p><p>If optional Azure receipt text extraction is enabled, the uploader must actively select it before that draft file is sent to Azure. Extraction suggests fields only; it does not verify the transaction or authenticate the receipt.</p></section>

    <section><h2>Security and retention</h2><p>Padala uses account, session, access-control, request-origin, upload-size, private-download, and activity-record safeguards. Production uploads are configured to be malware-scanned before storage. No security measure can eliminate every risk, so keep your password and invitations private and use only trusted devices and networks.</p><p>{notice.retention_summary}</p><p>The product currently offers household CSV/JSON metadata exports to signed-in users. It does not yet provide self-service account deletion or a complete binary-file export. To request access, correction, deletion, restriction, or another privacy action, contact the privacy email above. Requests may require identity verification and review of the shared-household impact.</p></section>

    <section><h2>Your choices and rights</h2><p>Subject to applicable law, you may ask to be informed about processing, access and correct your personal information, object or withdraw consent where consent is the basis, request erasure or blocking where applicable, seek data portability, and raise a concern. You may also contact the Philippine National Privacy Commission. Its guidance on data-subject rights and privacy notices is available at <a href="https://privacy.gov.ph/the-right-to-be-informed/" target="_blank" rel="noreferrer">privacy.gov.ph</a>.</p></section>

    <section><h2>Security incidents and changes</h2><p>We assess suspected security incidents and will provide notices where required by applicable law. The National Privacy Commission describes notification requirements for qualifying personal-data breaches, including circumstances that require timely notice to the Commission and affected people. See its <a href="https://privacy.gov.ph/pips-and-pics/breach-reporting/" target="_blank" rel="noreferrer">breach-reporting guidance</a>.</p><p>We may update this notice when the service or processing changes. The effective date and version above identify the current notice. For material changes, we will provide notice before or when the change takes effect, as applicable.</p></section>
  </article></main>;
}

export default async function PrivacyPage() {
  // Keep the notice dynamic: it is deployment configuration, not a build-time
  // placeholder. This also lets the page render without browser JavaScript.
  await connection();
  const apiOrigin = (process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
  let notice: PrivacyNotice | null = null;
  try {
    const response = await fetch(`${apiOrigin}/api/v1/config`, { cache: 'no-store' });
    if (response.ok) notice = (await response.json() as Config).privacy_notice || null;
  } catch {
    notice = null;
  }
  if (!notice?.published) return <NoticeUnavailable />;
  return <PublishedNotice notice={notice} />;
}
