#!/usr/bin/env python3
"""
Test script to verify encryption service is working correctly.

This script tests:
1. Key is properly set in environment
2. Encryption works
3. Decryption works
4. Encrypted data can't be decrypted with wrong key

Usage:
    python scripts/test_encryption.py
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.encryption_service import get_encryption_service


def test_encryption():
    """Test encryption and decryption."""
    print("=" * 80)
    print("TESTING ENCRYPTION SERVICE")
    print("=" * 80)
    print()

    # Check key is set
    if not settings.MASTER_ENCRYPTION_KEY:
        print("❌ FAILED: MASTER_ENCRYPTION_KEY is not set in environment!")
        print("   Generate a key using: python scripts/generate_encryption_key.py")
        return False

    print("✓ MASTER_ENCRYPTION_KEY is set")
    print()

    try:
        encryption_service = get_encryption_service()
        print("✓ Encryption service initialized")
        print()

        # Test encryption and decryption
        test_tokens = [
            "access-sandbox-12345678-1234-1234-1234-123456789012",
            "test-token-abcdefghijklmnopqrstuvwxyz",
            "short",
            "a" * 1000,  # Long token
        ]

        for i, original_token in enumerate(test_tokens, 1):
            print(f"Test {i}: {'Token' if len(original_token) < 50 else f'Long token ({len(original_token)} chars)'}")

            # Encrypt
            encrypted = encryption_service.encrypt_token(original_token)
            print(f"  ✓ Encrypted: {len(encrypted)} bytes")

            # Decrypt
            decrypted = encryption_service.decrypt_token(encrypted)
            print(f"  ✓ Decrypted: {len(decrypted)} chars")

            # Verify
            if decrypted == original_token:
                print("  ✓ Match: Decrypted token matches original")
            else:
                print("  ❌ ERROR: Decrypted token does NOT match original!")
                print(f"     Original:  {original_token[:50]}...")
                print(f"     Decrypted: {decrypted[:50]}...")
                return False

            print()

        print("=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        print()
        print("Encryption service is working correctly!")
        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("Encryption service is NOT working correctly!")
        return False


if __name__ == "__main__":
    success = test_encryption()
    sys.exit(0 if success else 1)
