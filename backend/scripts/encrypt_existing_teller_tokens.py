#!/usr/bin/env python3
"""
One-time migration script to encrypt existing Teller access tokens.

This script:
1. Reads all TellerEnrollment records from the database
2. Checks if tokens are already encrypted (by attempting decryption)
3. Encrypts any plaintext tokens
4. Updates the database

Run this script after:
- Setting MASTER_ENCRYPTION_KEY in .env
- Deploying the encryption service code
- Before using the new encrypted token system

Usage:
    python scripts/encrypt_existing_teller_tokens.py

WARNING: Back up your database before running this script!
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.account import TellerEnrollment
from app.services.encryption_service import get_encryption_service


async def encrypt_existing_teller_tokens():
    """Encrypt all existing plaintext Teller access tokens."""
    print("=" * 80)
    print("ENCRYPTING EXISTING TELLER ACCESS TOKENS")
    print("=" * 80)
    print()

    # Check that encryption key is set
    if not settings.MASTER_ENCRYPTION_KEY:
        print("ERROR: MASTER_ENCRYPTION_KEY is not set in environment!")
        print("Generate a key using: python scripts/generate_encryption_key.py")
        return False

    # Create database connection
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    encryption_service = get_encryption_service()

    async with async_session() as session:
        # Get all TellerEnrollment records
        result = await session.execute(select(TellerEnrollment))
        teller_enrollments = result.scalars().all()

        total = len(teller_enrollments)
        print(f"Found {total} TellerEnrollment records")
        print()

        if total == 0:
            print("No TellerEnrollment records to process. Exiting.")
            return True

        encrypted_count = 0
        already_encrypted_count = 0
        error_count = 0

        for i, enrollment in enumerate(teller_enrollments, 1):
            print(f"Processing {i}/{total}: TellerEnrollment {enrollment.id}...", end=" ")

            try:
                # Check if already encrypted by attempting to decrypt
                try:
                    decrypted = encryption_service.decrypt_token(enrollment.access_token)
                    # If decryption succeeded, it's already encrypted
                    print("✓ Already encrypted")
                    already_encrypted_count += 1
                    continue
                except Exception:
                    # Decryption failed, assume it's plaintext
                    pass

                # Assume it's stored as bytes or string but not encrypted
                # Convert bytes to string if needed
                if isinstance(enrollment.access_token, bytes):
                    plaintext_token = enrollment.access_token.decode('utf-8')
                else:
                    plaintext_token = enrollment.access_token

                # Encrypt the token
                encrypted_token = encryption_service.encrypt_token(plaintext_token)

                # Update the record
                enrollment.access_token = encrypted_token
                await session.flush()

                print("✓ Encrypted")
                encrypted_count += 1

            except Exception as e:
                print(f"✗ ERROR: {e}")
                error_count += 1

        # Commit all changes
        if encrypted_count > 0:
            await session.commit()
            print()
            print("✓ Changes committed to database")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total records: {total}")
    print(f"Newly encrypted: {encrypted_count}")
    print(f"Already encrypted: {already_encrypted_count}")
    print(f"Errors: {error_count}")
    print("=" * 80)

    return error_count == 0


if __name__ == "__main__":
    success = asyncio.run(encrypt_existing_teller_tokens())
    sys.exit(0 if success else 1)
