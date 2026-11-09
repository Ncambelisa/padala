"""Add reversible household-member access revocation.

Revision ID: 0004_household_member_access
Revises: 0003_privacy_notice_acknowledgement
"""
from alembic import op
import sqlalchemy as sa

revision = '0004_household_member_access'
down_revision = '0003_privacy_notice_acknowledgement'
branch_labels = None
depends_on = None


def upgrade():
    # Existing members retain access on upgrade.  Revocation is deliberately
    # separate from deletion because prior shared records retain their actor and
    # assignee references.
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('users', sa.Column('access_revoked_at', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('users', 'access_revoked_at')
    op.drop_column('users', 'is_active')
