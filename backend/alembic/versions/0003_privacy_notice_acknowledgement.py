"""Record acknowledgement of the published privacy-notice version.

Revision ID: 0003_privacy_notice_acknowledgement
Revises: 0002_email_verification
"""
from alembic import op
import sqlalchemy as sa

revision = '0003_privacy_notice_acknowledgement'
down_revision = '0002_email_verification'
branch_labels = None
depends_on = None


def upgrade():
    # Existing accounts have no recorded acknowledgement. If the operator
    # publishes a notice, they must acknowledge its current version before
    # household records are exposed.
    op.add_column('users', sa.Column('privacy_notice_version', sa.String(length=64), nullable=False, server_default=''))
    op.add_column('users', sa.Column('privacy_notice_acknowledged_at', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('users', 'privacy_notice_acknowledged_at')
    op.drop_column('users', 'privacy_notice_version')
