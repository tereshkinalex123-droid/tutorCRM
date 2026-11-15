import pytest 
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import URL

from app.config import settings
from app.models import BaseModel

TEST_DB_NAME = "crm_test"

TEST_DB_URL = URL.create(
    "postgresql+asyncpg",
    username=settings.postgres_user,
    password=settings.postgres_password,
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=TEST_DB_NAME,
)

@pytest.fixture()
async def session_factory():
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)

    async with engine.connect() as conn:                 
        db_name = (await conn.execute(text("SELECT current_database()"))).scalar_one()
    assert db_name == TEST_DB_NAME, f"Опасно: подключены к {db_name}"

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
        await conn.run_sync(BaseModel.metadata.create_all)

    yield async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
    await engine.dispose()