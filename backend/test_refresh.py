"""Debug script to test token refresh process."""
import asyncio
import hashlib
from app.core.database import async_session_factory
from app.core.security import decode_token
from app.crud.user import refresh_token_crud
from sqlalchemy import select, text

async def test_refresh():
    async with async_session_factory() as db:
        # Get most recent refresh token from database
        result = await db.execute(text("""
            SELECT token_hash, expires_at, revoked_at, created_at
            FROM refresh_tokens
            ORDER BY created_at DESC
            LIMIT 1
        """))
        token_row = result.first()

        if not token_row:
            print("No tokens found in database!")
            return

        print(f"Most recent token in DB:")
        print(f"  Hash (first 16 chars): {token_row[0][:16]}...")
        print(f"  Expires: {token_row[1]}")
        print(f"  Revoked: {token_row[2]}")
        print(f"  Created: {token_row[3]}")

        # Try to decode a token from localStorage (you'll need to paste it)
        print("\n" + "="*50)
        print("To test, copy refresh_token from browser localStorage")
        print("Then decode it to check JTI")
        print("="*50)

if __name__ == "__main__":
    asyncio.run(test_refresh())
