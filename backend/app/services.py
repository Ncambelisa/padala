from __future__ import annotations
import asyncio
import hashlib
import io
import smtplib
import socket
import ssl
import struct
import time
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from .models import *

Image.MAX_IMAGE_PIXELS = 20_000_000

def audit(db, user, action, detail, remittance_id=''):
    db.add(AuditEvent(household_id=user.household_id, actor=user.name, action=action,
                      detail=detail, remittance_id=remittance_id))

def queue_email(db, settings, recipient, subject, body):
    if settings.smtp_host:
        db.add(EmailOutbox(recipient=recipient, subject=subject, body=body))

def notify(db, settings, user, title, detail, remittance_id=''):
    # An access-revoked member must not accumulate household updates or receive
    # optional email notifications while they cannot sign in.
    if not user or not user.is_active:
        return
    db.add(Notification(user_id=user.id, title=title, detail=detail, remittance_id=remittance_id))
    if user.email_notifications:
        # No receipt, amount, or bank details are exposed in email notifications.
        queue_email(db, settings, user.email, 'An update in your Padala household',
                    f'Your household has a new update. Sign in to view it: {settings.app_url}\nDo not share your password or one-time codes.')

def inspect_file(data: bytes, filename: str, settings):
    if not data or len(data) > settings.max_upload_bytes:
        raise HTTPException(413, 'Upload a non-empty file up to 5 MB.')
    # Preserve original bytes for duplicate detection and evidence integrity.
    # PDFs are downloads only, not embedded; this is not malware scanning.
    if data.startswith(b'%PDF-'):
        if b'%%EOF' not in data[-2048:]:
            raise HTTPException(400, 'The PDF appears incomplete.')
        return 'application/pdf', '.pdf'
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            if image.format not in {'JPEG','PNG','WEBP'}:
                raise ValueError('Unsupported format')
            fmt = image.format
        return {'JPEG':('image/jpeg','.jpg'), 'PNG':('image/png','.png'), 'WEBP':('image/webp','.webp')}[fmt]
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(400, 'Use a valid JPEG, PNG, WebP, or PDF. HEIC is not supported; export as JPEG.')


def scan_file(data: bytes, settings) -> None:
    """Fail closed against a private ClamAV-compatible clamd scanner.

    The INSTREAM protocol sends only bytes, never a server file path. clamd itself
    does not provide transport encryption or authentication, so its TCP listener
    must stay on a private, operator-controlled network.
    """
    if not settings.malware_scan_host:
        if settings.malware_scan_required:
            raise HTTPException(503, 'File scanning is temporarily unavailable. Please try again later.')
        return
    try:
        with socket.create_connection((settings.malware_scan_host, settings.malware_scan_port), timeout=5) as scanner:
            scanner.settimeout(15)
            scanner.sendall(b'zINSTREAM\0')
            for start in range(0, len(data), 64 * 1024):
                chunk = data[start:start + 64 * 1024]
                scanner.sendall(struct.pack('!I', len(chunk)) + chunk)
            scanner.sendall(struct.pack('!I', 0))
            reply = bytearray()
            while b'\0' not in reply:
                received = scanner.recv(4096)
                if not received:
                    raise OSError('scanner closed the connection without a response')
                reply.extend(received)
                if len(reply) > 8192:
                    raise OSError('scanner returned an invalid response')
        result = bytes(reply).split(b'\0', 1)[0].decode('utf-8', 'replace')
    except OSError:
        raise HTTPException(503, 'File scanning is temporarily unavailable. Please try again later.')
    if result.endswith(' FOUND'):
        # Do not disclose signature names or internal scanner details to uploaders.
        raise HTTPException(422, 'This file cannot be accepted. Please choose a different file.')
    if not result.endswith(' OK'):
        raise HTTPException(503, 'File scanning is temporarily unavailable. Please try again later.')

async def extract_azure(data: bytes, mime: str, settings) -> dict:
    """Actual REST adapter; no fake OCR responses. Authentication is out of scope."""
    if not settings.ocr_enabled:
        raise HTTPException(503, 'Receipt extraction is not configured. Enter the details manually.')
    parsed = urlsplit(settings.azure_endpoint)
    if parsed.scheme != 'https' or not parsed.netloc:
        raise HTTPException(503, 'The administrator must configure a valid HTTPS Azure endpoint.')
    endpoint = settings.azure_endpoint + '/documentintelligence/documentModels/prebuilt-receipt:analyze?api-version=2024-11-30'
    headers = {'Ocp-Apim-Subscription-Key': settings.azure_key, 'Content-Type': mime}
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=False) as client:
            result = await client.post(endpoint, headers=headers, content=data)
            if result.status_code != 202:
                raise HTTPException(502, 'Extraction provider rejected this request. Check the account, region, and document support.')
            operation = result.headers.get('operation-location', '')
            # Never send the secret to a redirect or different origin.
            if urlsplit(operation).scheme != 'https' or urlsplit(operation).netloc != parsed.netloc:
                raise HTTPException(502, 'Extraction provider returned an invalid operation location.')
            for _ in range(25):
                await asyncio.sleep(1)
                poll = await client.get(operation, headers={'Ocp-Apim-Subscription-Key': settings.azure_key})
                if poll.status_code != 200:
                    raise HTTPException(502, 'Unable to read extraction results. Try again later.')
                body = poll.json()
                if body.get('status') == 'failed':
                    raise HTTPException(422, 'The provider could not extract this document. Enter its details manually.')
                if body.get('status') == 'succeeded':
                    return normalize_extraction(body)
            raise HTTPException(504, 'Extraction timed out. No authentication was performed. Enter the details manually or retry later.')
    except httpx.HTTPError:
        raise HTTPException(502, 'Could not reach the extraction provider. Your uploaded file is still available.')

def normalize_extraction(result: dict) -> dict:
    documents = result.get('analyzeResult', {}).get('documents', [])
    fields = documents[0].get('fields', {}) if documents else {}
    def value(name, key):
        return fields.get(name, {}).get(key)
    total = value('Total','valueCurrency')
    if isinstance(total, dict):
        amount = total.get('amount')
        currency = total.get('currencyCode')
    else:
        amount = value('Total','valueNumber')
        currency = None
    amount_minor = int((Decimal(str(amount))*100).quantize(Decimal('1'))) if amount is not None else None
    return {'provider':'azure-document-intelligence', 'merchant':value('MerchantName','valueString'),
            'occurred_on':value('TransactionDate','valueDate'), 'amount_minor':amount_minor,
            'currency':currency, 'confidence':{k: v.get('confidence') for k,v in fields.items() if k in {'MerchantName','Total','TransactionDate'}},
            'notice':'Extracted text only. Review the values. Not proof of authenticity or a completed transaction.'}

def send_outbox(factory, settings, stop):
    """One worker per local deployment. At-least-once email delivery, bounded retries."""
    while not stop.wait(3):
        if not settings.smtp_host:
            continue
        with factory() as db:
            messages = db.scalars(select(EmailOutbox).where(EmailOutbox.status=='queued', EmailOutbox.next_attempt<=int(time.time())).limit(10)).all()
            for item in messages:
                try:
                    msg = EmailMessage()
                    msg['From'], msg['To'], msg['Subject'] = settings.email_from, item.recipient, item.subject
                    msg.set_content(item.body)
                    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=8) as smtp:
                        smtp.ehlo()
                        if settings.smtp_starttls:
                            smtp.starttls(context=ssl.create_default_context())
                            smtp.ehlo()
                        if settings.smtp_user:
                            smtp.login(settings.smtp_user, settings.smtp_password)
                        smtp.send_message(msg)
                    item.status = 'sent'
                    item.body = ''  # Do not retain reset / invitation secrets after delivery.
                except (smtplib.SMTPException, OSError):
                    item.attempts += 1
                    item.next_attempt = int(time.time()) + min(3600, 30 * 2**item.attempts)
                    if item.attempts >= 5:
                        item.status = 'failed'
                        item.body = ''
                db.commit()
