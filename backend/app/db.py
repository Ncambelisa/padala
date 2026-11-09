from __future__ import annotations
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import Settings

class Base(DeclarativeBase):
    pass

def make_database(settings: Settings):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    url = settings.database_url or f'sqlite:///{settings.data_dir / "padala.sqlite3"}'
    kwargs = {'check_same_thread': False, 'timeout': 30} if url.startswith('sqlite') else {}
    engine = create_engine(url, connect_args=kwargs, pool_pre_ping=True)
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def sqlite_settings(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.close()
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
