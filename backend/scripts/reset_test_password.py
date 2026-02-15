"""Reset password for test@test.com user."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, init_db
from app.models.user import User
from app.core.security import hash_password


async def reset_test_password():
    """Reset password for test@test.com to 'password'."""
    await init_db()

    async with AsyncSessionLocal() as db:
        # Find test user
        result = await db.execute(
            select(User).where(User.email == "test@test.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("❌ test@test.com user not found")
            return

        # Reset password to 'test1234'
        new_password = "test1234"
        user.password_hash = hash_password(new_password)
        await db.commit()

        print("✅ Password reset successfully!")
        print(f"   Email: test@test.com")
        print(f"   Password: {new_password}")


if __name__ == "__main__":
    asyncio.run(reset_test_password())
