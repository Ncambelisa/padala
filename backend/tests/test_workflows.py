import io
import json
import time
import pytest
from PIL import Image
from sqlalchemy import select
from app.models import User, ResetToken, EmailOutbox, EmailVerificationToken, Upload
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from app.security import token_hash
from .conftest import register,login,member,create_padala,evidence_body,PASSWORD


def png_bytes(color='white'):
    out=io.BytesIO();Image.new('RGB',(32,32),color).save(out,format='PNG');return out.getvalue()

def family_padala(client,amount=300000):
    """Create a plan as the OFW, then leave the family member signed in."""
    owner=register(client)
    family,_=member(client)
    login(client,owner['email'])
    remittance=create_padala(client,family['id'],amount)
    login(client,family['email'])
    return owner,family,remittance

def test_health(client):
    assert client.get('/api/v1/health').json()['status']=='ok'

def test_config_truthful(client):
    c=client.get('/api/v1/config').json()
    assert c['bank_confirmation'] is False and c['ocr_configured'] is False
    assert c['privacy_notice']['published'] is False
    assert c['privacy_notice']['acknowledgement_required'] is False

def test_config_exposes_a_complete_privacy_notice_only_when_configured(tmp_path):
    settings=Settings(data_dir=tmp_path,
        privacy_controller_name='Padala Pilot Operator',privacy_controller_address='Manila, Philippines',
        privacy_contact_email='privacy@example.test',privacy_notice_version='1.0',
        privacy_notice_effective_date='2026-11-03',privacy_legal_basis_summary='Pilot-service provision.',
        privacy_retention_summary='Approved pilot-retention schedule.',privacy_processors_summary='Named pilot processors.')
    with TestClient(create_app(settings)) as configured_client:
        notice=configured_client.get('/api/v1/config').json()['privacy_notice']
    assert notice == {'published':True,'acknowledgement_required':True,'controller_name':'Padala Pilot Operator',
        'controller_address':'Manila, Philippines','contact_email':'privacy@example.test','version':'1.0',
        'effective_date':'2026-11-03','legal_basis_summary':'Pilot-service provision.',
        'retention_summary':'Approved pilot-retention schedule.','processors_summary':'Named pilot processors.'}

def test_published_privacy_notice_must_be_acknowledged_before_household_access(tmp_path):
    settings=Settings(data_dir=tmp_path,
        privacy_controller_name='Padala Pilot Operator',privacy_controller_address='Manila, Philippines',
        privacy_contact_email='privacy@example.test',privacy_notice_version='1.0',
        privacy_notice_effective_date='2026-11-03',privacy_legal_basis_summary='Pilot-service provision.',
        privacy_retention_summary='Approved pilot-retention schedule.',privacy_processors_summary='Named pilot processors.')
    with TestClient(create_app(settings)) as privacy_client:
        body={'name':'Private Owner','email':'private@example.test','household_name':'Private family','password':PASSWORD}
        assert privacy_client.post('/api/v1/auth/register',json=body).status_code==422
        registered=privacy_client.post('/api/v1/auth/register',json={**body,'privacy_notice_version':'1.0'})
        assert registered.status_code==201,registered.text
        privacy_client.headers['X-CSRF-Token']=registered.json()['csrf']
        assert privacy_client.get('/api/v1/auth/me').json()['privacy_notice_acknowledgement_required'] is False
        settings.privacy_notice_version='2.0'
        assert privacy_client.get('/api/v1/remittances').status_code==428
        assert privacy_client.get('/api/v1/auth/me').json()['privacy_notice_acknowledgement_required'] is True
        assert privacy_client.post('/api/v1/auth/privacy-notice',json={'privacy_notice_version':'1.0'}).status_code==422
        assert privacy_client.post('/api/v1/auth/privacy-notice',json={'privacy_notice_version':'2.0'}).json()['version']=='2.0'
        assert privacy_client.get('/api/v1/remittances').status_code==200

def test_unauthenticated(client):
    assert client.get('/api/v1/remittances').status_code==401

def test_registration_and_cookie(client):
    user=register(client)
    assert user['role']=='sender'
    me=client.get('/api/v1/auth/me')
    assert me.json()['user']['email']=='owner@example.test'
    assert 'password_hash' not in me.text

def test_http_only_cookie(client):
    r=client.post('/api/v1/auth/register',json={'name':'A','email':'a@b.test','household_name':'A','password':PASSWORD})
    assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=lax' in r.headers['set-cookie']

def test_csrf_enforced(client):
    register(client);client.headers.pop('X-CSRF-Token')
    assert client.post('/api/v1/notifications/read').status_code==403

def test_cross_origin_blocked(client):
    register(client)
    assert client.post('/api/v1/notifications/read',headers={'Origin':'https://untrusted.invalid'}).status_code==403

def test_wrong_login(client):
    register(client)
    assert client.post('/api/v1/auth/login',json={'email':'owner@example.test','password':'wrong'}).status_code==401

def test_duplicate_email(client):
    register(client)
    assert client.post('/api/v1/auth/register',json={'name':'A','email':'owner@example.test','household_name':'A','password':PASSWORD}).status_code==409

def test_logout_revokes_session(client):
    register(client);assert client.post('/api/v1/auth/logout').status_code==200
    assert client.get('/api/v1/auth/me').status_code==401

def test_password_change(client):
    register(client)
    assert client.post('/api/v1/auth/password',json={'current_password':PASSWORD,'new_password':'ChangedPass!1234'}).status_code==200
    assert client.get('/api/v1/auth/me').status_code==401
    login(client,'owner@example.test','ChangedPass!1234')

def test_invite_is_single_use(client):
    register(client);user,token=member(client)
    assert user['role']=='member'
    assert client.post('/api/v1/invitations/accept',json={'token':token,'name':'Replay','password':PASSWORD}).status_code==400

def test_sender_can_review_pending_invitations_and_replace_a_lost_link(client):
    register(client)
    created=client.post('/api/v1/invitations',json={'name':'Family','email':'family@example.test'})
    assert created.status_code==201,created.text
    first_token=created.json()['link'].split('invite=')[1]

    pending=client.get('/api/v1/invitations')
    assert pending.status_code==200,pending.text
    assert pending.json()==[{'name':'Family','email':'family@example.test','expires_at':pending.json()[0]['expires_at']}]
    assert 'link' not in pending.text and first_token not in pending.text
    assert client.post('/api/v1/invitations',json={'name':'Family','email':'family@example.test'}).status_code==409

    replacement=client.post('/api/v1/invitations/replace',json={'email':'family@example.test'})
    assert replacement.status_code==200,replacement.text
    second_token=replacement.json()['link'].split('invite=')[1]
    assert second_token != first_token
    assert client.get(f'/api/v1/invitations/{first_token}').status_code==404
    assert client.get(f'/api/v1/invitations/{second_token}').status_code==200
    assert client.get('/api/v1/invitations').json()[0]['email']=='family@example.test'
    revoked=client.post('/api/v1/invitations/revoke',json={'email':'family@example.test'})
    assert revoked.status_code==200,revoked.text
    assert client.get(f'/api/v1/invitations/{second_token}').status_code==404
    assert client.get('/api/v1/invitations').json()==[]
    assert client.post('/api/v1/invitations',json={'name':'Family','email':'family@example.test'}).status_code==201

def test_member_cannot_invite(client):
    register(client);member(client)
    assert client.post('/api/v1/invitations',json={'name':'Other','email':'new@example.test'}).status_code==403

def test_sender_can_revoke_and_restore_member_access(client):
    owner=register(client)
    family,_=member(client)
    former_session=client.cookies.get('padala_session')
    former_csrf=client.headers['X-CSRF-Token']
    login(client,owner['email'])
    existing=create_padala(client,family['id'])

    revoked=client.post(f"/api/v1/household/members/{family['id']}/revoke")
    assert revoked.status_code==200,revoked.text
    assert revoked.json()['member']['is_active'] is False
    assert any(row['id']==family['id'] and row['is_active'] is False for row in client.get('/api/v1/household').json()['members'])
    assert client.get(f"/api/v1/remittances/{existing['id']}").status_code==200

    inactive_plan={'title':'Inactive recipient','amount_minor':1000,'received_on':'2026-10-02','recipient_id':family['id'],
                   'allocations':[{'name':'Food','amount_minor':1000,'assigned_to':family['id']}]}
    assert client.post('/api/v1/remittances',json=inactive_plan).status_code==400

    client.cookies.set('padala_session',former_session,domain='testserver.local',path='/')
    client.headers['X-CSRF-Token']=former_csrf
    assert client.get('/api/v1/auth/me').status_code==401
    assert client.post('/api/v1/auth/login',json={'email':family['email'],'password':PASSWORD}).status_code==403

    login(client,owner['email'])
    restored=client.post(f"/api/v1/household/members/{family['id']}/restore")
    assert restored.status_code==200,restored.text
    assert restored.json()['member']['is_active'] is True
    assert client.post('/api/v1/auth/login',json={'email':family['email'],'password':PASSWORD}).status_code==200

def test_only_sender_can_change_member_access_and_owner_cannot_remove_self(client):
    owner=register(client)
    family,_=member(client)
    assert client.post(f"/api/v1/household/members/{family['id']}/revoke").status_code==403
    login(client,owner['email'])
    assert client.post(f"/api/v1/household/members/{owner['id']}/revoke").status_code==400

def test_invalid_invite(client):
    assert client.get('/api/v1/invitations/invalid').status_code==404

def test_plan_total_enforced(client):
    user=register(client)
    body={'title':'Wrong sum','amount_minor':1000,'received_on':'2026-10-01','recipient_id':user['id'],'allocations':[{'name':'Food','amount_minor':999,'assigned_to':user['id']}]}
    assert client.post('/api/v1/remittances',json=body).status_code==422

@pytest.mark.parametrize('amount',[1.5,0,-1,'100',True,1000000001])
def test_invalid_money(client,amount):
    u=register(client)
    assert client.post('/api/v1/remittances',json={'title':'Invalid','amount_minor':amount,'received_on':'2026-10-01','recipient_id':u['id'],'allocations':[{'name':'Food','amount_minor':amount,'assigned_to':u['id']}]}).status_code==422

def test_member_cannot_create_plan(client):
    register(client);u,_=member(client)
    assert client.post('/api/v1/remittances',json={'title':'Forbidden','amount_minor':1000,'received_on':'2026-10-01','recipient_id':u['id'],'allocations':[{'name':'Food','amount_minor':1000,'assigned_to':u['id']}]}).status_code==403

def test_tenant_remittance_isolation(client):
    u=register(client);r=create_padala(client,u['id'])
    register(client,'other@example.test')
    assert client.get('/api/v1/remittances/'+r['id']).status_code==404
    assert client.get('/api/v1/remittances').json()==[]

def test_foreign_assignee_rejected(client):
    u=register(client);r=create_padala(client,u['id'])
    v=register(client,'other@example.test')
    assert client.post('/api/v1/remittances',json={'title':'Foreign','amount_minor':1000,'received_on':'2026-10-01','recipient_id':u['id'],'allocations':[{'name':'Food','amount_minor':1000,'assigned_to':v['id']}]}).status_code==400

def test_recipient_confirmation(client):
    owner=register(client);family,_=member(client);login(client,owner['email']);r=create_padala(client,family['id'])
    assert client.post(f"/api/v1/remittances/{r['id']}/confirm").status_code==403
    login(client,family['email']);assert client.post(f"/api/v1/remittances/{r['id']}/confirm").json()['confirmed'] is True

def test_full_review_workflow(client):
    owner=register(client);family,_=member(client);login(client,owner['email']);r=create_padala(client,family['id']);login(client,family['email'])
    e=client.post('/api/v1/evidence',json=evidence_body(r)).json()
    assert e['status']=='pending'
    assert client.post(f"/api/v1/evidence/{e['id']}/review",json={'status':'accepted','expected_version':e['version']}).status_code==403
    login(client,owner['email'])
    assert len(client.get('/api/v1/notifications').json())>=1
    review=client.post(f"/api/v1/evidence/{e['id']}/review",json={'status':'clarification','note':'Please explain the amount','expected_version':e['version']})
    assert review.status_code==200,review.text
    login(client,family['email'])
    reply=client.post(f"/api/v1/evidence/{e['id']}/respond",json={'note':'This includes groceries for the week.','expected_version':review.json()['version']})
    assert reply.status_code==200,reply.text
    login(client,owner['email'])
    final=client.post(f"/api/v1/evidence/{e['id']}/review",json={'status':'accepted','note':'Understood','expected_version':reply.json()['version']})
    assert final.json()['provider_confirmation']=='not_connected'
    detail=client.get(f"/api/v1/remittances/{r['id']}").json()
    assert detail['accepted_minor']==10000 and len(detail['activity'])>=4

def test_split_receipt_no_double_count(client):
    _,_,r=family_padala(client);body=evidence_body(r,10000)
    body['lines']=[{'allocation_id':a['id'],'amount_minor':5000} for a in r['allocations']]
    response=client.post('/api/v1/evidence',json=body);assert response.status_code==201,response.text
    detail=client.get(f"/api/v1/remittances/{r['id']}").json()
    assert detail['recorded_minor']==10000 and detail['savings_contributions_minor']==5000

def test_mismatched_split(client):
    _,_,r=family_padala(client);body=evidence_body(r);body['lines'][0]['amount_minor']=1
    assert client.post('/api/v1/evidence',json=body).status_code==422

def test_foreign_allocation_rejected(client):
    owner,family,r=family_padala(client);login(client,owner['email']);s=create_padala(client,family['id']);login(client,family['email']);body=evidence_body(r);body['lines'][0]['allocation_id']=s['allocations'][0]['id']
    assert client.post('/api/v1/evidence',json=body).status_code==400

def test_unassigned_family_blocked(client):
    owner=register(client);family,_=member(client);login(client,owner['email']);r=create_padala(client,owner['id']);login(client,family['email'])
    assert client.post('/api/v1/evidence',json=evidence_body(r)).status_code==403

def test_ofw_cannot_upload_or_submit_a_family_update(client):
    owner=register(client);family,_=member(client);login(client,owner['email']);r=create_padala(client,family['id'])
    assert client.post('/api/v1/evidence',json=evidence_body(r)).status_code==403
    assert client.post('/api/v1/uploads',files={'file':('receipt.png',png_bytes(),'image/png')}).status_code==403

def test_no_receipt_requires_explanation(client):
    _,_,r=family_padala(client);body=evidence_body(r);body['note']=''
    assert client.post('/api/v1/evidence',json=body).status_code==422

def test_exact_duplicate_upload(client):
    register(client);member(client);b=png_bytes()
    first=client.post('/api/v1/uploads',files={'file':('receipt.png',b,'image/png')});assert first.status_code==201,first.text
    same=client.post('/api/v1/uploads',files={'file':('copy.png',b,'image/png')})
    assert same.json()['id']==first.json()['id']

def test_upload_attach_and_no_double_claim(client):
    _,_,r=family_padala(client)
    upload=client.post('/api/v1/uploads',files={'file':('receipt.png',png_bytes(),'image/png')}).json()
    body=evidence_body(r,upload_id=upload['id'])
    assert client.post('/api/v1/evidence',json=body).status_code==201
    assert client.post('/api/v1/evidence',json=body).status_code==409
    assert client.post('/api/v1/uploads',files={'file':('copy.png',png_bytes(),'image/png')}).status_code==409

def test_upload_access_protected(client):
    register(client);member(client)
    up=client.post('/api/v1/uploads',files={'file':('receipt.png',png_bytes(),'image/png')}).json()
    assert client.get(up['download_url']).status_code==200
    register(client,'other@example.test')
    assert client.get(up['download_url']).status_code==404

def test_invalid_upload(client):
    register(client);member(client)
    assert client.post('/api/v1/uploads',files={'file':('fake.png',b'<script>alert(1)</script>','image/png')}).status_code==400

def test_oversize_upload(client):
    register(client);member(client)
    assert client.post('/api/v1/uploads',files={'file':('large.jpg',b'x'*(6*1024*1024),'image/jpeg')}).status_code==413

def test_ocr_not_configured(client):
    register(client);member(client);up=client.post('/api/v1/uploads',files={'file':('r.png',png_bytes(),'image/png')}).json()
    assert client.post(f"/api/v1/uploads/{up['id']}/extract",json={'consent':True}).status_code==503

def test_ocr_requires_consent(client):
    register(client);member(client);up=client.post('/api/v1/uploads',files={'file':('r.png',png_bytes(),'image/png')}).json()
    assert client.post(f"/api/v1/uploads/{up['id']}/extract",json={'consent':False}).status_code==422

def test_duplicate_reference_flag(client):
    _,_,r=family_padala(client);body=evidence_body(r);body['reference']='REF-123'
    assert client.post('/api/v1/evidence',json=body).status_code==201
    second=client.post('/api/v1/evidence',json=body).json()
    assert any('reference' in msg for msg in second['checks'])

def test_overspend_flag(client):
    _,_,r=family_padala(client);result=client.post('/api/v1/evidence',json=evidence_body(r,200000)).json()
    assert any('exceed' in s for s in result['checks'])

def test_future_date_flag(client):
    _,_,r=family_padala(client);body=evidence_body(r);body['occurred_on']='2099-01-01'
    assert any('future' in s for s in client.post('/api/v1/evidence',json=body).json()['checks'])

def test_void_removes_totals_preserves_history(client):
    _,_,r=family_padala(client);e=client.post('/api/v1/evidence',json=evidence_body(r)).json()
    result=client.post(f"/api/v1/evidence/{e['id']}/void",json={'note':'Entered against the wrong plan.','expected_version':e['version']})
    assert result.status_code==200
    d=client.get(f"/api/v1/remittances/{r['id']}").json()
    assert d['recorded_minor']==0 and d['evidence'][0]['status']=='voided'

def test_stale_review_blocked(client):
    owner,_,r=family_padala(client);e=client.post('/api/v1/evidence',json=evidence_body(r)).json();login(client,owner['email'])
    body={'status':'accepted','expected_version':e['version']}
    assert client.post(f"/api/v1/evidence/{e['id']}/review",json=body).status_code==200
    assert client.post(f"/api/v1/evidence/{e['id']}/review",json=body).status_code==409

def test_no_forged_verification_field(client):
    _,_,r=family_padala(client);body=evidence_body(r);body['provider_confirmation']='verified'
    assert client.post('/api/v1/evidence',json=body).status_code==422

def test_export_scoped(client):
    u=register(client);r=create_padala(client,u['id'])
    assert len(client.get('/api/v1/export').json()['remittances'])==1
    register(client,'other@example.test')
    assert client.get('/api/v1/export').json()['remittances']==[]

def test_csv_formula_escaping(client):
    u=register(client)
    body={'title':'=HYPERLINK("bad")','amount_minor':1000,'received_on':'2026-10-01','recipient_id':u['id'],'allocations':[{'name':'+formula','amount_minor':1000,'assigned_to':u['id']}]}
    assert client.post('/api/v1/remittances',json=body).status_code==201
    text=client.get('/api/v1/export?format=csv').text
    assert "'=HYPERLINK" in text and "'+formula" in text

def test_email_preferences(client):
    register(client)
    assert client.patch('/api/v1/auth/preferences',json={'email_notifications':True}).json()['email_notifications'] is True

def test_forgot_without_email(client):
    assert client.post('/api/v1/auth/forgot-password',json={'email':'any@example.test'}).status_code==503

def test_password_reset_single_use(client,app):
    user=register(client);token='a-valid-long-reset-token-for-test'
    with app.state.session_factory() as db:
        db.add(ResetToken(token_hash=token_hash(token),user_id=user['id'],expires_at=int(time.time())+60));db.commit()
    body={'token':token,'password':'ANewPass!123456'}
    assert client.post('/api/v1/auth/reset-password',json=body).status_code==200
    assert client.get('/api/v1/auth/me').status_code==401
    assert client.post('/api/v1/auth/reset-password',json=body).status_code==400

def test_rate_limit(client):
    statuses=[client.post('/api/v1/auth/login',json={'email':'missing@example.test','password':'bad'}).status_code for _ in range(11)]
    assert statuses[-1]==429

def test_notification_read(client):
    register(client)
    assert client.post('/api/v1/notifications/read').status_code==200

def test_unknown_export_format(client):
    register(client)
    assert client.get('/api/v1/export?format=exe').status_code==400

def test_no_store_headers(client):
    assert client.get('/api/v1/config').headers['cache-control']=='no-store'


def test_password_whitespace_preserved(client):
    password='  Important Spaces!123  '
    result=client.post('/api/v1/auth/register',json={'name':'Owner','email':'space@example.test','household_name':'Family','password':password})
    assert result.status_code==201,result.text
    assert client.post('/api/v1/auth/login',json={'email':'space@example.test','password':password.strip()}).status_code==401
    assert client.post('/api/v1/auth/login',json={'email':'space@example.test','password':password}).status_code==200


def test_email_verification_blocks_sign_in_until_the_link_is_used(tmp_path):
    settings=Settings(data_dir=tmp_path,worker_enabled=False,registration_enabled=True,email_verification_required=True,
                      allowed_origins=['http://localhost:3000'],smtp_host='mail.example.test',email_from='Padala <support@example.test>')
    app=create_app(settings)
    with TestClient(app) as verification_client:
        response=verification_client.post('/api/v1/auth/register',json={'name':'Verified Owner','email':'verify@example.test','household_name':'Verified family','password':PASSWORD})
        assert response.status_code==201,response.text
        assert response.json()['verification_required'] is True
        assert verification_client.post('/api/v1/auth/login',json={'email':'verify@example.test','password':PASSWORD}).status_code==403
        with app.state.session_factory() as db:
            message=db.scalar(select(EmailOutbox).where(EmailOutbox.recipient=='verify@example.test'))
            token_row=db.scalar(select(EmailVerificationToken))
            assert message is not None and token_row is not None
            token=message.body.split('?verify=',1)[1].splitlines()[0]
        assert verification_client.post('/api/v1/auth/verify-email',json={'token':token}).status_code==200
        assert verification_client.post('/api/v1/auth/verify-email',json={'token':token}).status_code==400
        assert verification_client.post('/api/v1/auth/login',json={'email':'verify@example.test','password':PASSWORD}).status_code==200


def test_resend_verification_does_not_disclose_account_state(tmp_path):
    settings=Settings(data_dir=tmp_path,worker_enabled=False,registration_enabled=True,email_verification_required=True,
                      allowed_origins=['http://localhost:3000'],smtp_host='mail.example.test',email_from='Padala <support@example.test>')
    app=create_app(settings)
    with TestClient(app) as verification_client:
        register_response=verification_client.post('/api/v1/auth/register',json={'name':'Pending Owner','email':'pending@example.test','household_name':'Pending family','password':PASSWORD})
        assert register_response.status_code==201
        known=verification_client.post('/api/v1/auth/resend-verification',json={'email':'pending@example.test'})
        unknown=verification_client.post('/api/v1/auth/resend-verification',json={'email':'missing@example.test'})
        assert known.status_code==200 and known.json()==unknown.json()
        with app.state.session_factory() as db:
            assert len(db.scalars(select(EmailVerificationToken)).all())==1
