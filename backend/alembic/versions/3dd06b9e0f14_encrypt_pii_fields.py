"""encrypt_pii_fields

Widen vehicle_vin, property_address, property_zip to Text and encrypt any
existing plaintext values in-place using the application's Fernet encryption
key (MASTER_ENCRYPTION_KEY).

Revision ID: 3dd06b9e0f14
Revises: 2cc95a8fafd3
Create Date: 2026-02-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3dd06b9e0f14"
down_revision: Union[str, None] = "2cc95a8fafd3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widen columns to Text so they can hold encrypted ciphertext (longer than plaintext)
    op.alter_column("accounts", "vehicle_vin", type_=sa.Text, existing_nullable=True)
    op.alter_column("accounts", "property_address", type_=sa.Text, existing_nullable=True)
    op.alter_column("accounts", "property_zip", type_=sa.Text, existing_nullable=True)

    # Encrypt any existing plaintext values in-place
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT id, vehicle_vin, property_address, property_zip FROM accounts "
            "WHERE vehicle_vin IS NOT NULL "
            "   OR property_address IS NOT NULL "
            "   OR property_zip IS NOT NULL"
        )
    )
    rows = result.fetchall()
    if not rows:
        return

    from app.services.encryption_service import get_encryption_service

    svc = get_encryption_service()

    for row in rows:
        updates: dict = {}
        if row.vehicle_vin:
            updates["vehicle_vin"] = svc.encrypt_token(row.vehicle_vin)
        if row.property_address:
            updates["property_address"] = svc.encrypt_token(row.property_address)
        if row.property_zip:
            updates["property_zip"] = svc.encrypt_token(row.property_zip)

        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            bind.execute(
                sa.text(f"UPDATE accounts SET {set_clause} WHERE id = :id"),
                {**updates, "id": str(row.id)},
            )


def downgrade() -> None:
    # Decrypt existing ciphertext back to plaintext
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT id, vehicle_vin, property_address, property_zip FROM accounts "
            "WHERE vehicle_vin IS NOT NULL "
            "   OR property_address IS NOT NULL "
            "   OR property_zip IS NOT NULL"
        )
    )
    rows = result.fetchall()

    if rows:
        from app.services.encryption_service import get_encryption_service

        svc = get_encryption_service()

        for row in rows:
            updates: dict = {}
            if row.vehicle_vin:
                try:
                    updates["vehicle_vin"] = svc.decrypt_token(row.vehicle_vin)
                except Exception:
                    updates["vehicle_vin"] = row.vehicle_vin  # already plaintext
            if row.property_address:
                try:
                    updates["property_address"] = svc.decrypt_token(row.property_address)
                except Exception:
                    updates["property_address"] = row.property_address
            if row.property_zip:
                try:
                    updates["property_zip"] = svc.decrypt_token(row.property_zip)
                except Exception:
                    updates["property_zip"] = row.property_zip

            if updates:
                set_clause = ", ".join(f"{k} = :{k}" for k in updates)
                bind.execute(
                    sa.text(f"UPDATE accounts SET {set_clause} WHERE id = :id"),
                    {**updates, "id": str(row.id)},
                )

    # Narrow columns back to their original types
    op.alter_column(
        "accounts",
        "vehicle_vin",
        type_=sa.String(length=17),
        existing_nullable=True,
    )
    op.alter_column(
        "accounts",
        "property_address",
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "accounts",
        "property_zip",
        type_=sa.String(length=10),
        existing_nullable=True,
    )
