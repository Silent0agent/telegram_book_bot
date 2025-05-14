from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Genre
from sqlalchemy import select

DEFAULT_GENRES = [
    # Художественная литература
    "Фантастика",
    "Фэнтези",
    "Детектив",
    "Триллер",
    "Ужасы",
    "Роман",
    "Приключения",
    "Исторический роман",
    "Любовный роман",
    "Мистика",

    # Классика и драма
    "Классическая литература",
    "Драма",
    "Поэзия",
    "Сказки",
    "Басни",

    # Научная и документальная
    "Научная фантастика",
    "Научно-популярная",
    "Биография",
    "Мемуары",
    "История",

    # Другие популярные
    "Психология",
    "Саморазвитие",
    "Бизнес",
    "Философия",
    "Юмор",

    # Поджанры фантастики/фэнтези
    "Киберпанк",
    "Постапокалипсис",
    "Городское фэнтези",
    "Космическая опера",
    "Альтернативная история",

    # Для детей и подростков
    "Детская литература",
    "Подростковая литература",
    "Молодежная проза",

    # Специфические
    "Нон-фикшн",
    "Путешествия",
    "Кулинария",
    "Искусство",
    "Спорт"
]


async def init_genres(session: AsyncSession):
    # Проверяем существующие жанры
    existing_genres = await session.scalars(select(Genre))
    existing_names = {genre.name for genre in existing_genres}

    # Добавляем отсутствующие
    for genre_name in DEFAULT_GENRES:
        if genre_name not in existing_names:
            session.add(Genre(name=genre_name))

    await session.commit()