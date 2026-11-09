import json
from unittest.mock import patch
import pytest
import httpx
from app.config import Settings
from app.services import normalize_extraction,extract_azure


def test_extract_normalization():
    result=normalize_extraction({'analyzeResult':{'documents':[{'fields':{'MerchantName':{'valueString':'Test Store','confidence':0.9},'Total':{'valueCurrency':{'amount':123.45,'currencyCode':'PHP'},'confidence':0.8},'TransactionDate':{'valueDate':'2026-10-01'}}}]}})
    assert result['amount_minor']==12345
    assert result['currency']=='PHP'
    assert 'authentic' in result['notice']

def test_missing_fields_safe():
    result=normalize_extraction({'analyzeResult':{}})
    assert result['amount_minor'] is None and result['merchant'] is None

def test_azure_adapter_mocked(tmp_path):
    import asyncio
    calls=[]
    def handler(request):
        calls.append(request)
        if request.method=='POST':
            return httpx.Response(202,headers={'operation-location':'https://test.cognitiveservices.azure.com/documentintelligence/result'})
        return httpx.Response(200,json={'status':'succeeded','analyzeResult':{'documents':[{'fields':{'Total':{'valueNumber':88.75}}}]}})
    original=httpx.AsyncClient
    def make_client(**kwargs):
        return original(transport=httpx.MockTransport(handler),**kwargs)
    async def no_wait(_):
        return None
    settings=Settings(data_dir=tmp_path,azure_endpoint='https://test.cognitiveservices.azure.com',azure_key='fake-test-key')
    with patch('app.services.httpx.AsyncClient',side_effect=make_client),patch('app.services.asyncio.sleep',side_effect=no_wait):
        result=asyncio.run(extract_azure(b'fake-test-bytes','image/png',settings))
    assert result['amount_minor']==8875
    assert calls[0].headers['Ocp-Apim-Subscription-Key']=='fake-test-key'
    assert calls[0].content==b'fake-test-bytes'

def test_azure_rejects_foreign_poll_host(tmp_path):
    import asyncio
    from fastapi import HTTPException
    original=httpx.AsyncClient
    def make_client(**kwargs):
        return original(transport=httpx.MockTransport(lambda request:httpx.Response(202,headers={'operation-location':'https://foreign.invalid/steal-key'})),**kwargs)
    settings=Settings(data_dir=tmp_path,azure_endpoint='https://test.cognitiveservices.azure.com',azure_key='fake-test-key')
    with patch('app.services.httpx.AsyncClient',side_effect=make_client),pytest.raises(HTTPException) as exc:
        asyncio.run(extract_azure(b'fake','image/png',settings))
    assert exc.value.status_code==502


def test_email_outbox_mocked(app):
    from app.models import EmailOutbox
    from app.services import send_outbox
    from sqlalchemy import select
    from unittest.mock import MagicMock
    settings=app.state.settings
    settings.smtp_host='test-smtp.invalid'
    class OneIteration:
        calls=0
        def wait(self,_):
            self.calls+=1
            return self.calls>1
    with app.state.session_factory() as db:
        # Test fixture app schema is created by the TestClient lifespan in the next block.
        pass
    from fastapi.testclient import TestClient
    with TestClient(app):
        with app.state.session_factory() as db:
            db.add(EmailOutbox(recipient='test@example.test',subject='Test',body='Private test link'));db.commit()
        smtp=MagicMock()
        with patch('app.services.smtplib.SMTP') as smtp_factory:
            smtp_factory.return_value.__enter__.return_value=smtp
            send_outbox(app.state.session_factory,settings,OneIteration())
        assert smtp.send_message.call_count==1
        with app.state.session_factory() as db:
            row=db.scalar(select(EmailOutbox))
            assert row.status=='sent' and row.body==''
