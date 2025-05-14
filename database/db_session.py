import logging
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import AsyncAttrs

SqlAlchemyBase = declarative_base(cls=AsyncAttrs)

__async_factory = None
logger = logging.getLogger()


async def global_init(db_file: str):
    global __async_factory

    if __async_factory:
        return

    if not db_file or not db_file.strip():
        raise Exception("Необходимо указать файл базы данных.")

    # Для SQLite используем aiosqlite
    conn_str = f'sqlite+aiosqlite:///{db_file.strip()}'
    logger.info(f"Подключение к базе данных по адресу {conn_str}")

    engine = create_async_engine(
        conn_str,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False}
    )

    __async_factory = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        future=True
    )

    async with engine.begin() as conn:
        from . import models  # Импорт моделей перед созданием таблиц
        await conn.run_sync(SqlAlchemyBase.metadata.create_all)


async def create_session() -> AsyncSession:
    global __async_factory
    return __async_factory()
