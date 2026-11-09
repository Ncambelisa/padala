from fastapi.testclient import TestClient

import time
from datetime import datetime, timezone

from app.billing import amount_for_xendit, amount_minor_from_xendit, one_month_trial_end, subscription_payload
from app.config import Settings
from app.main import create_app
from app.models import Subscription
from .conftest import PASSWORD


def billing_settings(tmp_path, **overrides):
    values = {
        'data_dir': tmp_path,
        'worker_enabled': False,
        'registration_enabled': True,
        'allowed_origins': ['https://app.example.test'],
        'app_url': 'https://app.example.test',
        'billing_enabled': True,
        'billing_enforcement_enabled': True,
        'billing_basic_price_minor': 9900,
        'billing_family_price_minor': 14900,
        'billing_trial_months': 1,
        'billing_terms_version': '1.0',
        'billing_terms_effective_date': '2026-11-04',
        'billing_support_email': 'support@example.test',
        'billing_refund_summary': 'Test refund policy.',
        'billing_cancellation_summary': 'Test cancellation policy.',
        'billing_tax_summary': 'Test tax treatment.',
        'xendit_secret_key': 'xnd_development_test_key',
        'xendit_webhook_token': 'xendit-test-webhook-token',
        'xendit_api_base': 'https://api.xendit.co',
    }
    values.update(overrides)
    return Settings(**values)


def register_owner(client):
    response = client.post('/api/v1/auth/register', json={
        'name': 'Owner', 'email': 'owner@example.test',
        'household_name': 'Test household', 'password': PASSWORD,
    })
    assert response.status_code == 201, response.text
    client.headers['X-CSRF-Token'] = response.json()['csrf']


def subscription_for(app):
    with app.state.session_factory() as db:
        return db.query(Subscription).one()


def test_money_conversion_and_hosted_subscription_payload(tmp_path):
    settings = billing_settings(tmp_path, billing_family_price_minor=14999)
    trial_end = int(one_month_trial_end(datetime(2026, 11, 4, 10, 30, tzinfo=timezone.utc)).timestamp())
    subscription = Subscription(household_id='h' * 32, plan_code='family', amount_minor=14999, trial_ends_at=trial_end, provider_reference='sub_reference')
    class User:
        id = 'u' * 32
        name = 'Nico Cambelisa'
        email = 'nico@example.test'
    payload = subscription_payload(settings, subscription, User())
    assert amount_for_xendit(14999) == 149.99
    assert amount_minor_from_xendit('149.99') == 14999
    assert payload['session_type'] == 'SUBSCRIPTION'
    assert payload['mode'] == 'PAYMENT_LINK'
    assert payload['amount'] == 149.99
    assert payload['subscription']['schedule']['anchor_date'] == '2026-12-04T10:30:00Z'
    assert payload['subscription']['immediate_payment'] is False
    assert payload['success_return_url'] == 'https://app.example.test/?billing=return'


def test_one_month_trial_uses_the_first_supported_later_anchor():
    assert one_month_trial_end(datetime(2026, 1, 28, 9, tzinfo=timezone.utc)).isoformat() == '2026-02-28T09:00:00+00:00'
    # Xendit Payment Sessions only permit anchors through day 28. Padala
    # extends (never shortens) the promised free month for late-month signup.
    assert one_month_trial_end(datetime(2026, 1, 31, 9, tzinfo=timezone.utc)).isoformat() == '2026-03-01T09:00:00+00:00'


def test_billing_is_disabled_without_complete_operator_configuration(client):
    register_owner(client)
    assert client.get('/api/v1/billing/subscription').json()['checkout_available'] is False
    response = client.post('/api/v1/billing/checkout', json={'plan_code': 'basic'})
    assert response.status_code == 503


def test_enforcement_cannot_be_enabled_without_a_safe_checkout(tmp_path):
    try:
        Settings(data_dir=tmp_path, billing_enforcement_enabled=True).validate()
    except Exception as error:
        assert 'BILLING_ENFORCEMENT_ENABLED=true requires a complete Xendit checkout' in str(error)
    else:
        raise AssertionError('unsafe paid-access configuration was accepted')


def test_xendit_subscription_webhook_controls_entitlement(tmp_path, monkeypatch):
    settings = billing_settings(tmp_path)
    test_app = create_app(settings)

    async def fake_session(_settings, _subscription, _user):
        return {
            'checkout_url': 'https://checkout-staging.xendit.co/sessions/ps-test-session',
            'session_id': 'ps-test-session',
            'plan_id': 'repl-test-plan',
            'customer_id': 'cust-test-customer',
        }

    async def fake_deactivate(_settings, _plan_id):
        return None

    monkeypatch.setattr('app.main.create_xendit_subscription_session', fake_session)
    monkeypatch.setattr('app.main.deactivate_xendit_plan', fake_deactivate)
    with TestClient(test_app) as c:
        register_owner(c)
        # The browser must not gain records access merely by creating checkout.
        assert c.get('/api/v1/remittances').status_code == 402
        checkout = c.post('/api/v1/billing/checkout', json={'plan_code': 'basic'})
        assert checkout.status_code == 200, checkout.text
        assert checkout.json()['checkout_url'].startswith('https://checkout-staging.xendit.co/')
        subscription = subscription_for(test_app)
        payload = {
            'event': 'recurring.plan.activated',
            'data': {
                'id': 'repl-test-plan',
                'reference_id': subscription.provider_reference,
                'payment_session_id': 'ps-test-session',
                'customer_id': 'cust-test-customer',
                'currency': 'PHP',
                'amount': 99,
            },
        }
        headers = {'x-callback-token': 'xendit-test-webhook-token'}
        activated = c.post('/api/v1/billing/xendit/webhook', json=payload, headers=headers)
        assert activated.status_code == 200, activated.text
        assert c.get('/api/v1/remittances').status_code == 200
        active = c.get('/api/v1/billing/subscription').json()['subscription']
        assert active['in_trial'] is True
        assert active['amount_minor'] == 9900
        duplicate = c.post('/api/v1/billing/xendit/webhook', json=payload, headers=headers)
        assert duplicate.json() == {'ok': True, 'duplicate': True}
        assert c.post('/api/v1/billing/xendit/webhook', json=payload, headers={'x-callback-token': 'wrong'}).status_code == 401
        # A trial does not turn into indefinite free access when its scheduled
        # first payment has not been confirmed.
        with test_app.state.session_factory() as db:
            db.query(Subscription).one().trial_ends_at = int(time.time()) - 1
            db.commit()
        assert c.get('/api/v1/remittances').status_code == 402
        paid = c.post('/api/v1/billing/xendit/webhook', json={
            'event': 'recurring.cycle.succeeded',
            'data': {
                'plan_id': 'repl-test-plan',
                'reference_id': subscription.provider_reference,
                'currency': 'PHP',
                'amount': 99,
            },
        }, headers=headers)
        assert paid.status_code == 200, paid.text
        assert c.get('/api/v1/remittances').status_code == 200
        cancel = c.post('/api/v1/billing/cancel')
        assert cancel.status_code == 200, cancel.text
        assert cancel.json()['subscription']['status'] == 'cancellation_pending'
        assert c.get('/api/v1/remittances').status_code == 200
        stopped = c.post('/api/v1/billing/xendit/webhook', json={
            'event': 'recurring.plan.inactivated',
            'data': {'id': 'repl-test-plan', 'reference_id': subscription.provider_reference, 'currency': 'PHP', 'amount': 99},
        }, headers=headers)
        assert stopped.status_code == 200
        assert c.get('/api/v1/billing/subscription').json()['subscription']['status'] == 'canceled'
        assert c.get('/api/v1/remittances').status_code == 402


def test_trial_is_used_once_per_household(tmp_path, monkeypatch):
    settings = billing_settings(tmp_path)
    test_app = create_app(settings)

    async def fake_session(_settings, _subscription, _user):
        return {
            'checkout_url': 'https://checkout-staging.xendit.co/sessions/ps-test-session',
            'session_id': 'ps-test-session',
            'plan_id': 'repl-test-plan',
            'customer_id': 'cust-test-customer',
        }

    async def fake_deactivate(_settings, _plan_id):
        return None

    monkeypatch.setattr('app.main.create_xendit_subscription_session', fake_session)
    monkeypatch.setattr('app.main.deactivate_xendit_plan', fake_deactivate)
    with TestClient(test_app) as c:
        register_owner(c)
        assert c.post('/api/v1/billing/checkout', json={'plan_code': 'family'}).status_code == 200
        subscription = subscription_for(test_app)
        headers = {'x-callback-token': 'xendit-test-webhook-token'}
        c.post('/api/v1/billing/xendit/webhook', json={
            'event': 'recurring.plan.activated',
            'data': {'id': 'repl-test-plan', 'reference_id': subscription.provider_reference, 'payment_session_id': 'ps-test-session', 'currency': 'PHP', 'amount': 149},
        }, headers=headers)
        assert c.post('/api/v1/billing/cancel').status_code == 200
        assert c.post('/api/v1/billing/xendit/webhook', json={
            'event': 'recurring.plan.inactivated',
            'data': {'id': 'repl-test-plan', 'reference_id': subscription.provider_reference, 'currency': 'PHP', 'amount': 149},
        }, headers=headers).status_code == 200
        restarted = c.post('/api/v1/billing/checkout', json={'plan_code': 'basic'})
        assert restarted.status_code == 200, restarted.text
        with test_app.state.session_factory() as db:
            current = db.query(Subscription).one()
            assert current.plan_code == 'basic'
            assert current.amount_minor == 9900
            assert current.trial_started_at > 0
            assert current.trial_ends_at == 0
            assert subscription_payload(settings, current, type('User', (), {'id': 'u' * 32, 'name': 'Owner', 'email': 'owner@example.test'})())['subscription']['immediate_payment'] is True


def test_basic_plan_enforces_its_active_member_capacity(tmp_path, monkeypatch):
    settings = billing_settings(tmp_path)
    test_app = create_app(settings)

    async def fake_session(_settings, _subscription, _user):
        return {
            'checkout_url': 'https://checkout-staging.xendit.co/sessions/ps-test-session',
            'session_id': 'ps-test-session',
            'plan_id': 'repl-test-plan',
            'customer_id': 'cust-test-customer',
        }

    monkeypatch.setattr('app.main.create_xendit_subscription_session', fake_session)
    with TestClient(test_app) as c:
        register_owner(c)
        assert c.post('/api/v1/billing/checkout', json={'plan_code': 'basic'}).status_code == 200
        subscription = subscription_for(test_app)
        assert c.post('/api/v1/billing/xendit/webhook', json={
            'event': 'recurring.plan.activated',
            'data': {'id': 'repl-test-plan', 'reference_id': subscription.provider_reference, 'payment_session_id': 'ps-test-session', 'currency': 'PHP', 'amount': 99},
        }, headers={'x-callback-token': 'xendit-test-webhook-token'}).status_code == 200
        for index in range(3):
            response = c.post('/api/v1/invitations', json={'name': f'Member {index}', 'email': f'member-{index}@example.test'})
            assert response.status_code == 201, response.text
        full = c.post('/api/v1/invitations', json={'name': 'Member four', 'email': 'member-four@example.test'})
        assert full.status_code == 409
        assert 'up to 4 active household members' in full.json()['detail']


def test_production_rejects_incomplete_or_non_enforced_billing(tmp_path):
    settings = billing_settings(tmp_path, environment='production', billing_enforcement_enabled=False)
    # Other production prerequisites are deliberately absent, but this confirms
    # the commercial gate is represented in the operator-visible failures.
    try:
        settings.validate()
    except Exception as error:
        assert 'Public billing requires BILLING_ENFORCEMENT_ENABLED=true' in str(error)
    else:
        raise AssertionError('unsafe production billing configuration was accepted')
