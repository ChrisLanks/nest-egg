"""Add missing columns: OCR on attachments, scheduled_delivery on report_templates,
expires_at on household_guests, access_expires_days on household_guest_invitations.

Revision ID: m1s2c3o4l5m6
Revises: 513b8ec9f6cc
Create Date: 2026-03-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'm1s2c3o4l5m6'
down_revision: Union[str, None] = '513b8ec9f6cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transaction_attachments', sa.Column('ocr_status', sa.String(20), nullable=True))
    op.add_column('transaction_attachments', sa.Column('ocr_data', sa.JSON(), nullable=True))
    op.add_column('report_templates', sa.Column('scheduled_delivery', sa.JSON(), nullable=True))
    op.add_column('household_guests', sa.Column('expires_at', sa.DateTime(), nullable=True))
    op.add_column('household_guest_invitations', sa.Column('access_expires_days', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('household_guest_invitations', 'access_expires_days')
    op.drop_column('household_guests', 'expires_at')
    op.drop_column('report_templates', 'scheduled_delivery')
    op.drop_column('transaction_attachments', 'ocr_data')
    op.drop_column('transaction_attachments', 'ocr_status')
