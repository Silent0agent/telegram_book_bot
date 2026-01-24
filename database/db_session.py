__all__ = ()

import importlib
import logging

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SqlAlchemyBase = declarative_base(cls=AsyncAttrs)

__async_factory = None
logger = logging.getLogger()


async def global_init(db_file: str):
    global __async_factory

    if __async_factory:
        return

    if not db_file or not db_file.strip():
        raise Exception("Specify database file.")

    # Для SQLite используем aiosqlite
    conn_str = f"sqlite+aiosqlite:///{db_file.strip()}"
    logger.info(
        f"Connecting to the database at the following address: {conn_str}",
    )

    engine = create_async_engine(
        conn_str,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )

    __async_factory = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        future=True,
    )

    async with engine.begin() as conn:
        importlib.import_module("database.models")

        await conn.run_sync(SqlAlchemyBase.metadata.create_all)


async def create_session() -> AsyncSession:
    if __async_factory is None:
        raise RuntimeError("Databese not initialized. Call global_init()")

    return __async_factory()
