from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import text


def ensure_version_table_capacity(connection) -> None:
    """Make Alembic's revision column large enough for this application's IDs.

    Alembic creates `alembic_version.version_num` as VARCHAR(32) by default.
    Some of Padala's descriptive revision identifiers are longer. SQLite does
    not enforce that length, but PostgreSQL does, so widen the tool-owned table
    before applying migrations. This is idempotent and touches no app data.
    """
    if connection.dialect.name == 'postgresql':
        connection.execute(text('ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)'))

def upgrade_database(engine):
    root=Path(__file__).resolve().parents[1]
    cfg=Config(str(root/'alembic.ini'))
    cfg.set_main_option('script_location',str(root/'alembic'))
    with engine.begin() as connection:
        cfg.attributes['connection']=connection
        # Ensure the default Alembic table exists before widening it. This also
        # upgrades an already-created Render staging database that failed while
        # recording a long revision identifier.
        command.ensure_version(cfg)
        ensure_version_table_capacity(connection)
        command.upgrade(cfg,'head')
