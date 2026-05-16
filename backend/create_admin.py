import asyncio
from app.models.database import AsyncSessionLocal as SessionLocal, init_db
from app.models.user import User
from sqlalchemy import select

async def create_admin():
    async with SessionLocal() as db:
        # Check if admin exists
        query = select(User).where(User.username == "admin")
        result = await db.execute(query)
        admin = result.scalar_one_or_none()
        
        if admin:
            print("Admin already exists. Resetting password to 'admin123'...")
            admin.hashed_password = User.hash_password("admin123")
        else:
            print("Creating new admin user...")
            admin = User(
                username="admin",
                email="admin@example.com",
                hashed_password=User.hash_password("admin123"),
                is_active=True,
                is_superuser=True
            )
            db.add(admin)
        
        await db.commit()
        print("Admin user is ready!")
        print("Username: admin")
        print("Password: admin123")

if __name__ == "__main__":
    asyncio.run(create_admin())
