from __future__ import annotations
import csv
import hashlib
import io
import json
import secrets
import time
import threading
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated
from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select, delete, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from .config import Settings
from .migrations import upgrade_database
from .db import Base, make_database
from .models import *
from .schemas import *
from .security import *
from .services import audit, notify, queue_email, inspect_file, scan_file, extract_azure, send_outbox
from .billing import create_xendit_subscription_session, cancel_xendit_session, deactivate_xendit_plan, amount_minor_from_xendit, one_month_trial_end, subscription_has_access
from .presenters import user_dict, upload_dict, evidence_dict, remittance_dict, event_dict, subscription_dict

Db = Annotated[Session, Depends(get_db)]

def current_user(request: Request, db: Db) -> User:
    user = authenticate(request, db)
    # A locked household can still read its billing state, cancel a charge, and
    # manage its account.  Household records stay protected until a signed
    # Xendit activation webhook marks the subscription active.
    exempt_prefixes = ('/api/v1/auth/', '/api/v1/billing/')
    settings = request.app.state.settings
    if settings.billing_enforcement_enabled and not request.url.path.startswith(exempt_prefixes):
        subscription = db.scalar(select(Subscription).where(Subscription.household_id == user.household_id))
        # A linked subscription starts the household's one-month trial. After
        # that, access continues only after a signed recurring-cycle success.
        # Keep existing access while a provider-confirmed cancellation is in
        # flight; a browser click is never the entitlement boundary.
        if not subscription_has_access(subscription):
            raise HTTPException(402, 'An active household subscription is required to access Padala records. Open Billing to subscribe or refresh its status.')
    return user
Auth = Annotated[User, Depends(current_user)]

def user_for_privacy_notice(request: Request, db: Db) -> User:
    return authenticate(request, db, require_privacy_notice=False)
PrivacyAuth = Annotated[User, Depends(user_for_privacy_notice)]

def user_for_billing(request: Request, db: Db) -> User:
    return authenticate(request, db)
BillingAuth = Annotated[User, Depends(user_for_billing)]

def owned(db, model, object_id, user):
    item = db.get(model,object_id)
    if item is None or item.household_id != user.household_id:
        raise HTTPException(404,'Record not found.')
    return item

def require_version(item, version):
    if item.version != version:
        raise HTTPException(409,'This receipt changed in another session. Refresh before reviewing it.')

def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.validate()
    engine, factory = make_database(settings)
    stop = threading.Event()
    @asynccontextmanager
    async def lifespan(app):
        # Versioned schema; migrations are no-ops once applied.
        upgrade_database(engine)
        worker = None
        if settings.worker_enabled:
            worker=threading.Thread(target=send_outbox,args=(factory,settings,stop),daemon=True)
            worker.start()
        yield
        stop.set()
        if worker:
            worker.join(timeout=12)
        engine.dispose()

    app=FastAPI(
        title='Padala API',
        version='1.0.0',
        description='Household remittance allocations and evidence. Not a payment service or receipt-authentication API.',
        lifespan=lifespan,
        docs_url=None if settings.is_production else '/docs',
        redoc_url=None if settings.is_production else '/redoc',
        openapi_url=None if settings.is_production else '/openapi.json',
    )
    app.state.settings=settings
    app.state.engine=engine
    app.state.session_factory=factory
    app.state.limiter=RateLimiter(settings.redis_url, settings.rate_limit_fail_closed)
    if settings.is_production:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse({'detail':'This record already exists or conflicts with a related record. Refresh and try again.'},409)

    @app.exception_handler(StaleDataError)
    async def stale(request, exc):
        return JSONResponse({'detail':'Another session updated this record. Refresh before trying again.'},409)

    @app.middleware('http')
    async def boundaries(request: Request, call_next):
        request_id = secrets.token_hex(16)
        if request.method in {'POST','PUT','PATCH','DELETE'}:
            is_xendit_webhook = request.url.path == '/api/v1/billing/xendit/webhook'
            if not is_xendit_webhook:
                origin=request.headers.get('origin','').rstrip('/')
                is_private_proxy = origin in settings.internal_proxy_origins and settings.is_trusted_proxy(request.client.host if request.client else None)
                if (origin and origin not in settings.allowed_origins and not is_private_proxy) or request.headers.get('sec-fetch-site')=='cross-site':
                    return JSONResponse({'detail':'This origin is not allowed. Configure ALLOWED_ORIGINS for your local app address.'},403)
            max_request=128*1024 if is_xendit_webhook else settings.max_upload_bytes+128*1024
            try:
                if int(request.headers.get('content-length','0'))>max_request:
                    return JSONResponse({'detail':'Request too large.'},413)
            except ValueError:
                return JSONResponse({'detail':'Invalid request length.'},400)
            chunks=[]; size=0
            async for chunk in request.stream():
                size+=len(chunk)
                if size>max_request:
                    return JSONResponse({'detail':'Request too large.'},413)
                chunks.append(chunk)
            request._body=b''.join(chunks)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Cross-Origin-Opener-Policy']='same-origin'
        response.headers['Cross-Origin-Resource-Policy']='same-origin'
        response.headers['X-Permitted-Cross-Domain-Policies']='none'
        response.headers['X-Request-ID']=request_id
        if settings.secure_cookies:
            response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    def limit(request, prefix, limit=15):
        address=request_client_address(request,settings)
        app.state.limiter.hit(prefix+':'+address,limit)

    def active_member_count(db: Session, household_id: str) -> int:
        return int(db.scalar(select(func.count()).select_from(User).where(User.household_id==household_id, User.is_active==True)) or 0)

    def pending_invitation_count(db: Session, household_id: str) -> int:
        return int(db.scalar(select(func.count()).select_from(Invitation).where(Invitation.household_id==household_id, Invitation.used==False, Invitation.expires_at>=int(time.time()))) or 0)

    def subscription_member_limit(db: Session, household_id: str) -> int | None:
        if not settings.billing_enabled:
            return None
        subscription=db.scalar(select(Subscription).where(Subscription.household_id==household_id))
        plan=settings.billing_plan(subscription.plan_code) if subscription else None
        return int(plan['max_members']) if plan else None

    def require_household_capacity(db: Session, household_id: str, *, include_pending: bool) -> None:
        member_limit=subscription_member_limit(db,household_id)
        if member_limit is None:
            return
        occupied=active_member_count(db,household_id)
        if include_pending:
            occupied+=pending_invitation_count(db,household_id)
        if occupied>=member_limit:
            raise HTTPException(409, f'The selected subscription allows up to {member_limit} active household members. Remove a member or choose Padala Family before inviting another person.')

    @app.get('/api/v1/health',tags=['System'])
    def health(db: Db):
        db.execute(select(1))
        return {'status':'ok','version':'1.0.0','storage':'database','environment':settings.environment}

    @app.get('/api/v1/config',tags=['System'])
    def config():
        return {'ocr_configured':settings.ocr_enabled,'email_configured':bool(settings.smtp_host),
                'bank_confirmation':False,'payment_processing':settings.xendit_checkout_ready,'registration_enabled':settings.registration_enabled,
                'email_verification_required':settings.email_verification_required,
                'max_upload_bytes':settings.max_upload_bytes,'version':'1.0.0',
                'privacy_notice':{
                    'published':settings.privacy_notice_published,
                    'acknowledgement_required':settings.privacy_notice_acknowledgement_required,
                    'controller_name':settings.privacy_controller_name if settings.privacy_notice_published else '',
                    'controller_address':settings.privacy_controller_address if settings.privacy_notice_published else '',
                    'contact_email':settings.privacy_contact_email if settings.privacy_notice_published else '',
                    'version':settings.privacy_notice_version if settings.privacy_notice_published else '',
                    'effective_date':settings.privacy_notice_effective_date if settings.privacy_notice_published else '',
                    'legal_basis_summary':settings.privacy_legal_basis_summary if settings.privacy_notice_published else '',
                    'retention_summary':settings.privacy_retention_summary if settings.privacy_notice_published else '',
                    'processors_summary':settings.privacy_processors_summary if settings.privacy_notice_published else '',
                },
                'billing': subscription_dict(None, settings)}

    def privacy_notice_acknowledgement(version: str) -> tuple[str, int]:
        if not settings.privacy_notice_acknowledgement_required:
            return '', 0
        if not secrets.compare_digest(version,settings.privacy_notice_version):
            raise HTTPException(422,'Read and acknowledge the current privacy notice before creating an account.')
        return settings.privacy_notice_version, int(time.time())

    def queue_email_verification(db: Session, user: User) -> None:
        if not settings.smtp_host:
            raise HTTPException(503, 'Email verification is unavailable until the administrator configures email delivery.')
        db.execute(delete(EmailVerificationToken).where(EmailVerificationToken.user_id==user.id))
        token=secrets.token_urlsafe(32)
        db.add(EmailVerificationToken(token_hash=token_hash(token),user_id=user.id,expires_at=int(time.time())+24*3600))
        queue_email(db,settings,user.email,'Verify your Padala email address',
                    f'Open {settings.app_url}/?verify={token}\nThis link expires in 24 hours. If you did not create this account, ignore this email.')

    @app.post('/api/v1/auth/register',tags=['Accounts'],status_code=201)
    def register(data:Register,request:Request,db:Db):
        limit(request,'register',10)
        if not settings.registration_enabled:
            raise HTTPException(403,'New household registration is disabled.')
        if db.scalar(select(User).where(User.email==data.email)):
            raise HTTPException(409,'This email cannot be registered. Sign in or reset your password.')
        privacy_version,privacy_acknowledged_at=privacy_notice_acknowledgement(data.privacy_notice_version)
        household=Household(name=data.household_name)
        db.add(household);db.flush()
        user=User(name=data.name,email=data.email,household_id=household.id,role='sender',password_hash=HASHER.hash(data.password),email_verified=not settings.email_verification_required,privacy_notice_version=privacy_version,privacy_notice_acknowledged_at=privacy_acknowledged_at)
        db.add(user);db.flush()
        audit(db,user,'household_created','Household created.')
        if settings.email_verification_required:
            queue_email_verification(db,user)
            db.commit()
            return {'verification_required':True,'message':'Check your email for a verification link before signing in.'}
        response=JSONResponse({'user':user_dict(user),'household':{'id':household.id,'name':household.name}},201)
        csrf=new_session(db,user,response,settings)
        response.body=json.dumps({'user':user_dict(user),'csrf':csrf,'household':{'id':household.id,'name':household.name}}).encode()
        response.headers['content-length']=str(len(response.body))
        db.commit()
        return response

    @app.post('/api/v1/auth/login',tags=['Accounts'])
    def login(data:Login,request:Request,db:Db):
        limit(request,'login',50)
        app.state.limiter.hit('email:'+data.email,10)
        user=db.scalar(select(User).where(User.email==data.email))
        if not check_password(data.password,user.password_hash if user else DUMMY_HASH):
            raise HTTPException(401,'Email or password is incorrect.')
        if not user.is_active:
            raise HTTPException(403,'Household access has been removed. Contact the household owner.')
        if settings.email_verification_required and not user.email_verified:
            raise HTTPException(403,'Verify your email address before signing in. You can request a new verification email.')
        response=JSONResponse({'ok':True})
        csrf=new_session(db,user,response,settings)
        response.body=json.dumps({'user':user_dict(user),'csrf':csrf}).encode()
        response.headers['content-length']=str(len(response.body))
        db.commit()
        return response

    @app.get('/api/v1/auth/me',tags=['Accounts'])
    def me(request:Request,db:Db,user:PrivacyAuth):
        house=db.get(Household,user.household_id)
        subscription=db.scalar(select(Subscription).where(Subscription.household_id==user.household_id))
        return {'user':user_dict(user),'csrf':request.state.login_session.csrf,'household':{'id':house.id,'name':house.name},
                'privacy_notice_acknowledgement_required':settings.privacy_notice_acknowledgement_required and not secrets.compare_digest(user.privacy_notice_version or '',settings.privacy_notice_version),
                'billing':subscription_dict(subscription,settings)}

    @app.get('/api/v1/billing/subscription',tags=['Billing'])
    def billing_subscription(db:Db,user:BillingAuth):
        subscription=db.scalar(select(Subscription).where(Subscription.household_id==user.household_id))
        return subscription_dict(subscription,settings)

    @app.post('/api/v1/billing/checkout',tags=['Billing'])
    async def billing_checkout(data:SubscriptionCheckout,db:Db,user:BillingAuth):
        """Create a hosted Xendit Subscription Session for the household owner."""
        require_sender(user)
        if not settings.xendit_checkout_ready:
            raise HTTPException(503,'Subscription checkout is not configured yet. Please contact support.')
        plan=settings.billing_plan(data.plan_code)
        if plan is None:
            raise HTTPException(422,'Choose a valid Padala subscription plan.')
        if active_member_count(db,user.household_id)>int(plan['max_members']):
            raise HTTPException(409, f"{plan['name']} supports up to {plan['max_members']} active household members. Choose Padala Family or remove access before continuing.")
        now=int(time.time())
        subscription=db.scalar(select(Subscription).where(Subscription.household_id==user.household_id))
        if subscription and subscription.status=='active':
            if subscription_has_access(subscription,now):
                raise HTTPException(409,'This household already has an active subscription.')
            raise HTTPException(409,'The trial has ended and the first recurring payment is still awaiting confirmation. Refresh Billing shortly or contact support before starting another subscription.')
        if subscription and subscription.status=='cancellation_pending':
            raise HTTPException(409,'Cancellation is awaiting provider confirmation. Refresh the billing status shortly.')
        if subscription and subscription.status=='pending' and subscription.checkout_url and subscription.checkout_expires_at>now:
            if subscription.plan_code!=data.plan_code:
                raise HTTPException(409,'A secure checkout is already open for the other plan. Cancel that checkout before choosing a different plan.')
            return {'checkout_url':subscription.checkout_url,'message':'Continue with the existing secure checkout session.'}
        if subscription and subscription.status=='pending' and not subscription.provider_session_id:
            raise HTTPException(409,'A checkout request is still being prepared. Refresh billing before trying again.')
        trial_ends_at=int(one_month_trial_end().timestamp()) if subscription is None or not subscription.trial_started_at else 0
        if subscription is None:
            subscription=Subscription(household_id=user.household_id,plan_code=data.plan_code,amount_minor=int(plan['amount_minor']),trial_ends_at=trial_ends_at,
                                      provider_reference=f'sub_{user.household_id[:16]}_{secrets.token_urlsafe(12)[:20]}')
            db.add(subscription)
        else:
            # An expired/cancelled hosted checkout cannot activate again. Retain
            # the household's single reconciliation record but clear only old
            # provider identifiers before requesting a brand-new session.
            subscription.plan_code=data.plan_code
            subscription.amount_minor=int(plan['amount_minor'])
            subscription.currency='PHP'
            subscription.status='pending'
            subscription.provider_reference=f'sub_{user.household_id[:16]}_{secrets.token_urlsafe(12)[:20]}'
            subscription.provider_customer_id=''
            subscription.provider_session_id=None
            subscription.provider_plan_id=None
            subscription.checkout_url=''
            subscription.checkout_expires_at=0
            subscription.trial_ends_at=trial_ends_at
            subscription.first_payment_confirmed_at=0
            subscription.cancel_requested_at=0
            subscription.ended_at=0
        # Commit the unique local reference first. It stops concurrent browser
        # tabs from creating multiple chargeable subscription setups.
        db.commit()
        result=await create_xendit_subscription_session(settings,subscription,user)
        subscription.provider_session_id=result['session_id']
        subscription.provider_plan_id=result['plan_id']
        subscription.provider_customer_id=result['customer_id']
        subscription.checkout_url=result['checkout_url']
        subscription.checkout_expires_at=int(time.time())+25*60
        audit(db,user,'subscription_checkout_created',f"Created an Xendit hosted checkout for {plan['name']}.")
        db.commit()
        trial_message='Your first charge is scheduled after the one-month free trial.' if subscription.trial_ends_at else 'This enrollment does not include another free trial; Xendit will collect the first monthly payment now.'
        return {'checkout_url':result['checkout_url'],'message':f'Continue securely with Xendit. {trial_message} Padala will confirm activation after its signed webhook arrives.'}

    @app.post('/api/v1/billing/cancel',tags=['Billing'])
    async def cancel_billing_subscription(db:Db,user:BillingAuth):
        """Cancel a pending checkout or ask Xendit to stop future billing cycles."""
        require_sender(user)
        subscription=db.scalar(select(Subscription).where(Subscription.household_id==user.household_id))
        if subscription is None or subscription.status in {'canceled','inactive'}:
            return subscription_dict(subscription,settings)
        if not settings.xendit_checkout_ready:
            raise HTTPException(503,'Subscription cancellation is unavailable until the provider is configured. Please contact support.')
        if subscription.status=='pending':
            if not subscription.provider_session_id:
                raise HTTPException(409,'Checkout setup is still pending. Refresh billing before trying again.')
            await cancel_xendit_session(settings,subscription.provider_session_id)
            subscription.status='canceled'
            subscription.ended_at=int(time.time())
            subscription.checkout_url=''
            audit(db,user,'subscription_checkout_canceled','Canceled an unfinished Xendit subscription checkout.')
            db.commit()
            return subscription_dict(subscription,settings)
        if subscription.status=='cancellation_pending':
            return subscription_dict(subscription,settings)
        if not subscription.provider_plan_id:
            raise HTTPException(409,'The subscription does not have a provider plan to cancel. Please contact support.')
        await deactivate_xendit_plan(settings,subscription.provider_plan_id)
        subscription.status='cancellation_pending'
        subscription.cancel_requested_at=int(time.time())
        audit(db,user,'subscription_cancellation_requested','Requested Xendit cancellation of future subscription cycles.')
        db.commit()
        return subscription_dict(subscription,settings)

    @app.post('/api/v1/billing/xendit/webhook',tags=['Billing'],include_in_schema=False)
    async def xendit_webhook(request:Request,db:Db):
        """Receive signed Xendit events without trusting browser redirects.

        Xendit retries and can deliver events out of order, so the raw-payload
        digest is used for idempotency. Plan activation starts the free trial;
        only a signed successful recurring cycle continues access after it.
        """
        if not settings.xendit_webhook_token:
            raise HTTPException(503,'Billing webhook is not configured.')
        callback_token=request.headers.get('x-callback-token','')
        if not secrets.compare_digest(callback_token,settings.xendit_webhook_token):
            raise HTTPException(401,'Invalid billing webhook signature.')
        raw=await request.body()
        digest=hashlib.sha256(raw).hexdigest()
        if db.scalar(select(BillingWebhookEvent).where(BillingWebhookEvent.provider=='xendit',BillingWebhookEvent.payload_sha256==digest)):
            return {'ok':True,'duplicate':True}
        try:
            payload=json.loads(raw)
        except (UnicodeDecodeError,json.JSONDecodeError):
            raise HTTPException(400,'Invalid billing webhook payload.')
        if not isinstance(payload,dict) or not isinstance(payload.get('data'),dict) or not isinstance(payload.get('event'),str):
            raise HTTPException(400,'Invalid billing webhook payload.')
        event=BillingWebhookEvent(provider='xendit',payload_sha256=digest,event_type=payload['event'],outcome='ignored')
        db.add(event)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            return {'ok':True,'duplicate':True}
        data=payload['data']
        event_type=payload['event']
        reference=data.get('reference_id')
        plan_id=data.get('recurring_plan_id') or data.get('plan_id')
        if event_type in {'recurring.plan.activated','recurring.plan.inactivated','recurring_plan.activated','recurring_plan.inactivated'}:
            plan_id=data.get('id')
        subscription=db.scalar(select(Subscription).where(Subscription.provider_reference==reference)) if isinstance(reference,str) else None
        plan_subscription=db.scalar(select(Subscription).where(Subscription.provider_plan_id==plan_id)) if isinstance(plan_id,str) else None
        if subscription is not None and plan_subscription is not None and subscription.id!=plan_subscription.id:
            event.outcome='rejected';db.commit();return {'ok':True}
        subscription=subscription or plan_subscription
        if subscription is None:
            event.outcome='rejected' if not isinstance(reference,str) and not isinstance(plan_id,str) else 'ignored';db.commit();return {'ok':True}
        event.subscription_id=subscription.id
        try:
            if data.get('currency') not in {None,'PHP'} or (data.get('amount') is not None and amount_minor_from_xendit(data['amount'])!=subscription.amount_minor):
                raise ValueError('Provider amount mismatch.')
            session_id=data.get('payment_session_id')
            if session_id and subscription.provider_session_id and session_id!=subscription.provider_session_id:
                raise ValueError('Provider session mismatch.')
            if plan_id and subscription.provider_plan_id and plan_id!=subscription.provider_plan_id:
                raise ValueError('Provider plan mismatch.')
        except (TypeError,ValueError):
            event.outcome='rejected';db.commit();return {'ok':True}
        if data.get('customer_id') and not subscription.provider_customer_id:
            subscription.provider_customer_id=str(data['customer_id'])
        if data.get('payment_session_id') and not subscription.provider_session_id:
            subscription.provider_session_id=str(data['payment_session_id'])
        if plan_id and not subscription.provider_plan_id:
            subscription.provider_plan_id=str(plan_id)
        if event_type in {'recurring.plan.activated','recurring_plan.activated'}:
            subscription.status='active'
            subscription.checkout_url=''
            if subscription.trial_ends_at and not subscription.trial_started_at:
                subscription.trial_started_at=int(time.time())
                title='Free trial active'
                detail='Your Padala household free trial is active. Your first monthly charge is scheduled at the trial end shown in Billing.'
                audit_action='subscription_trial_activated'
                audit_detail='Xendit confirmed the subscription plan is active and the household free trial started.'
            else:
                subscription.first_payment_confirmed_at=subscription.first_payment_confirmed_at or int(time.time())
                title='Subscription active'
                detail='Your Padala household subscription is active.'
                audit_action='subscription_activated'
                audit_detail='Xendit confirmed the subscription plan is active.'
            for owner in db.scalars(select(User).where(User.household_id==subscription.household_id,User.role=='sender')):
                notify(db,settings,owner,title,detail)
            db.add(AuditEvent(household_id=subscription.household_id,actor='Padala billing',action=audit_action,detail=audit_detail))
            event.outcome='processed'
        elif event_type in {'recurring.cycle.succeeded','recurring_cycle.succeeded'}:
            if subscription.trial_ends_at and not subscription.first_payment_confirmed_at:
                subscription.first_payment_confirmed_at=int(time.time())
                for owner in db.scalars(select(User).where(User.household_id==subscription.household_id,User.role=='sender')):
                    notify(db,settings,owner,'Subscription payment confirmed','Xendit confirmed the first monthly subscription payment after the free trial.')
                db.add(AuditEvent(household_id=subscription.household_id,actor='Padala billing',action='subscription_first_payment_confirmed',detail='Xendit confirmed the first successful recurring payment after the free trial.'))
                event.outcome='processed'
        elif event_type in {'recurring.plan.inactivated','recurring_plan.inactivated'}:
            subscription.status='canceled' if subscription.cancel_requested_at else 'inactive'
            subscription.ended_at=int(time.time())
            subscription.checkout_url=''
            db.add(AuditEvent(household_id=subscription.household_id,actor='Padala billing',action='subscription_inactivated',detail='Xendit confirmed the subscription plan is inactive.'))
            event.outcome='processed'
        db.commit()
        return {'ok':True}

    @app.post('/api/v1/auth/logout',tags=['Accounts'])
    def logout(request:Request,db:Db,user:PrivacyAuth):
        db.delete(request.state.login_session);db.commit()
        response=JSONResponse({'ok':True});response.delete_cookie(COOKIE,path='/')
        return response

    @app.post('/api/v1/auth/privacy-notice',tags=['Accounts'])
    def acknowledge_privacy_notice(data:PrivacyNoticeAcknowledgement,db:Db,user:PrivacyAuth):
        if not settings.privacy_notice_acknowledgement_required:
            return {'ok':True,'version':''}
        if not secrets.compare_digest(data.privacy_notice_version,settings.privacy_notice_version):
            raise HTTPException(422,'The privacy notice has changed. Review its current version before acknowledging it.')
        user.privacy_notice_version=settings.privacy_notice_version
        user.privacy_notice_acknowledged_at=int(time.time())
        audit(db,user,'privacy_notice_acknowledged',f'Acknowledged privacy notice version {settings.privacy_notice_version}.')
        db.commit()
        return {'ok':True,'version':settings.privacy_notice_version}

    @app.post('/api/v1/auth/password',tags=['Accounts'])
    def password(data:ChangePassword,db:Db,user:Auth):
        if not check_password(data.current_password,user.password_hash):
            raise HTTPException(400,'The current password is incorrect.')
        user.password_hash=HASHER.hash(data.new_password)
        db.execute(delete(LoginSession).where(LoginSession.user_id==user.id))
        audit(db,user,'password_changed','Password changed; all sessions signed out.')
        db.commit()
        response=JSONResponse({'ok':True});response.delete_cookie(COOKIE,path='/')
        return response

    @app.post('/api/v1/auth/forgot-password',tags=['Accounts'])
    def forgot(data:EmailSchema,request:Request,db:Db):
        limit(request,'forgot-password',5)
        if not settings.smtp_host:
            raise HTTPException(503,'Email is not configured. The local administrator can use the password-reset command.')
        user=db.scalar(select(User).where(User.email==data.email))
        if user and user.is_active:
            db.execute(delete(ResetToken).where(ResetToken.user_id==user.id))
            token=secrets.token_urlsafe(32)
            db.add(ResetToken(token_hash=token_hash(token),user_id=user.id,expires_at=int(time.time())+1800))
            queue_email(db,settings,user.email,'Reset your Padala password',f'Open {settings.app_url}/?reset={token}\nThis link expires in 30 minutes. Ignore this email if you did not request it.')
            db.commit()
        return {'message':'If an account exists, a reset link has been queued for delivery.'}

    @app.post('/api/v1/auth/resend-verification',tags=['Accounts'])
    def resend_verification(data:EmailSchema,request:Request,db:Db):
        limit(request,'resend-verification',5)
        if not settings.email_verification_required:
            return {'message':'Email verification is not required for this installation.'}
        if not settings.smtp_host:
            raise HTTPException(503,'Email verification is unavailable until the administrator configures email delivery.')
        user=db.scalar(select(User).where(User.email==data.email))
        if user and user.is_active and not user.email_verified:
            queue_email_verification(db,user)
            db.commit()
        return {'message':'If an unverified account exists, a verification link has been queued for delivery.'}

    @app.post('/api/v1/auth/verify-email',tags=['Accounts'])
    def verify_email(data:VerifyEmail,request:Request,db:Db):
        limit(request,'verify-email',10)
        row=db.get(EmailVerificationToken,token_hash(data.token))
        if not row or row.used or row.expires_at<int(time.time()):
            raise HTTPException(400,'This verification link is invalid or expired.')
        changed=db.execute(update(EmailVerificationToken).where(EmailVerificationToken.token_hash==row.token_hash,EmailVerificationToken.used==False).values(used=True))
        if changed.rowcount!=1:
            raise HTTPException(400,'This verification link was already used.')
        user=db.get(User,row.user_id)
        if user is None:
            raise HTTPException(400,'This verification link is invalid or expired.')
        user.email_verified=True
        db.execute(delete(EmailVerificationToken).where(EmailVerificationToken.user_id==user.id,EmailVerificationToken.token_hash!=row.token_hash))
        audit(db,user,'email_verified','Email address verified.')
        db.commit()
        return {'message':'Email verified. You can now sign in.'}

    @app.post('/api/v1/auth/reset-password',tags=['Accounts'])
    def reset_password(data:ResetPassword,request:Request,db:Db):
        limit(request,'reset-password',10)
        row=db.get(ResetToken,token_hash(data.token))
        if not row or row.used or row.expires_at<int(time.time()):
            raise HTTPException(400,'This reset link is invalid or expired.')
        changed=db.execute(update(ResetToken).where(ResetToken.token_hash==row.token_hash,ResetToken.used==False).values(used=True))
        if changed.rowcount!=1:
            raise HTTPException(400,'This reset link was already used.')
        user=db.get(User,row.user_id)
        if user is None or not user.is_active:
            raise HTTPException(403,'Household access has been removed. Contact the household owner.')
        user.password_hash=HASHER.hash(data.password)
        db.execute(delete(LoginSession).where(LoginSession.user_id==user.id))
        audit(db,user,'password_reset','Password reset; all sessions signed out.')
        db.commit()
        return {'ok':True}

    @app.patch('/api/v1/auth/preferences',tags=['Accounts'])
    def preferences(data:Preferences,db:Db,user:Auth):
        user.email_notifications=data.email_notifications;db.commit()
        return user_dict(user)

    @app.get('/api/v1/household',tags=['Household'])
    def household(db:Db,user:Auth):
        house=db.get(Household,user.household_id)
        members=db.scalars(select(User).where(User.household_id==house.id).order_by(User.created_at)).all()
        return {'id':house.id,'name':house.name,'members':[user_dict(u) for u in members]}

    def member_for_access_change(member_id: str, db: Session, user: User) -> User:
        require_sender(user)
        member=owned(db,User,member_id,user)
        if member.id==user.id or member.role=='sender':
            raise HTTPException(400,'The household owner cannot remove their own access.')
        return member

    @app.post('/api/v1/household/members/{member_id}/revoke',tags=['Household'])
    def revoke_member_access(member_id:str,db:Db,user:Auth):
        """End a member's household access without erasing shared history."""
        member=member_for_access_change(member_id,db,user)
        if not member.is_active:
            raise HTTPException(400,'This member already has no household access.')
        member.is_active=False
        member.access_revoked_at=int(time.time())
        db.execute(delete(LoginSession).where(LoginSession.user_id==member.id))
        db.execute(delete(ResetToken).where(ResetToken.user_id==member.id))
        db.execute(delete(EmailVerificationToken).where(EmailVerificationToken.user_id==member.id))
        audit(db,user,'member_access_revoked',f'Revoked household access for {member.name}.')
        db.commit()
        return {'member':user_dict(member),'message':'Household access removed. Existing shared records remain in the household history.'}

    @app.post('/api/v1/household/members/{member_id}/restore',tags=['Household'])
    def restore_member_access(member_id:str,db:Db,user:Auth):
        """Restore a former member's existing account; do not create a session."""
        member=member_for_access_change(member_id,db,user)
        if member.is_active:
            raise HTTPException(400,'This member already has household access.')
        require_household_capacity(db,user.household_id,include_pending=False)
        member.is_active=True
        member.access_revoked_at=0
        audit(db,user,'member_access_restored',f'Restored household access for {member.name}.')
        notify(db,settings,member,'Household access restored','The household owner restored your access. Sign in to view the shared records.')
        db.commit()
        return {'member':user_dict(member),'message':'Household access restored. The member can sign in with their existing account.'}

    @app.post('/api/v1/invitations',tags=['Household'],status_code=201)
    def invite(data:Invite,request:Request,db:Db,user:Auth):
        require_sender(user);limit(request,'invitations',20)
        if db.scalar(select(User).where(User.email==data.email)):
            raise HTTPException(409,'This email is already registered.')
        now=int(time.time())
        if db.scalar(select(Invitation).where(Invitation.household_id==user.household_id,Invitation.email==data.email,Invitation.used==False,Invitation.expires_at>=now)):
            raise HTTPException(409,'An active invitation already exists for this email. Replace its link from Pending invitations if needed.')
        require_household_capacity(db,user.household_id,include_pending=True)
        token=secrets.token_urlsafe(32)
        db.add(Invitation(token_hash=token_hash(token),household_id=user.household_id,email=data.email,name=data.name,expires_at=now+7*86400))
        link=f'{settings.app_url}/?invite={token}'
        queue_email(db,settings,data.email,'Your Padala household invitation',f'{user.name} invited you to a shared household.\nOpen {link}\nThe link expires in 7 days. Only accept an invitation from someone you know.')
        audit(db,user,'member_invited',f'Invited {data.name}.');db.commit()
        return {'link':link,'email_queued':bool(settings.smtp_host),'expires_in_days':7}

    @app.get('/api/v1/invitations',tags=['Household'])
    def pending_invitations(db:Db,user:Auth):
        """List pending invitation metadata without disclosing bearer tokens."""
        require_sender(user)
        rows=db.scalars(select(Invitation).where(Invitation.household_id==user.household_id,Invitation.used==False,Invitation.expires_at>=int(time.time())).order_by(Invitation.expires_at)).all()
        return [{'name':row.name,'email':row.email,'expires_at':row.expires_at} for row in rows]

    @app.post('/api/v1/invitations/replace',tags=['Household'])
    def replace_invitation(data:ReplaceInvitation,request:Request,db:Db,user:Auth):
        """Invalidate one pending invitation and issue a new copyable link."""
        require_sender(user);limit(request,'invitations',20)
        now=int(time.time())
        current=db.scalar(select(Invitation).where(Invitation.household_id==user.household_id,Invitation.email==data.email,Invitation.used==False,Invitation.expires_at>=now))
        if current is None:
            raise HTTPException(404,'No active invitation was found for this email.')
        # The original random token is stored only as a hash. Delete its record
        # before issuing a replacement, so it cannot be accepted after a new
        # link is copied. The audit trail records the replacement action.
        db.delete(current);db.flush()
        token=secrets.token_urlsafe(32)
        replacement=Invitation(token_hash=token_hash(token),household_id=user.household_id,email=current.email,name=current.name,expires_at=now+7*86400)
        db.add(replacement)
        link=f'{settings.app_url}/?invite={token}'
        queue_email(db,settings,current.email,'Your replacement Padala invitation',f'{user.name} replaced a household invitation link.\nOpen {link}\nThe link expires in 7 days. Only accept an invitation from someone you know.')
        audit(db,user,'invitation_link_replaced',f'Replaced the pending invitation link for {current.name}.')
        db.commit()
        return {'link':link,'email_queued':bool(settings.smtp_host),'expires_in_days':7}

    @app.post('/api/v1/invitations/revoke',tags=['Household'])
    def revoke_invitation(data:RevokeInvitation,request:Request,db:Db,user:Auth):
        """Invalidate a pending invitation link at the household owner's request."""
        require_sender(user);limit(request,'invitations',20)
        invitation=db.scalar(select(Invitation).where(Invitation.household_id==user.household_id,Invitation.email==data.email,Invitation.used==False,Invitation.expires_at>=int(time.time())))
        if invitation is None:
            raise HTTPException(404,'No active invitation was found for this email.')
        name=invitation.name
        db.delete(invitation)
        audit(db,user,'invitation_revoked',f'Revoked the pending invitation for {name}.')
        db.commit()
        return {'message':f'Invitation for {name} was revoked. The link no longer works.'}

    @app.get('/api/v1/invitations/{token}',tags=['Household'])
    def invitation_info(token:str,db:Db):
        inv=db.get(Invitation,token_hash(token))
        if not inv or inv.used or inv.expires_at<int(time.time()):
            raise HTTPException(404,'Invitation expired or unavailable.')
        return {'name':inv.name,'email':inv.email,'household_name':db.get(Household,inv.household_id).name}

    @app.post('/api/v1/invitations/accept',tags=['Household'])
    def accept_invitation(data:AcceptInvite,request:Request,db:Db):
        limit(request,'accept-invitation',10)
        inv=db.get(Invitation,token_hash(data.token))
        if not inv or inv.used or inv.expires_at<int(time.time()):
            raise HTTPException(400,'Invitation expired or unavailable.')
        member_limit=subscription_member_limit(db,inv.household_id)
        if member_limit is not None and active_member_count(db,inv.household_id)+pending_invitation_count(db,inv.household_id)>member_limit:
            raise HTTPException(409, f'The selected household subscription allows up to {member_limit} active members. Ask the household owner to remove access or choose Padala Family.')
        changed=db.execute(update(Invitation).where(Invitation.token_hash==inv.token_hash,Invitation.used==False).values(used=True))
        if changed.rowcount!=1:
            raise HTTPException(400,'Invitation already used.')
        privacy_version,privacy_acknowledged_at=privacy_notice_acknowledgement(data.privacy_notice_version)
        user=User(name=data.name,email=inv.email,household_id=inv.household_id,role='member',password_hash=HASHER.hash(data.password),email_verified=not settings.email_verification_required,privacy_notice_version=privacy_version,privacy_notice_acknowledged_at=privacy_acknowledged_at)
        db.add(user);db.flush();audit(db,user,'member_joined','Joined the household.')
        if settings.email_verification_required:
            queue_email_verification(db,user)
            db.commit()
            return {'verification_required':True,'message':'Check your email for a verification link before signing in.'}
        response=JSONResponse({'ok':True});new_session(db,user,response,settings);db.commit()
        return response

    @app.get('/api/v1/remittances',tags=['Remittances'])
    def list_remittances(db:Db,user:Auth):
        rows=db.scalars(select(Remittance).where(Remittance.household_id==user.household_id).order_by(Remittance.received_on.desc(),Remittance.created_at.desc())).all()
        return [remittance_dict(db,r) for r in rows]

    @app.post('/api/v1/remittances',tags=['Remittances'],status_code=201)
    def create_remittance(data:RemittanceCreate,db:Db,user:Auth):
        require_sender(user)
        members={u.id for u in db.scalars(select(User).where(User.household_id==user.household_id,User.is_active==True))}
        if data.recipient_id not in members or any(a.assigned_to not in members for a in data.allocations):
            raise HTTPException(400,'Choose recipients and assignees with active household access.')
        r=Remittance(household_id=user.household_id,title=data.title,amount_minor=data.amount_minor,
            received_on=data.received_on.isoformat(),recipient_id=data.recipient_id,source_currency=data.source_currency,source_amount=data.source_amount)
        db.add(r);db.flush()
        for a in data.allocations:
            db.add(Allocation(remittance_id=r.id,name=a.name,kind=a.kind,amount_minor=a.amount_minor,assigned_to=a.assigned_to,due_on=a.due_on.isoformat() if a.due_on else ''))
        audit(db,user,'remittance_created',f'Created {r.title} and its allocation plan.',r.id)
        recipient=db.get(User,r.recipient_id)
        if recipient.id!=user.id:
            notify(db,settings,recipient,'A new padala plan is ready',r.title,r.id)
        db.commit()
        return remittance_dict(db,r,True)

    @app.get('/api/v1/remittances/{rid}',tags=['Remittances'])
    def get_remittance(rid:str,db:Db,user:Auth):
        return remittance_dict(db,owned(db,Remittance,rid,user),True)

    @app.post('/api/v1/remittances/{rid}/confirm',tags=['Remittances'])
    def confirm(rid:str,db:Db,user:Auth):
        r=owned(db,Remittance,rid,user)
        if user.id!=r.recipient_id:
            raise HTTPException(403,'Only the designated recipient may confirm receiving the money.')
        if not r.confirmed:
            r.confirmed=True;audit(db,user,'receipt_of_funds_confirmed','Recipient confirmed receiving the money. Self-reported, not bank-verified.',rid)
            for sender_user in db.scalars(select(User).where(User.household_id==user.household_id,User.role=='sender')):
                notify(db,settings,sender_user,'Money received',f'{user.name} confirmed receiving {r.title}.',rid)
            db.commit()
        return remittance_dict(db,r,True)

    @app.post('/api/v1/uploads',tags=['Receipts'],status_code=201)
    async def upload(request:Request,db:Db,user:Auth,file:UploadFile=File(...)):
        limit(request,'upload',100)
        data=await file.read(settings.max_upload_bytes+1)
        mime,extension=inspect_file(data,file.filename or 'receipt',settings)
        scan_file(data,settings)
        digest=hashlib.sha256(data).hexdigest()
        existing=db.scalar(select(Upload).where(Upload.household_id==user.household_id,Upload.sha256==digest))
        if existing:
            # Reuse unsubmitted drafts belonging to the same uploader; never duplicate an expense.
            used=db.scalar(select(Evidence).where(Evidence.upload_id==existing.id))
            if existing.uploader_id==user.id and not used:
                return upload_dict(existing)
            raise HTTPException(409,'This exact file is already in the household. Reuse the existing receipt, not a second expense.')
        identifier=uid();storage=identifier+extension
        safe_name=Path((file.filename or 'receipt').replace('\\','/')).name[:150]
        target=settings.uploads_dir/storage
        target.write_bytes(data)
        try:
            row=Upload(id=identifier,household_id=user.household_id,uploader_id=user.id,name=safe_name,mime=mime,
                       sha256=digest,size=len(data),storage_name=storage)
            db.add(row);db.commit()
        except Exception:
            target.unlink(missing_ok=True);raise
        return upload_dict(row)

    @app.get('/api/v1/uploads/{upload_id}/download',tags=['Receipts'])
    def download(upload_id:str,db:Db,user:Auth):
        row=owned(db,Upload,upload_id,user)
        evidence=db.scalar(select(Evidence).where(Evidence.upload_id==row.id))
        if row.uploader_id!=user.id and evidence is None:
            raise HTTPException(404,'File not found.')
        path=settings.uploads_dir/row.storage_name
        if not path.is_file():
            raise HTTPException(404,'The stored file is unavailable. Check your data backup.')
        return FileResponse(path,media_type=row.mime,filename=row.name,content_disposition_type='attachment')

    @app.post('/api/v1/uploads/{upload_id}/extract',tags=['Integrations'])
    async def extract(upload_id:str,data:ExtractionRequest,request:Request,db:Db,user:Auth):
        app.state.limiter.hit('ocr:'+user.id,20,3600)
        row=owned(db,Upload,upload_id,user)
        if row.uploader_id!=user.id:
            raise HTTPException(403,'Only the uploader may send this draft to the extraction provider.')
        if row.extraction:
            return row.extraction
        path=settings.uploads_dir/row.storage_name
        if not path.is_file():
            raise HTTPException(404,'File unavailable.')
        result=await extract_azure(path.read_bytes(),row.mime,settings)
        row.extraction=result
        audit(db,user,'extraction_requested','Uploader consented to Azure processing. Text extraction only; no authentication.')
        db.commit()
        return result

    @app.get('/api/v1/evidence',tags=['Receipts'])
    def list_evidence(db:Db,user:Auth):
        return [evidence_dict(db,e) for e in db.scalars(select(Evidence).where(Evidence.household_id==user.household_id).order_by(Evidence.created_at.desc()))]

    @app.post('/api/v1/evidence',tags=['Receipts'],status_code=201)
    def submit_evidence(data:EvidenceCreate,db:Db,user:Auth):
        remittance=owned(db,Remittance,data.remittance_id,user)
        upload=owned(db,Upload,data.upload_id,user) if data.upload_id else None
        if upload and upload.uploader_id!=user.id:
            raise HTTPException(403,'Use a file you uploaded yourself.')
        if upload and db.scalar(select(Evidence).where(Evidence.upload_id==upload.id)):
            raise HTTPException(409,'This document already supports an evidence record.')
        flags=[]
        if data.occurred_on>date.today()+timedelta(days=1):
            flags.append('The transaction date is in the future. Please clarify the date.')
        if data.occurred_on<date.fromisoformat(remittance.received_on):
            flags.append('The transaction predates this padala. Explain any reimbursement.')
        if data.reference and db.scalar(select(Evidence).where(Evidence.household_id==user.household_id,func.lower(Evidence.reference)==data.reference.lower(),Evidence.status!='voided')):
            flags.append('This reference appears on another household record. Check for a duplicate.')
        for line in data.lines:
            a=db.get(Allocation,line.allocation_id)
            if not a or a.remittance_id!=remittance.id:
                raise HTTPException(400,'Each split must belong to this padala.')
            if user.role!='sender' and a.assigned_to!=user.id:
                raise HTTPException(403,'Submit evidence only for allocations assigned to you.')
            used=db.scalar(select(func.coalesce(func.sum(EvidenceLine.amount_minor),0)).join(Evidence,Evidence.id==EvidenceLine.evidence_id).where(EvidenceLine.allocation_id==a.id,Evidence.status!='voided')) or 0
            if used+line.amount_minor>a.amount_minor:
                flags.append(f'{a.name}: submitted records exceed this allocation. Review the plan and amount.')
        if upload and upload.extraction:
            total=upload.extraction.get('amount_minor')
            if total is not None and total!=data.amount_minor:
                flags.append('The entered amount differs from the extracted total. Review the original document.')
            currency=upload.extraction.get('currency')
            if currency and currency!='PHP':
                flags.append('The extracted currency is not PHP. Explain the conversion; the allocation ledger is in PHP.')
        e=Evidence(household_id=user.household_id,remittance_id=remittance.id,uploader_id=user.id,
                   upload_id=upload.id if upload else None,merchant=data.merchant,amount_minor=data.amount_minor,
                   occurred_on=data.occurred_on.isoformat(),reference=data.reference,note=data.note,checks=flags)
        db.add(e);db.flush()
        for l in data.lines:
            db.add(EvidenceLine(evidence_id=e.id,allocation_id=l.allocation_id,amount_minor=l.amount_minor))
        audit(db,user,'evidence_submitted',f'Submitted evidence for {e.merchant}.',remittance.id)
        for sender_user in db.scalars(select(User).where(User.household_id==user.household_id,User.role=='sender')):
            if sender_user.id!=user.id:
                notify(db,settings,sender_user,'New evidence to review',f'{user.name} submitted {e.merchant}.',remittance.id)
        db.commit()
        return evidence_dict(db,e)

    @app.post('/api/v1/evidence/{eid}/review',tags=['Receipts'])
    def review(eid:str,data:Review,db:Db,user:Auth):
        require_sender(user)
        e=owned(db,Evidence,eid,user);require_version(e,data.expected_version)
        if e.status=='voided':
            raise HTTPException(400,'A voided record cannot be accepted.')
        e.status=data.status;e.review_note=data.note
        audit(db,user,'evidence_reviewed',f'{e.merchant}: {data.status}. {data.note}',e.remittance_id)
        notify(db,settings,db.get(User,e.uploader_id),'Receipt review updated',f'{e.merchant}: {data.status}.',e.remittance_id)
        db.commit()
        return evidence_dict(db,e)

    @app.post('/api/v1/evidence/{eid}/respond',tags=['Receipts'])
    def respond(eid:str,data:Note,db:Db,user:Auth):
        e=owned(db,Evidence,eid,user);require_version(e,data.expected_version)
        if e.uploader_id!=user.id or e.status!='clarification':
            raise HTTPException(403,'Only the uploader can respond to an outstanding clarification.')
        e.note=(e.note+'\n\nClarification: '+data.note).strip();e.status='pending'
        audit(db,user,'clarification_added',data.note,e.remittance_id)
        for recipient in db.scalars(select(User).where(User.household_id==user.household_id,User.role=='sender')):
            notify(db,settings,recipient,'Clarification received',e.merchant,e.remittance_id)
        db.commit();return evidence_dict(db,e)

    @app.post('/api/v1/evidence/{eid}/void',tags=['Receipts'])
    def void(eid:str,data:Note,db:Db,user:Auth):
        e=owned(db,Evidence,eid,user);require_version(e,data.expected_version)
        if user.role!='sender' and (e.uploader_id!=user.id or e.status=='accepted'):
            raise HTTPException(403,'Only the OFW can void an accepted record.')
        if e.status=='voided':
            raise HTTPException(400,'This record is already voided.')
        e.status='voided';e.review_note=data.note
        audit(db,user,'evidence_voided',f'{e.merchant}: {data.note}',e.remittance_id)
        db.commit();return evidence_dict(db,e)

    @app.get('/api/v1/notifications',tags=['Notifications'])
    def notifications(db:Db,user:Auth):
        rows=db.scalars(select(Notification).where(Notification.user_id==user.id).order_by(Notification.created_at.desc(),Notification.id).limit(100))
        return [{'id':n.id,'title':n.title,'detail':n.detail,'remittance_id':n.remittance_id,'is_read':n.is_read,'created_at':n.created_at} for n in rows]

    @app.post('/api/v1/notifications/read',tags=['Notifications'])
    def read_all(db:Db,user:Auth):
        db.execute(update(Notification).where(Notification.user_id==user.id).values(is_read=True));db.commit()
        return {'ok':True}

    @app.get('/api/v1/activity',tags=['Reports'])
    def activity(db:Db,user:Auth):
        return [event_dict(e) for e in db.scalars(select(AuditEvent).where(AuditEvent.household_id==user.household_id).order_by(AuditEvent.created_at.desc(),AuditEvent.id).limit(100))]

    @app.get('/api/v1/export',tags=['Reports'])
    def export(db:Db,user:Auth,format:str='json'):
        records=[remittance_dict(db,r,True) for r in db.scalars(select(Remittance).where(Remittance.household_id==user.household_id).order_by(Remittance.received_on))]
        if format=='json':
            content=json.dumps({'schema_version':1,'currency':'PHP','notice':'Amounts are integer centavos. Evidence is not bank verification. Savings contributions are not current balances.','remittances':records},ensure_ascii=False,indent=2)
            return Response(content,media_type='application/json',headers={'Content-Disposition':'attachment; filename="padala-records.json"'})
        if format!='csv':
            raise HTTPException(400,'Choose json or csv.')
        out=io.StringIO();w=csv.writer(out)
        w.writerow(['Padala','Allocation','Kind','Planned PHP','Recorded PHP','OFW accepted PHP','Provider confirmation'])
        def safe(s):
            # Prevent spreadsheet formula injection, including leading whitespace.
            text=str(s)
            return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
        for r in records:
            for a in r['allocations']:
                w.writerow([safe(r['title']),safe(a['name']),a['kind'],f"{a['amount_minor']/100:.2f}",f"{a['recorded_minor']/100:.2f}",f"{a['accepted_minor']/100:.2f}",'Not connected'])
        return Response('\ufeff'+out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="padala-summary.csv"'})

    return app

app=create_app()
