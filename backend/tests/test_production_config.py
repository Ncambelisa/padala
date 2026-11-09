import pytest

from app.config import ProductionConfigurationError, Settings


def production_settings(**overrides):
    values = {
        'environment': 'production',
        'app_url': 'https://app.example.test',
        'allowed_origins': ['https://app.example.test'],
        'allowed_hosts': ['app.example.test'],
        'internal_proxy_origins': ['http://padala-api.internal:8000'],
        'trusted_proxy_networks': ['10.42.0.0/16'],
        'secure_cookies': True,
        'email_verification_required': True,
        'database_url': 'postgresql+psycopg://user:pass@db.example.test:5432/padala',
        'redis_url': 'rediss://:password@redis.example.test:6380/0',
        'rate_limit_fail_closed': True,
        'malware_scan_host': 'clamd.internal.example.test',
        'malware_scan_required': True,
        'smtp_host': 'smtp.example.test',
        'smtp_port': 587,
        'smtp_starttls': True,
        'email_from': 'Padala <support@example.test>',
        'privacy_controller_name': 'Padala Pilot Operator',
        'privacy_controller_address': 'Manila, Philippines',
        'privacy_contact_email': 'privacy@example.test',
        'privacy_notice_version': '1.0',
        'privacy_notice_effective_date': '2026-11-03',
        'privacy_legal_basis_summary': 'Provision of the requested pilot service and consent where applicable.',
        'privacy_retention_summary': 'Retain active records while the pilot is active, then delete under the approved closure process.',
        'privacy_processors_summary': 'Named hosting, database, backup, email, scanner, and optional extraction processors.',
        'worker_enabled': False,
    }
    values.update(overrides)
    return Settings(**values)


def test_production_configuration_accepts_explicit_safe_baseline():
    production_settings().validate()


def test_production_configuration_accepts_complete_paid_xendit_setup():
    production_settings(
        billing_enabled=True,
        billing_enforcement_enabled=True,
        billing_basic_price_minor=9900,
        billing_family_price_minor=14900,
        billing_trial_months=1,
        billing_terms_version='1.0',
        billing_terms_effective_date='2026-11-04',
        billing_support_email='support@example.test',
        billing_refund_summary='Approved fictional refund policy.',
        billing_cancellation_summary='Approved fictional cancellation policy.',
        billing_tax_summary='Approved fictional tax wording.',
        xendit_secret_key='xnd_production_example',
        xendit_webhook_token='example-webhook-token',
    ).validate()


@pytest.mark.parametrize('overrides', [
    {'secure_cookies': False},
    {'database_url': 'sqlite:////tmp/padala.sqlite3'},
    {'allowed_origins': ['http://app.example.test']},
    {'allowed_hosts': ['*']},
    {'internal_proxy_origins': []},
    {'trusted_proxy_networks': []},
    {'redis_url': 'redis://redis.example.test:6379/0'},
    {'rate_limit_fail_closed': False},
    {'email_verification_required': False},
    {'malware_scan_host': ''},
    {'malware_scan_required': False},
    {'smtp_starttls': False},
    {'privacy_contact_email': ''},
    {'worker_enabled': True},
])
def test_production_configuration_rejects_unsafe_defaults(overrides):
    with pytest.raises(ProductionConfigurationError):
        production_settings(**overrides).validate()


def test_non_production_keeps_local_developer_defaults():
    Settings(environment='development').validate()


@pytest.mark.parametrize(('database_url', 'expected'), [
    ('postgresql://user:pass@db.example.test:5432/padala', 'postgresql+psycopg://user:pass@db.example.test:5432/padala'),
    ('postgres://user:pass@db.example.test:5432/padala', 'postgresql+psycopg://user:pass@db.example.test:5432/padala'),
])
def test_standard_managed_postgres_urls_use_the_psycopg_driver(database_url, expected):
    assert production_settings(database_url=database_url).sqlalchemy_database_url == expected
    production_settings(database_url=database_url).validate()


def test_render_style_public_host_configures_the_staging_origin(monkeypatch):
    monkeypatch.delenv('APP_URL', raising=False)
    monkeypatch.delenv('ALLOWED_ORIGINS', raising=False)
    monkeypatch.setenv('PUBLIC_APP_HOST', 'padala-staging.example.test')
    settings = Settings(environment='staging')
    assert settings.app_url == 'https://padala-staging.example.test'
    assert 'https://padala-staging.example.test' in settings.allowed_origins


def test_only_configured_proxy_networks_are_trusted():
    settings = production_settings()
    assert settings.is_trusted_proxy('10.42.0.7') is True
    assert settings.is_trusted_proxy('10.43.0.7') is False
