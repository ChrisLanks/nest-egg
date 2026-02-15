#!/usr/bin/env python3
"""
Generate a Fernet encryption key for use as MASTER_ENCRYPTION_KEY.

Run this script to generate a new encryption key:
    python scripts/generate_encryption_key.py

Add the generated key to your .env file:
    MASTER_ENCRYPTION_KEY=<generated_key>

WARNING: Never commit this key to version control!
WARNING: Changing this key will break decryption of existing encrypted data!
"""

from cryptography.fernet import Fernet


def generate_key():
    """Generate a new Fernet encryption key."""
    key = Fernet.generate_key()
    return key.decode()


if __name__ == "__main__":
    key = generate_key()
    print("=" * 80)
    print("GENERATED ENCRYPTION KEY")
    print("=" * 80)
    print()
    print("Add this to your .env file:")
    print()
    print(f"MASTER_ENCRYPTION_KEY={key}")
    print()
    print("=" * 80)
    print("IMPORTANT SECURITY WARNINGS:")
    print("=" * 80)
    print("1. Never commit this key to version control")
    print("2. Store it securely (password manager, secrets manager)")
    print("3. Changing this key will break decryption of existing data")
    print("4. Back up this key in a secure location")
    print("5. Use a different key for development, staging, and production")
    print("=" * 80)
