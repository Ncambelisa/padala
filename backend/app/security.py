from __future__ import annotations
import hashlib
from ipaddress import ip_address
import secrets
import time
from threading import Lock
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from .models import LoginSession, User

COOKIE = 'padala_session'
HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_HASH = HASHER.hash('not-a-real-user-password-2026')

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def check_password(password: str, encoded: str) -> bool:
    try:
        return HASHER.verify(encoded, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False

class RateLimiter:
    """Rate limiter with an optional Redis-backed, shared production mode."""
    _LUA_HIT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return count
"""

    def __init__(self, redis_url: str = '', fail_closed: bool = False):
        self.entries: dict[str, list[float]] = {}
        self.lock = Lock()
        self.fail_closed = fail_closed
        self.redis = None
        if redis_url:
            try:
                import redis
                self.redis = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
            except ImportError as exc:
                raise RuntimeError('Redis rate limiting is configured but the redis package is unavailable. Install backend requirements.') from exc

    def hit(self, key: str, limit: int = 15, window: int = 900):
        if self.redis is not None:
            try:
                # Hash the key so account emails/IP addresses are not stored as Redis key text.
                redis_key = 'padala:rate-limit:' + hashlib.sha256(key.encode()).hexdigest()
                count = int(self.redis.eval(self._LUA_HIT, 1, redis_key, window))
                if count > limit:
                    raise HTTPException(429, 'Too many attempts. Please try again later.')
                return
            except HTTPException:
                raise
            except Exception:
                if self.fail_closed:
                    raise HTTPException(503, 'The security service is temporarily unavailable. Please try again later.')
                # Development fallback only. Production configuration requires fail-closed.
        now = time.time()
        with self.lock:
            if len(self.entries) > 10000:
                self.entries = {k: [t for t in v if t > now-window] for k,v in self.entries.items() if v and v[-1] > now-window}
            items = [t for t in self.entries.get(key, []) if t > now-window]
            if len(items) >= limit:
                raise HTTPException(429, 'Too many attempts. Please try again later.')
            self.entries[key] = items + [now]


def request_client_address(request: Request, settings) -> str:
    """Use a forwarded address only when the direct sender is a configured proxy."""
    direct = request.client.host if request.client else 'unknown'
    if settings.is_trusted_proxy(direct):
        forwarded = request.headers.get('x-forwarded-for', '').split(',', 1)[0].strip()
        if forwarded:
            try:
                return str(ip_address(forwarded))
            except ValueError:
                pass
    return direct

def get_db(request: Request):
    with request.app.state.session_factory() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise

def authenticate(request: Request, db: Session, require_privacy_notice: bool = True) -> User:
    token = request.cookies.get(COOKIE, '')
    session = db.get(LoginSession, token_hash(token))
    if not session or session.expires_at <= int(time.time()):
        raise HTTPException(401, 'Please sign in to continue.')
    if request.method not in {'GET','HEAD','OPTIONS'}:
        csrf = request.headers.get('x-csrf-token', '')
        if not secrets.compare_digest(csrf, session.csrf):
            raise HTTPException(403, 'Security token missing or expired. Refresh and try again.')
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, 'Please sign in to continue.')
    if not user.is_active:
        # Revocation normally deletes every session atomically.  This fallback
        # also closes a session if a concurrent request races that deletion.
        db.delete(session)
        db.commit()
        raise HTTPException(403, 'Household access has been removed. Contact the household owner.')
    if request.app.state.settings.email_verification_required and not user.email_verified:
        db.delete(session)
        db.commit()
        raise HTTPException(403, 'Verify your email address before continuing.')
    settings=request.app.state.settings
    if require_privacy_notice and settings.privacy_notice_acknowledgement_required and not secrets.compare_digest(user.privacy_notice_version or '',settings.privacy_notice_version):
        raise HTTPException(428, 'Review and acknowledge the current privacy notice before continuing.')
    request.state.login_session = session
    return user

def require_sender(user: User):
    if user.role != 'sender':
        raise HTTPException(403, 'Only the OFW account can perform this action.')

def new_session(db, user, response, settings):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, csrf=csrf,
                        expires_at=int(time.time()) + settings.session_hours*3600))
    response.set_cookie(COOKIE, token, max_age=settings.session_hours*3600,
                        httponly=True, secure=settings.secure_cookies, samesite='lax', path='/')
    return csrf
