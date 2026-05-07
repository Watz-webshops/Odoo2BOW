"""
Gebruik: python scripts/create_admin.py admin@example.com geheim-wachtwoord
Maak een eerste admin user aan in de database.
"""
import asyncio
import sys

from sqlalchemy import select

sys.path.insert(0, ".")

from app.core.security import hash_password
from app.database import AsyncSessionLocal
from app.models.admin_user import AdminUser


async def create_admin(email: str, password: str) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(AdminUser).where(AdminUser.email == email))
        if existing.scalar_one_or_none():
            print(f"Admin '{email}' bestaat al.")
            return

        admin = AdminUser(email=email, password_hash=hash_password(password))
        db.add(admin)
        await db.commit()
        print(f"Admin '{email}' aangemaakt.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Gebruik: python scripts/create_admin.py <email> <wachtwoord>")
        sys.exit(1)
    asyncio.run(create_admin(sys.argv[1], sys.argv[2]))
