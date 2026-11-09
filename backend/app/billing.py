"""Server-side Xendit Subscription helpers.

No payment details are accepted by Padala.  The browser is redirected to
Xendit's hosted checkout and the application relies on signed webhooks for the
subscription lifecycle.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException


XENDIT_API_VERSION = '2026-01-01'


def one_month_trial_end(now: datetime | None = None) -> datetime:
    """Return the first valid Xendit monthly anchor after one full month.

    Payment Sessions restrict subscription anchor dates to day 28 or earlier.
    For signups on the 29th–31st, the trial is extended to the first day of the
    following month instead of shortening the promised free month.
    """
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    month_index = started.month
    year = started.year + month_index // 12
    month = month_index % 12 + 1
    requested_day = started.day
    day = min(requested_day, calendar.monthrange(year, month)[1])
    if requested_day > 28:
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        return started.replace(year=year, month=month, day=1)
    return started.replace(year=year, month=month, day=day)


def subscription_has_access(subscription, now: int | None = None) -> bool:
    """Determine entitlement only from server-recorded subscription lifecycle.

    A Xendit plan activation starts the one-month trial but does not prove that
    its first scheduled charge succeeded. Once the trial end passes, a signed
    recurring-cycle success event is needed before the household remains open.
    """
    if subscription is None:
        return False
    if subscription.status == 'cancellation_pending':
        return True
    if subscription.status != 'active':
        return False
    if not subscription.trial_ends_at:
        return True  # Existing no-trial records remain compatible.
    if subscription.first_payment_confirmed_at:
        return True
    return subscription.trial_ends_at > (now if now is not None else int(datetime.now(timezone.utc).timestamp()))


def amount_for_xendit(amount_minor: int) -> int | float:
    """Convert Padala's integer centavos to an exact PHP API amount."""
    if amount_minor <= 0:
        raise ValueError('Subscription price must be positive.')
    pesos, centavos = divmod(amount_minor, 100)
    return pesos if centavos == 0 else float(Decimal(amount_minor) / Decimal(100))


def amount_minor_from_xendit(value: object) -> int:
    """Parse an Xendit PHP amount without using binary money arithmetic."""
    try:
        amount = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError('The provider amount is invalid.')
    if amount <= 0 or amount.as_tuple().exponent < -2:
        raise ValueError('The provider amount is invalid.')
    return int(amount * 100)


def hosted_checkout_url(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError('The provider did not return a checkout link.')
    parsed = urlsplit(value)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or not host or not (host == 'xen.to' or host == 'dev.xen.to' or host.endswith('.xendit.co')):
        raise ValueError('The provider returned an invalid checkout link.')
    return value


def subscription_payload(settings, subscription, user) -> dict:
    """Build the supported hosted Subscription Session request.

    Xendit's amount is expressed in PHP, while Padala stores the approved price
    in centavos.  The payment method is collected only by Xendit.
    """
    plan = settings.billing_plan(subscription.plan_code)
    if plan is None or plan['amount_minor'] != subscription.amount_minor:
        raise ValueError('The selected subscription plan is invalid.')
    trial_active = bool(subscription.trial_ends_at and not subscription.trial_started_at)
    anchor_at = datetime.fromtimestamp(subscription.trial_ends_at, timezone.utc) if trial_active else datetime.now(timezone.utc)
    anchor = anchor_at.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    customer_name = user.name.strip()[:120] or 'Padala customer'
    plan_name = str(plan['name'])
    return {
        'reference_id': subscription.provider_reference,
        'session_type': 'SUBSCRIPTION',
        'mode': 'PAYMENT_LINK',
        'amount': amount_for_xendit(subscription.amount_minor),
        'currency': 'PHP',
        'country': 'PH',
        'customer': {
            'reference_id': f'padala-user-{user.id}',
            'type': 'INDIVIDUAL',
            'email': user.email,
            'individual_detail': {'given_names': customer_name},
        },
        'locale': 'en',
        'description': f'{plan_name} monthly subscription',
        'items': [{
            'reference_id': f'padala-{subscription.plan_code}-monthly',
            'type': 'DIGITAL_SERVICE',
            'name': f'{plan_name} monthly subscription',
            'category': 'SOFTWARE',
            'net_unit_amount': amount_for_xendit(subscription.amount_minor),
            'quantity': 1,
            'currency': 'PHP',
        }],
        'subscription': {
            'schedule': {
                'interval': 'MONTH',
                'interval_count': 1,
                'anchor_date': anchor,
                'retry_interval': 'DAY',
                'retry_interval_count': 1,
                'total_retry': 3,
                'failed_attempt_notifications': [1, 2, 3],
            },
            # Xendit collects the recurring payment method at hosted checkout.
            # The first household enrollment defers its first charge to the
            # one-month trial end; a later re-enrollment is paid immediately.
            'immediate_payment': not trial_active,
            'failed_cycle_action': 'STOP',
            'payment_link_for_failed_attempt': True,
        },
        'success_return_url': f'{settings.app_url}/?billing=return',
        'cancel_return_url': f'{settings.app_url}/?billing=cancel',
        'metadata': {'household_id': subscription.household_id, 'plan_code': subscription.plan_code, 'trial_ends_at': str(subscription.trial_ends_at)},
    }


async def create_xendit_subscription_session(settings, subscription, user) -> dict:
    if not settings.xendit_checkout_ready:
        raise HTTPException(503, 'Subscription checkout is not configured yet. Please contact support.')
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.post(
                f'{settings.xendit_api_base}/sessions',
                auth=(settings.xendit_secret_key, ''),
                headers={'api-version': XENDIT_API_VERSION},
                json=subscription_payload(settings, subscription, user),
            )
    except httpx.HTTPError:
        raise HTTPException(502, 'Could not reach the subscription provider. Please try again later.')
    if response.status_code != 201:
        raise HTTPException(502, 'The subscription provider could not create checkout. Please try again later.')
    try:
        body = response.json()
        checkout_url = hosted_checkout_url(body.get('payment_link_url'))
        if body.get('reference_id') != subscription.provider_reference:
            raise ValueError('Provider reference mismatch.')
        if body.get('currency') != 'PHP' or amount_minor_from_xendit(body.get('amount')) != subscription.amount_minor:
            raise ValueError('Provider price mismatch.')
        session_id = str(body['payment_session_id'])
        plan_id = str(body['recurring_plan_id'])
        customer_id = str(body.get('customer_id') or '')
    except (KeyError, TypeError, ValueError):
        raise HTTPException(502, 'The subscription provider returned an invalid checkout response.')
    return {'checkout_url': checkout_url, 'session_id': session_id, 'plan_id': plan_id, 'customer_id': customer_id}


async def cancel_xendit_session(settings, session_id: str) -> None:
    await _xendit_post(settings, f'/sessions/{session_id}/cancel')


async def deactivate_xendit_plan(settings, plan_id: str) -> None:
    await _xendit_post(settings, f'/recurring/plans/{plan_id}/deactivate', api_version=True)


async def _xendit_post(settings, path: str, api_version: bool = False) -> None:
    if not settings.xendit_checkout_ready:
        raise HTTPException(503, 'Subscription checkout is not configured yet. Please contact support.')
    headers = {'api-version': XENDIT_API_VERSION} if api_version else {}
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.post(f'{settings.xendit_api_base}{path}', auth=(settings.xendit_secret_key, ''), headers=headers)
    except httpx.HTTPError:
        raise HTTPException(502, 'Could not reach the subscription provider. Please try again later.')
    # 404/422 may mean a prior successful call is still being reconciled; do
    # not falsely mark a subscription cancelled in that situation.
    if response.status_code not in {200, 201}:
        raise HTTPException(502, 'The subscription provider could not confirm the cancellation. Please try again later.')
