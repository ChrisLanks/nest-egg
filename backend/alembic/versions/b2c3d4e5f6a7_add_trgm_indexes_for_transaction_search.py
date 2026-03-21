"""Add pg_trgm GIN indexes for fast transaction text search.

Revision ID: b3c4d5e6f7a8
Revises: z8a9b0c1d2e3
Create Date: 2026-03-20
"""
from alembic import op

revision = 'b3c4d5e6f7a8'
down_revision = 'z8a9b0c1d2e3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Enable pg_trgm extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # GIN trigram indexes for ILIKE search on transactions
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_transactions_merchant_name_trgm
        ON transactions USING GIN (merchant_name gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_transactions_description_trgm
        ON transactions USING GIN (description gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_transactions_notes_trgm
        ON transactions USING GIN (notes gin_trgm_ops)
    """)
    op.create_index('ix_report_templates_updated_at', 'report_templates', ['updated_at'])

def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_transactions_merchant_name_trgm")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_transactions_description_trgm")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_transactions_notes_trgm")
    op.drop_index('ix_report_templates_updated_at', 'report_templates')
