import { connection } from 'next/server';
import type { Config, Billing } from '@/lib/types';

function Unavailable() {
  return <main className="privacy-page"><a className="privacy-back" href="/">← Back to Padala</a><article className="privacy-card"><p className="privacy-kicker">PADALA SUBSCRIPTION</p><h1>Subscription terms not yet published</h1><p>This environment is not accepting subscription payments. The operator must publish the plan price, cancellation, refund, tax, and support terms before enabling checkout.</p></article></main>;
}

function PublishedTerms({ billing }: { billing: Billing }) {
  return <main className="privacy-page"><a className="privacy-back" href="/">← Back to Padala</a><article className="privacy-card"><header className="privacy-header"><p className="privacy-kicker">PADALA SUBSCRIPTION TERMS</p><h1>Household subscription, cancellation, and refund terms</h1><p>Effective {billing.terms.effective_date} · Version {billing.terms.version}</p></header>
    <section><h2>Plans and billing</h2><ul>{billing.plans.map(plan=>{const price=new Intl.NumberFormat('en-PH',{style:'currency',currency:'PHP',minimumFractionDigits:2}).format(plan.amount_minor/100);return <li key={plan.code}><strong>{plan.name}</strong>: {price} per month, for up to {plan.max_members} active household members. {plan.description}</li>;})}</ul><p>Billing is recurring until it is cancelled in accordance with the terms below. Xendit’s hosted checkout identifies the selected plan and final charged amount before you authorize it.</p></section>
    <section><h2>One-month free trial</h2><p>A household’s first completed subscription enrollment includes one month free. Xendit securely collects the recurring payment method at signup, but Padala schedules the first charge after the trial end shown before authorization. A household that has already started its trial does not receive another free trial when it re-enrolls.</p></section>
    <section><h2>Payment provider</h2><p>Payment details are collected and stored by Xendit through its hosted checkout. Padala does not collect or store card, e-wallet, or bank-account credentials. A browser return from checkout is not payment confirmation; Padala updates subscription access only after a signed provider webhook confirms the relevant subscription event.</p></section>
    <section><h2>Cancellation</h2><p>{billing.terms.cancellation_summary}</p><p>The household owner can request cancellation from Padala’s Billing screen. Cancel before the displayed trial-end date to avoid the first scheduled charge. The request stops future subscription cycles once Xendit confirms it, and access ends when that confirmation is received. Keep a copy of the confirmation and contact support if the status remains pending.</p></section>
    <section><h2>Refunds</h2><p>{billing.terms.refund_summary}</p></section>
    <section><h2>Taxes and receipts</h2><p>{billing.terms.tax_summary}</p></section>
    <section><h2>Support</h2><p>For billing questions, cancellation assistance, or a refund request, email <a href={`mailto:${billing.terms.support_email}`}>{billing.terms.support_email}</a>. For privacy information, read the <a href="/privacy">Privacy Notice</a>.</p></section>
  </article></main>;
}

export default async function TermsPage() {
  await connection();
  const apiOrigin = (process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
  let billing: Billing | null = null;
  try {
    const response = await fetch(`${apiOrigin}/api/v1/config`, { cache: 'no-store' });
    if (response.ok) billing = (await response.json() as Config).billing || null;
  } catch {
    billing = null;
  }
  if (!billing?.terms.published || !billing.checkout_available) return <Unavailable />;
  return <PublishedTerms billing={billing} />;
}
