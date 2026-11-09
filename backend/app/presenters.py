from __future__ import annotations
import time
from sqlalchemy import select
from .models import *
from .billing import subscription_has_access

def user_dict(u):
    return {'id':u.id,'name':u.name,'email':u.email,'role':u.role,'email_verified':u.email_verified,
            'email_notifications':u.email_notifications,'is_active':u.is_active}

def upload_dict(u):
    return {'id':u.id,'name':u.name,'mime':u.mime,'size':u.size,'extraction':u.extraction,
            'download_url':f'/api/v1/uploads/{u.id}/download',
            'preview_url':f'/api/v1/uploads/{u.id}/preview'}

def evidence_dict(db, e):
    lines = db.scalars(select(EvidenceLine).where(EvidenceLine.evidence_id==e.id)).all()
    upload = db.get(Upload,e.upload_id) if e.upload_id else None
    uploader = db.get(User,e.uploader_id)
    return {'id':e.id,'remittance_id':e.remittance_id,'uploader_id':e.uploader_id,
            'uploader_name':uploader.name if uploader else 'Member','merchant':e.merchant,
            'amount_minor':e.amount_minor,'occurred_on':e.occurred_on,'reference':e.reference,
            'note':e.note,'status':e.status,'review_note':e.review_note,'checks':e.checks,
            'version':e.version,'created_at':e.created_at,'provider_confirmation':'not_connected',
            'document_status':'declared_without_receipt' if not e.upload_id else ('needs_attention' if e.checks else 'checks_completed'),
            'upload':upload_dict(upload) if upload else None,
            'lines':[{'allocation_id':l.allocation_id,'amount_minor':l.amount_minor} for l in lines]}

def remittance_dict(db,r,detail=False):
    allocations = db.scalars(select(Allocation).where(Allocation.remittance_id==r.id)).all()
    evidence = db.scalars(select(Evidence).where(Evidence.remittance_id==r.id).order_by(Evidence.created_at.desc(),Evidence.id)).all()
    ids = [e.id for e in evidence]
    lines = db.scalars(select(EvidenceLine).where(EvidenceLine.evidence_id.in_(ids))).all() if ids else []
    emap = {e.id:e for e in evidence}
    allocation_data=[]
    for a in allocations:
        recorded=sum(l.amount_minor for l in lines if l.allocation_id==a.id and emap[l.evidence_id].status!='voided')
        accepted=sum(l.amount_minor for l in lines if l.allocation_id==a.id and emap[l.evidence_id].status=='accepted')
        allocation_data.append({'id':a.id,'name':a.name,'kind':a.kind,'amount_minor':a.amount_minor,
            'assigned_to':a.assigned_to,'due_on':a.due_on,'recorded_minor':recorded,'accepted_minor':accepted})
    recorded=sum(a['recorded_minor'] for a in allocation_data)
    result={'id':r.id,'title':r.title,'amount_minor':r.amount_minor,'received_on':r.received_on,
        'recipient_id':r.recipient_id,'source_currency':r.source_currency,'source_amount':r.source_amount,
        'confirmed':r.confirmed,'created_at':r.created_at,'allocations':allocation_data,
        'recorded_minor':recorded,'remaining_minor':max(0,r.amount_minor-recorded),
        'accepted_minor':sum(a['accepted_minor'] for a in allocation_data),
        'savings_contributions_minor':sum(a['recorded_minor'] for a in allocation_data if a['kind']=='savings'),
        'pending_count':sum(e.status=='pending' for e in evidence), 'evidence_count':len(evidence)}
    if detail:
        result['evidence']=[evidence_dict(db,e) for e in evidence]
        result['activity']=[event_dict(e) for e in db.scalars(select(AuditEvent).where(AuditEvent.remittance_id==r.id).order_by(AuditEvent.created_at.desc(),AuditEvent.id).limit(100))]
    return result

def event_dict(e):
    return {'id':e.id,'actor':e.actor,'action':e.action,'detail':e.detail,'remittance_id':e.remittance_id,'created_at':e.created_at}


def subscription_dict(subscription, settings):
    """Customer-safe billing state; never expose checkout URLs or provider keys."""
    now = int(time.time())
    plans = [
        {
            'code': plan['code'],
            'name': plan['name'],
            'amount_minor': plan['amount_minor'] if settings.billing_enabled else 0,
            'currency': plan['currency'],
            'interval': plan['interval'],
            'max_members': plan['max_members'],
            'description': plan['description'],
        }
        for plan in settings.billing_plans
    ]
    in_trial = bool(subscription and subscription.trial_ends_at and not subscription.first_payment_confirmed_at and subscription.trial_ends_at > now)
    return {
        'provider': 'xendit' if settings.billing_enabled else '',
        'checkout_available': settings.xendit_checkout_ready,
        'enforcement_enabled': settings.billing_enforcement_enabled,
        'plans': plans,
        'trial': {'months': settings.billing_trial_months, 'enabled': settings.billing_enabled and settings.billing_catalog_configured},
        'terms': {
            'published': settings.billing_terms_published,
            'version': settings.billing_terms_version if settings.billing_terms_published else '',
            'effective_date': settings.billing_terms_effective_date if settings.billing_terms_published else '',
            'support_email': settings.billing_support_email if settings.billing_terms_published else '',
            'refund_summary': settings.billing_refund_summary if settings.billing_terms_published else '',
            'cancellation_summary': settings.billing_cancellation_summary if settings.billing_terms_published else '',
            'tax_summary': settings.billing_tax_summary if settings.billing_terms_published else '',
        },
        'subscription': None if subscription is None else {
            'status': subscription.status,
            'plan_code': subscription.plan_code,
            'amount_minor': subscription.amount_minor,
            'currency': subscription.currency,
            'trial_ends_at': subscription.trial_ends_at,
            'trial_started_at': subscription.trial_started_at,
            'first_payment_confirmed_at': subscription.first_payment_confirmed_at,
            'in_trial': in_trial,
            'access_active': subscription_has_access(subscription, now),
            'cancel_requested_at': subscription.cancel_requested_at,
            'ended_at': subscription.ended_at,
            'created_at': subscription.created_at,
        },
    }
