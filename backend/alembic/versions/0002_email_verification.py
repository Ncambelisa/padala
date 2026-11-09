"""Add verified-email state and one-time verification tokens.

Revision ID: 0002_email_verification
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_email_verification'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Existing local/pilot users keep access; production enables verification for
    # accounts created after EMAIL_VERIFICATION_REQUIRED is turned on.
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table(
        'email_verification_tokens',
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('expires_at', sa.Integer(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('token_hash'),
    )


def downgrade():
    op.drop_table('email_verification_tokens')
    op.drop_column('users', 'email_verified')
