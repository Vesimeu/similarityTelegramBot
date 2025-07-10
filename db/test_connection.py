import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models.user import User, UserPreference, UserVisibility, UserSocialLink, UserInterest, Photo
from models.poll import Poll, PollAnswer
from models.admin import AdminSetting, AdminVisibleField

# Замените на свой DSN PostgreSQL
DATABASE_URL = "postgresql+asyncpg://postgres:123123@localhost:5432/postgres"

async def test_db():
    engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        print("Создаю все таблицы...")
        await conn.run_sync(Base.metadata.create_all)
        print("Таблицы успешно созданы!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_db()) 