from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False, # атрибуты после коммита не устаревают 
)

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
        # session.close()