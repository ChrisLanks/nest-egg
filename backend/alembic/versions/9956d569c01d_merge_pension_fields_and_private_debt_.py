"""merge_pension_fields_and_private_debt_enum_fix

Revision ID: 9956d569c01d
Revises: f0549612d0ad, a3b4c5d6e7f8
Create Date: 2026-02-19 17:08:07.999657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9956d569c01d'
down_revision: Union[str, None] = ('f0549612d0ad', 'a3b4c5d6e7f8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
