"""Add tax_treatment column to accounts table.

Stores the tax treatment (pre_tax, roth, taxable, tax_free) for retirement
and investment accounts.  Existing retirement accounts get a sensible default:
  - RETIREMENT_ROTH → ROTH
  - RETIREMENT_401K / RETIREMENT_IRA → PRE_TAX
  - HSA → TAX_FREE
  - RETIREMENT_529 → TAX_FREE

Non-retirement accounts are left NULL (meaning "not applicable").

Revision ID: o7p8q9r0s1t2
Revises: n6o7p8q9r0s1
Create Date: 2026-02-24 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "o7p8q9r0s1t2"
down_revision: Union[str, None] = "n6o7p8q9r0s1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type first
    tax_treatment_enum = sa.Enum(
        "PRE_TAX", "ROTH", "TAXABLE", "TAX_FREE",
        name="taxtreatment",
    )
    tax_treatment_enum.create(op.get_bind(), checkfirst=True)

    # Add the nullable column
    op.add_column(
        "accounts",
        sa.Column("tax_treatment", tax_treatment_enum, nullable=True),
    )

    # Backfill existing retirement accounts with sensible defaults
    op.execute(
        "UPDATE accounts SET tax_treatment = 'ROTH' "
        "WHERE account_type = 'RETIREMENT_ROTH' AND tax_treatment IS NULL"
    )
    op.execute(
        "UPDATE accounts SET tax_treatment = 'PRE_TAX' "
        "WHERE account_type IN ('RETIREMENT_401K', 'RETIREMENT_IRA') AND tax_treatment IS NULL"
    )
    op.execute(
        "UPDATE accounts SET tax_treatment = 'TAX_FREE' "
        "WHERE account_type IN ('HSA', 'RETIREMENT_529') AND tax_treatment IS NULL"
    )


def downgrade() -> None:
    op.drop_column("accounts", "tax_treatment")
    sa.Enum(name="taxtreatment").drop(op.get_bind(), checkfirst=True)
