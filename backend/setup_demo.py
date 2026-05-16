import asyncio
from app.models.database import AsyncSessionLocal as SessionLocal
from app.models.user import User
from sqlalchemy import select

async def setup_demo_user():
    async with SessionLocal() as db:
        query = select(User).where(User.username == "demo")
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            print("Demo user already exists. Resetting password to 'demo123'...")
            user.hashed_password = User.hash_password("demo123")
        else:
            print("Creating new demo user...")
            user = User(
                username="demo",
                email="demo@example.com",
                hashed_password=User.hash_password("demo123"),
                is_active=True,
                is_superuser=False
            )
            db.add(user)
        
        await db.commit()
        print("Demo user is ready!")
        print("Username: demo")
        print("Password: demo123")

if __name__ == "__main__":
    asyncio.run(setup_demo_user())
