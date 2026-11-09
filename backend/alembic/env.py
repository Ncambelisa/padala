from alembic import context
from sqlalchemy import engine_from_config, pool
from app.db import Base
from app import models  # Register every mapped table.
from app.config import Settings

config=context.config
target_metadata=Base.metadata

def run(connection):
    context.configure(connection=connection,target_metadata=target_metadata,compare_type=True,render_as_batch=True)
    with context.begin_transaction():context.run_migrations()

if context.is_offline_mode():
    settings=Settings()
    url=settings.database_url or f'sqlite:///{settings.data_dir / "padala.sqlite3"}'
    context.configure(url=url,target_metadata=target_metadata,literal_binds=True)
    with context.begin_transaction():context.run_migrations()
elif config.attributes.get('connection') is not None:
    run(config.attributes['connection'])
else:
    settings=Settings();settings.data_dir.mkdir(parents=True,exist_ok=True)
    section=config.get_section(config.config_ini_section) or {}
    section['sqlalchemy.url']=settings.database_url or f'sqlite:///{settings.data_dir / "padala.sqlite3"}'
    engine=engine_from_config(section,prefix='sqlalchemy.',poolclass=pool.NullPool)
    with engine.connect() as connection:run(connection)
