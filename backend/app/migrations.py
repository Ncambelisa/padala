from pathlib import Path
from alembic import command
from alembic.config import Config

def upgrade_database(engine):
    root=Path(__file__).resolve().parents[1]
    cfg=Config(str(root/'alembic.ini'))
    cfg.set_main_option('script_location',str(root/'alembic'))
    with engine.begin() as connection:
        cfg.attributes['connection']=connection
        command.upgrade(cfg,'head')
