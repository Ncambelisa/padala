import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app

PASSWORD='PilotPass!12345'
@pytest.fixture
def app(tmp_path):
    return create_app(Settings(data_dir=tmp_path,worker_enabled=False,registration_enabled=True,allowed_origins=['http://localhost:3000'],smtp_host='',azure_endpoint='',azure_key=''))
@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c

def register(client,email='owner@example.test'):
    result=client.post('/api/v1/auth/register',json={'name':'Owner','email':email,'household_name':'Test family','password':PASSWORD})
    assert result.status_code==201,result.text
    client.headers['X-CSRF-Token']=result.json()['csrf']
    return result.json()['user']

def login(client,email,password=PASSWORD):
    result=client.post('/api/v1/auth/login',json={'email':email,'password':password})
    assert result.status_code==200,result.text
    client.headers['X-CSRF-Token']=result.json()['csrf']
    return result.json()['user']

def member(client):
    inv=client.post('/api/v1/invitations',json={'name':'Family','email':'family@example.test'})
    assert inv.status_code==201,inv.text
    token=inv.json()['link'].split('invite=')[1]
    result=client.post('/api/v1/invitations/accept',json={'token':token,'name':'Family','password':PASSWORD})
    assert result.status_code==200,result.text
    me=client.get('/api/v1/auth/me').json();client.headers['X-CSRF-Token']=me['csrf']
    return me['user'],token

def create_padala(client,recipient_id,amount=300000):
    body={'title':'Test padala','amount_minor':amount,'received_on':'2026-10-01','recipient_id':recipient_id,
          'allocations':[{'name':'Food','kind':'expense','amount_minor':amount//2,'assigned_to':recipient_id},
                         {'name':'Savings','kind':'savings','amount_minor':amount-amount//2,'assigned_to':recipient_id}]}
    result=client.post('/api/v1/remittances',json=body)
    assert result.status_code==201,result.text
    return result.json()

def evidence_body(r,amount=10000,upload_id=None):
    return {'remittance_id':r['id'],'upload_id':upload_id,'merchant':'Test merchant','amount_minor':amount,
            'occurred_on':'2026-10-02','reference':'','note':'A documented fictional test purchase.',
            'lines':[{'allocation_id':r['allocations'][0]['id'],'amount_minor':amount}]}
