"""
Database connection and session management for TodoApp Backend API.

This module provides async database connectivity using SQLModel and asyncpg,
with proper connection pooling and session management.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from src.config import settings


# Create async engine with connection pooling
engine = create_async_engine(
    settings.get_database_url(),
    echo=settings.debug,  # Log SQL queries in debug mode
    future=True,
    pool_size=5,  # Maximum number of connections in the pool
    max_overflow=10,  # Maximum overflow connections
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create async session factory
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    This function is used as a FastAPI dependency to provide database
    sessions to route handlers. It ensures proper session lifecycle
    management with automatic cleanup.

    Yields:
        AsyncSession: Database session for executing queries

    Example:
        ```python
        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(get_session)):
            result = await session.execute(select(User))
            return result.scalars().all()
        ```
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in SQLModel models. This should be called
    on application startup in development. In production, use Alembic
    migrations instead.

    Note:
        This function should only be used for development and testing.
        Production deployments should use Alembic migrations.

    Raises:
        Exception: If database initialization fails
    """
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered
        from src.models import Task, User  # noqa: F401
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.

    Disposes of the database engine and closes all connections.
    This should be called on application shutdown to ensure
    graceful cleanup of database resources.

    Raises:
        Exception: If connection cleanup fails
    """
    await engine.dispose()
