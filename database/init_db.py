__all__ = ()

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Genre
from lexicon import DEFAULT_GENRES


async def init_genres(session: AsyncSession, force: bool = False):
    if not force:
        # Используем func.count() вместо .count()
        existing_count = await session.scalar(
            select(func.count()).select_from(Genre),
        )

        if existing_count > 0:
            return

    for genre_name in DEFAULT_GENRES:
        genre = Genre(name=genre_name)
        session.add(genre)

    await session.commit()
