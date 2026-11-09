from __future__ import annotations
import os
from ipaddress import ip_address, ip_network
from pathlib import Path
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

def flag(name: str, default: str = 'false') -> bool:
    return os.getenv(name, default).lower() in {'1', 'true', 'yes'}


class ProductionConfigurationError(RuntimeError):
    """Raised when a production process is configured with an unsafe local default."""

@dataclass
class Settings:
    environment: str = field(default_factory=lambda: os.getenv('PADALA_ENV', 'development').strip().lower())
    data_dir: Path = field(default_factory=lambda: Path(os.getenv('DATA_DIR', str(ROOT / 'data'))).resolve())
    database_url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', ''))
    app_url: str = field(default_factory=lambda: os.getenv('APP_URL', 'http://localhost:3000').rstrip('/'))
    allowed_origins: list[str] = field(default_factory=lambda: [s.strip().rstrip('/') for s in os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000').split(',') if s.strip()])
    allowed_hosts: list[str] = field(default_factory=lambda: [s.strip().lower() for s in os.getenv('ALLOWED_HOSTS', '').split(',') if s.strip()])
    internal_proxy_origins: list[str] = field(default_factory=lambda: [s.strip().rstrip('/') for s in os.getenv('INTERNAL_PROXY_ORIGINS', '').split(',') if s.strip()])
    trusted_proxy_networks: list[str] = field(default_factory=lambda: [s.strip() for s in os.getenv('TRUSTED_PROXY_NETWORKS', '').split(',') if s.strip()])
    secure_cookies: bool = field(default_factory=lambda: flag('SECURE_COOKIES'))
    registration_enabled: bool = field(default_factory=lambda: flag('REGISTRATION_ENABLED', 'true'))
    email_verification_required: bool = field(default_factory=lambda: flag('EMAIL_VERIFICATION_REQUIRED', 'true' if os.getenv('PADALA_ENV', 'development').lower() == 'production' else 'false'))
    redis_url: str = field(default_factory=lambda: os.getenv('REDIS_URL', '').strip())
    rate_limit_fail_closed: bool = field(default_factory=lambda: flag('RATE_LIMIT_FAIL_CLOSED', 'true' if os.getenv('PADALA_ENV', 'development').lower() == 'production' else 'false'))
    malware_scan_host: str = field(default_factory=lambda: os.getenv('MALWARE_SCAN_HOST', '').strip())
    malware_scan_port: int = field(default_factory=lambda: int(os.getenv('MALWARE_SCAN_PORT', '3310')))
    malware_scan_required: bool = field(default_factory=lambda: flag('MALWARE_SCAN_REQUIRED', 'true' if os.getenv('PADALA_ENV', 'development').lower() == 'production' else 'false'))
    smtp_host: str = field(default_factory=lambda: os.getenv('SMTP_HOST', ''))
    smtp_port: int = field(default_factory=lambda: int(os.getenv('SMTP_PORT', '1025')))
    smtp_user: str = field(default_factory=lambda: os.getenv('SMTP_USER', ''))
    smtp_password: str = field(default_factory=lambda: os.getenv('SMTP_PASSWORD', ''))
    smtp_starttls: bool = field(default_factory=lambda: flag('SMTP_STARTTLS'))
    email_from: str = field(default_factory=lambda: os.getenv('EMAIL_FROM', 'Padala <no-reply@padala.local>'))
    azure_endpoint: str = field(default_factory=lambda: os.getenv('AZURE_DOCUMENT_ENDPOINT', '').rstrip('/'))
    azure_key: str = field(default_factory=lambda: os.getenv('AZURE_DOCUMENT_KEY', ''))
    privacy_controller_name: str = field(default_factory=lambda: os.getenv('PRIVACY_CONTROLLER_NAME', '').strip())
    privacy_controller_address: str = field(default_factory=lambda: os.getenv('PRIVACY_CONTROLLER_ADDRESS', '').strip())
    privacy_contact_email: str = field(default_factory=lambda: os.getenv('PRIVACY_CONTACT_EMAIL', '').strip().lower())
    privacy_notice_version: str = field(default_factory=lambda: os.getenv('PRIVACY_NOTICE_VERSION', '').strip())
    privacy_notice_effective_date: str = field(default_factory=lambda: os.getenv('PRIVACY_NOTICE_EFFECTIVE_DATE', '').strip())
    privacy_legal_basis_summary: str = field(default_factory=lambda: os.getenv('PRIVACY_LEGAL_BASIS_SUMMARY', '').strip())
    privacy_retention_summary: str = field(default_factory=lambda: os.getenv('PRIVACY_RETENTION_SUMMARY', '').strip())
    privacy_processors_summary: str = field(default_factory=lambda: os.getenv('PRIVACY_PROCESSORS_SUMMARY', '').strip())
    # Billing is deliberately off by default. A subscription product needs
    # approved public terms, a secure Xendit server key, and a signed callback
    # before checkout is exposed to a customer. The owner selected these two
    # plan prices and a one-month free trial; the public flags still remain off
    # until the operational launch requirements are complete.
    billing_enabled: bool = field(default_factory=lambda: flag('BILLING_ENABLED'))
    billing_enforcement_enabled: bool = field(default_factory=lambda: flag('BILLING_ENFORCEMENT_ENABLED'))
    billing_basic_price_minor: int = field(default_factory=lambda: int(os.getenv('BILLING_BASIC_PRICE_MINOR', '9900')))
    billing_family_price_minor: int = field(default_factory=lambda: int(os.getenv('BILLING_FAMILY_PRICE_MINOR', '14900')))
    billing_trial_months: int = field(default_factory=lambda: int(os.getenv('BILLING_TRIAL_MONTHS', '1')))
    billing_terms_version: str = field(default_factory=lambda: os.getenv('BILLING_TERMS_VERSION', '').strip())
    billing_terms_effective_date: str = field(default_factory=lambda: os.getenv('BILLING_TERMS_EFFECTIVE_DATE', '').strip())
    billing_support_email: str = field(default_factory=lambda: os.getenv('BILLING_SUPPORT_EMAIL', '').strip().lower())
    billing_refund_summary: str = field(default_factory=lambda: os.getenv('BILLING_REFUND_SUMMARY', '').strip())
    billing_cancellation_summary: str = field(default_factory=lambda: os.getenv('BILLING_CANCELLATION_SUMMARY', '').strip())
    billing_tax_summary: str = field(default_factory=lambda: os.getenv('BILLING_TAX_SUMMARY', '').strip())
    xendit_secret_key: str = field(default_factory=lambda: os.getenv('XENDIT_SECRET_KEY', '').strip())
    xendit_webhook_token: str = field(default_factory=lambda: os.getenv('XENDIT_WEBHOOK_TOKEN', '').strip())
    xendit_api_base: str = field(default_factory=lambda: os.getenv('XENDIT_API_BASE', 'https://api.xendit.co').rstrip('/'))
    max_upload_bytes: int = 5 * 1024 * 1024
    session_hours: int = 24
    worker_enabled: bool = field(default_factory=lambda: flag('EMAIL_WORKER_ENABLED', 'true'))

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / 'uploads'

    @property
    def ocr_enabled(self) -> bool:
        return bool(self.azure_endpoint and self.azure_key)

    @property
    def is_production(self) -> bool:
        return self.environment == 'production'

    @property
    def privacy_notice_published(self) -> bool:
        """Whether the public notice has all operator-owned publication details.

        The app cannot choose the controller, retention schedule, lawful basis, or
        processor terms on the owner's behalf.  These values are intentionally
        public configuration, not secrets.
        """
        return all((
            self.privacy_controller_name,
            self.privacy_controller_address,
            self.privacy_contact_email,
            self.privacy_notice_version,
            self.privacy_notice_effective_date,
            self.privacy_legal_basis_summary,
            self.privacy_retention_summary,
            self.privacy_processors_summary,
        ))

    @property
    def privacy_notice_acknowledgement_required(self) -> bool:
        """A published notice must be acknowledged before household data is shown."""
        return self.privacy_notice_published

    @property
    def billing_terms_published(self) -> bool:
        """Whether the customer-facing commercial terms are complete.

        These fields are public product commitments, never payment secrets.  The
        app intentionally cannot invent a price, refund rule, tax treatment, or
        support address for the operator.
        """
        return all((
            self.billing_terms_version,
            self.billing_terms_effective_date,
            self.billing_support_email,
            self.billing_refund_summary,
            self.billing_cancellation_summary,
            self.billing_tax_summary,
        ))

    @property
    def billing_plans(self) -> tuple[dict[str, object], ...]:
        """The customer-visible Padala household subscription catalogue.

        Member limits are enforced server-side when a paid/trial household
        invites or restores an account. They deliberately count active people,
        including the owner, rather than browser-side form entries.
        """
        return (
            {
                'code': 'basic',
                'name': 'Padala Basic',
                'amount_minor': self.billing_basic_price_minor,
                'currency': 'PHP',
                'interval': 'month',
                'max_members': 4,
                'description': 'For one household with up to 4 active members.',
            },
            {
                'code': 'family',
                'name': 'Padala Family',
                'amount_minor': self.billing_family_price_minor,
                'currency': 'PHP',
                'interval': 'month',
                'max_members': 8,
                'description': 'For a larger household with up to 8 active members.',
            },
        )

    def billing_plan(self, code: str) -> dict[str, object] | None:
        return next((plan for plan in self.billing_plans if plan['code'] == code), None)

    @property
    def billing_catalog_configured(self) -> bool:
        plans = self.billing_plans
        return bool(
            self.billing_trial_months == 1
            and len(plans) == 2
            and all(isinstance(plan['amount_minor'], int) and plan['amount_minor'] > 0 for plan in plans)
            and self.billing_basic_price_minor < self.billing_family_price_minor
        )

    @property
    def xendit_checkout_ready(self) -> bool:
        """A safe, complete server-side Xendit checkout configuration."""
        api = urlsplit(self.xendit_api_base)
        app = self._https_origin(self.app_url)
        return bool(
            self.billing_enabled
            and self.billing_catalog_configured
            and self.billing_terms_published
            and self.xendit_secret_key
            and self.xendit_webhook_token
            and app
            and api.scheme == 'https'
            and api.netloc == 'api.xendit.co'
            and api.path in {'', '/'}
            and not api.query
            and not api.fragment
        )

    @staticmethod
    def _https_origin(value: str) -> str | None:
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.path not in {'', '/'} or parsed.query or parsed.fragment:
            return None
        return f'https://{parsed.netloc}'

    @staticmethod
    def _origin(value: str) -> str | None:
        parsed = urlsplit(value)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.path not in {'', '/'} or parsed.query or parsed.fragment:
            return None
        return f'{parsed.scheme}://{parsed.netloc}'

    @property
    def trusted_hosts(self) -> list[str]:
        """Hosts accepted by the API, including the private Next.js proxy hop."""
        hosts = set(self.allowed_hosts)
        for origin in self.internal_proxy_origins:
            host = urlsplit(origin).hostname
            if host:
                hosts.add(host.lower())
        return sorted(hosts)

    def is_trusted_proxy(self, address: str | None) -> bool:
        if not address:
            return False
        try:
            client = ip_address(address)
            return any(client in ip_network(network, strict=False) for network in self.trusted_proxy_networks)
        except ValueError:
            return False

    def validate(self) -> None:
        """Fail closed when an operator explicitly starts a public production process.

        This deliberately validates only controls the application can verify itself.
        It does not certify a hosting provider, backups, malware scanning, privacy
        notices, billing, or external provider contracts.
        """
        if self.environment not in {'development', 'test', 'staging', 'production'}:
            raise ProductionConfigurationError('PADALA_ENV must be development, test, staging, or production.')
        # This protects every environment from accidentally locking households
        # behind a paywall that has no secure checkout path.
        if self.billing_enforcement_enabled and not self.xendit_checkout_ready:
            raise ProductionConfigurationError('BILLING_ENFORCEMENT_ENABLED=true requires a complete Xendit checkout and published billing terms.')
        if not self.is_production:
            return

        errors: list[str] = []
        app_origin = self._https_origin(self.app_url)
        if not app_origin:
            errors.append('APP_URL must be one HTTPS origin in production.')
        if not self.secure_cookies:
            errors.append('SECURE_COOKIES=true is required in production.')
        if not self.database_url.startswith('postgresql+psycopg://'):
            errors.append('DATABASE_URL must use PostgreSQL via postgresql+psycopg:// in production; SQLite is local-only.')
        if not self.allowed_origins:
            errors.append('ALLOWED_ORIGINS must contain the public HTTPS application origin.')
        else:
            invalid_origins = [origin for origin in self.allowed_origins if not self._https_origin(origin)]
            if invalid_origins:
                errors.append('ALLOWED_ORIGINS may contain only HTTPS origins in production.')
            if app_origin and app_origin not in self.allowed_origins:
                errors.append('ALLOWED_ORIGINS must include APP_URL.')
        parsed_app_url = urlsplit(self.app_url)
        if not self.allowed_hosts or '*' in self.allowed_hosts:
            errors.append('ALLOWED_HOSTS must explicitly list the public application host; wildcards are not allowed.')
        elif parsed_app_url.hostname and parsed_app_url.hostname.lower() not in self.allowed_hosts:
            errors.append('ALLOWED_HOSTS must include the APP_URL hostname.')
        if not self.internal_proxy_origins or any(not self._origin(origin) for origin in self.internal_proxy_origins):
            errors.append('INTERNAL_PROXY_ORIGINS must list the private http(s) API origin used by the Next.js proxy.')
        if not self.trusted_proxy_networks:
            errors.append('TRUSTED_PROXY_NETWORKS must list only the private proxy IP/CIDR ranges.')
        else:
            try:
                for network in self.trusted_proxy_networks:
                    ip_network(network, strict=False)
            except ValueError:
                errors.append('TRUSTED_PROXY_NETWORKS contains an invalid IP or CIDR range.')
        redis = urlsplit(self.redis_url)
        if redis.scheme != 'rediss' or not redis.netloc:
            errors.append('REDIS_URL must be a TLS Redis URL (rediss://...) for shared production rate limits.')
        if not self.rate_limit_fail_closed:
            errors.append('RATE_LIMIT_FAIL_CLOSED=true is required in production.')
        if not self.malware_scan_host or not self.malware_scan_required or not 1 <= self.malware_scan_port <= 65535:
            errors.append('A reachable private malware scanner and MALWARE_SCAN_REQUIRED=true are required in production.')
        if not self.email_verification_required:
            errors.append('EMAIL_VERIFICATION_REQUIRED=true is required in production.')
        if not self.smtp_host or not self.smtp_starttls or self.smtp_port == 465 or not self.email_from or self.email_from.endswith('@padala.local>'):
            errors.append('Configure a verified SMTP submission service with STARTTLS and a non-local EMAIL_FROM for production.')
        if not self.privacy_notice_published:
            errors.append('Configure the controller, contact, notice version/date, legal-basis, retention, and processor fields required by the public privacy notice.')
        if self.worker_enabled:
            errors.append('EMAIL_WORKER_ENABLED=false is required for API processes in production; run the dedicated worker once instead.')
        if self.billing_enabled:
            if not self.xendit_checkout_ready:
                errors.append('Public billing requires valid BILLING_BASIC_PRICE_MINOR and BILLING_FAMILY_PRICE_MINOR values, BILLING_TRIAL_MONTHS=1, published commercial terms, XENDIT_SECRET_KEY, XENDIT_WEBHOOK_TOKEN, HTTPS APP_URL, and an HTTPS XENDIT_API_BASE.')
            if self.xendit_api_base != 'https://api.xendit.co':
                errors.append('Production XENDIT_API_BASE must be https://api.xendit.co; use test credentials outside production.')
            if not self.billing_enforcement_enabled:
                errors.append('Public billing requires BILLING_ENFORCEMENT_ENABLED=true so paid access is not misrepresented.')
        if errors:
            raise ProductionConfigurationError('Invalid production configuration:\n- ' + '\n- '.join(errors))
