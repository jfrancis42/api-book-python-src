"""Async SQLAlchemy setup for PostgreSQL (Chapter 37).

Requires: pip install asyncpg sqlalchemy[asyncio]
Set DATABASE_URL environment variable or edit the default below.
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://minigithub:password@localhost/minigithub",
)

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
