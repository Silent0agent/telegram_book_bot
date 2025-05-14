import asyncio

from sqlalchemy import select

from database import models
from database.models import Genre


async def add_genrs(conn):
    result = await conn.execute(select(Genre))
    genres_exist = result.scalars().first()

    if genres_exist:
        return  # Жанры уже есть — выходим

    genres = [
        "Драма",
        "Фантастика",
        "Детектив",
        "Приключения",
        "Фэнтези",
        "Роман",
        "Исторический роман",
        "Триллер",
        "Ужасы",
        "Научная литература",
        "Биография",
        "Поэзия",
        "Юмор",
        "Психология",
        "Саморазвитие",
        "Классика",
        "Детская литература",
        "Мистика",
        "Научная фантастика",
        "Постапокалипсис"
    ]

    for i, el in enumerate(genres):
        genre = models.Genre()
        # genre.genre_id = (i + 1)
        genre.name = el
        conn.add(genre)
        await conn.commit()
