import asyncio
from app.db.database import engine, Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных и таблицы созданы")

# Для прямого запуска через python -m
if __name__ == "__main__":
    asyncio.run(init_db())
