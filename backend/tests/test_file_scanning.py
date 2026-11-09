from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.services import scan_file


class FakeScanner:
    def __init__(self, reply: bytes):
        self.reply = reply
        self.sent: list[bytes] = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def settimeout(self, _seconds):
        return None

    def sendall(self, value: bytes):
        self.sent.append(value)

    def recv(self, _size: int) -> bytes:
        reply, self.reply = self.reply, b''
        return reply


def scanner_settings(**overrides):
    values = {'malware_scan_host': 'clamd.internal.test', 'malware_scan_port': 3310, 'malware_scan_required': True}
    values.update(overrides)
    return Settings(**values)


def test_scan_streams_file_to_clamd_and_accepts_clean_result():
    scanner = FakeScanner(b'stream: OK\0')
    with patch('app.services.socket.create_connection', return_value=scanner):
        scan_file(b'fictional-file', scanner_settings())
    assert scanner.sent[0] == b'zINSTREAM\0'
    assert scanner.sent[-1] == b'\x00\x00\x00\x00'


def test_scan_rejects_detected_file_without_leaking_signature():
    scanner = FakeScanner(b'stream: Test.Signature FOUND\0')
    with patch('app.services.socket.create_connection', return_value=scanner):
        with pytest.raises(HTTPException) as exc:
            scan_file(b'fictional-file', scanner_settings())
    assert exc.value.status_code == 422
    assert 'Signature' not in exc.value.detail


def test_required_scanner_failure_fails_closed():
    with patch('app.services.socket.create_connection', side_effect=OSError('offline')):
        with pytest.raises(HTTPException) as exc:
            scan_file(b'fictional-file', scanner_settings())
    assert exc.value.status_code == 503
