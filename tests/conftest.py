import pytest 
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import URL
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.models import BaseModel, User
from app.database import get_db
from app.main import app
from app.auth import get_current_user

from factories import  create_tutor_student


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

@pytest.fixture
async def tutor_student(session_factory):
    async with session_factory() as db:
        tutor_id, student_id = await create_tutor_student(db)
    return tutor_id, student_id

@pytest.fixture
async def client(session_factory, tutor_student):
    tutor_id, _ = tutor_student

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def override_current_user() -> User:
        async with session_factory() as db:
            return await db.get(User, tutor_id)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()