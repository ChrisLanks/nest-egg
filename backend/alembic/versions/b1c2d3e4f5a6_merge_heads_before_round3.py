"""merge_heads_before_round3

Merge the two branch heads:
  - a1b2c3d4e5f6  (create_account_contributions_table, from e1f2g3h4i5j6 chain)
  - f1a2b3c4d5e6  (add_transaction_composite_indexes, from 3dd06b9e0f14 chain)

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6, f1a2b3c4d5e6
Create Date: 2026-02-22 00:00:00.000000

"""
from typing import Sequence, Union

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str]] = ("a1b2c3d4e5f6", "f1a2b3c4d5e6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
