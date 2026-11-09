"""Dedicated outbox worker for a production deployment.

Run exactly one worker instance per queue until a durable queue with worker
coordination is introduced. API processes must set EMAIL_WORKER_ENABLED=false.
"""
from __future__ import annotations

import signal
from threading import Event

from .config import Settings
from .db import make_database
from .migrations import upgrade_database
from .services import send_outbox


def main() -> None:
    settings = Settings()
    settings.validate()
    if not settings.smtp_host:
        raise SystemExit('SMTP_HOST is required to run the outbox worker.')
    engine, factory = make_database(settings)
    upgrade_database(engine)
    stop = Event()

    def stop_worker(_signum, _frame) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)
    try:
        send_outbox(factory, settings, stop)
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
