from sqlalchemy.orm import joinedload, selectinload
from database.models import Book, Page, Bookmark, Genre, Review, Audiobook
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


async def sqlite_search_books_by_any_field(session: AsyncSession, query: str):
    # Нормализация запроса
    normalized_query = (
        query.lower()
        .replace("ё", "е")
        .translate(str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
        .strip()
    )

    # Разбиваем на отдельные слова
    search_words = [word for word in normalized_query.split() if word]

    if not search_words:
        return []

    # Получаем все книги
    all_books = (await session.execute(select(Book))).scalars().all()

    results = []
    for book in all_books:
        # Нормализуем название и автора одинаковым способом
        title_normalized = (
            (book.title or "").lower()
            .replace("ё", "е")
            .translate(str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
        )

        author_normalized = (
            (book.author or "").lower()
            .replace("ё", "е")
            .translate(str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
        )

        # Объединяем все данные книги в одну строку для поиска
        book_data = f"{title_normalized} {author_normalized}"

        # Проверяем, содержатся ли ВСЕ слова запроса где-то в данных книги
        if all(word in book_data for word in search_words):
            results.append(book)

    return results


async def sqlite_search_books_by_title(session: AsyncSession, query: str):
    # Нормализация запроса
    normalized_query = (
        query.lower()
        .replace("ё", "е")
        .translate(str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
        .strip()
    )

    # Разбиваем на слова
    search_words = [word for word in normalized_query.split() if word]

    if not search_words:
        return []

    # Получаем ВСЕ книги из базы
    all_books = (await session.execute(select(Book))).scalars().all()

    # Фильтруем локально в Python
    result = []
    for book in all_books:
        # Нормализуем название книги
        title_normalized = (
            book.title.lower()
            .replace("ё", "е")
            .translate(str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
            .strip()
        )

        # Проверяем, содержатся ли все слова поиска в названии
        if all(word in title_normalized for word in search_words):
            result.append(book)

    return result


async def sqlite_search_books_by_author(session: AsyncSession, query: str):
    # Нормализация запроса
    normalized_query = (
        query.lower()
        .replace("ё", "е")
        .translate(str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
        .strip()
    )

    # Разбиваем на слова
    search_words = [word for word in normalized_query.split() if word]

    if not search_words:
        return []

    # Получаем ВСЕ книги из базы
    all_books = (await session.execute(select(Book))).scalars().all()

    # Фильтруем локально в Python
    result = []
    for book in all_books:
        # Нормализуем название книги
        title_normalized = (
            book.author.lower()
            .replace("ё", "е")
            .translate(str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
            .strip()
        )

        # Проверяем, содержатся ли все слова поиска в названии
        if all(word in title_normalized for word in search_words):
            result.append(book)

    return result


async def sqlite_search_books_by_description(session: AsyncSession, query: str):
    # Нормализация запроса
    normalized_query = (
        query.lower()
        .replace("ё", "е")
        .translate(str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
        .strip()
    )

    # Разбиваем на слова
    search_words = [word for word in normalized_query.split() if word]

    if not search_words:
        return []

    # Получаем ВСЕ книги из базы
    all_books = (await session.execute(select(Book))).scalars().all()

    # Фильтруем локально в Python
    result = []
    for book in all_books:
        if not book.description:  # Пропускаем книги без описания
            continue

        # Нормализуем описание книги
        description_normalized = (
            book.description.lower()
            .replace("ё", "е")
            .translate(str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'))
            .strip()
        )

        # Проверяем, содержатся ли все слова поиска в описании
        if all(word in description_normalized for word in search_words):
            result.append(book)

    return result


async def sqlite_get_book_with_pages_by_book_id(session: AsyncSession, book_id: int):
    stmt = (
        select(Book)
        .where(Book.book_id == book_id)
        .options(joinedload(Book.pages))  # Загружаем связанные страницы сразу
    )

    result = await session.execute(stmt)
    book = result.scalars().first()
    return book


async def sqlite_get_book_with_genres_audio_reviews_by_book_id(session: AsyncSession, book_id: int):
    book = await session.scalar(
        select(Book)
        .options(selectinload(Book.genres),
                 selectinload(Book.audiobooks),
                 selectinload(Book.reviews))  # Явная загрузка жанров
        .where(Book.book_id == book_id)
    )
    return book


async def sqlite_get_total_book_pages(session: AsyncSession, book_id: int):
    total_pages = await session.scalar(
        select(func.count(Page.page_id))
        .where(Page.book_id == book_id)
    )
    return total_pages


async def sqlite_get_bookmarks_with_books_by_user_id(session: AsyncSession, user_id: int):
    bookmarks = await session.execute(
        select(Bookmark).options(selectinload(Bookmark.book)).where(Bookmark.user_id == user_id))
    return bookmarks.scalars().all()


async def sqlite_get_page_by_book_id_and_page_num(session: AsyncSession, book_id: int, page_num: int):
    page = await session.scalar(
        select(Page)
        .where(
            (Page.book_id == book_id) &
            (Page.num == page_num)  # Используем уже вычисленное значение
        )
    )
    return page


async def sqlite_get_bookmark_or_none(
        session: AsyncSession,
        user_id: int,
        book_id: int,
        page_number: int
) -> Bookmark | None:
    """
    Находит конкретную закладку пользователя для указанной книги и страницы.

    Args:
        session: Асинхронная сессия SQLAlchemy
        user_id: ID пользователя
        book_id: ID книги
        page_number: Номер страницы

    Returns:
        Bookmark | None: Объект закладки или None, если не найден
    """
    result = await session.execute(
        select(Bookmark)
        .where(
            (Bookmark.user_id == user_id) &
            (Bookmark.book_id == book_id) &
            (Bookmark.page_number == page_number)
        )
    )
    return result.scalar_one_or_none()


async def sqlite_get_books_by_genre(session: AsyncSession, genre_id: int) -> list[Book]:
    """Поиск книг по ID жанра с жадной загрузкой"""
    stmt = (
        select(Book)
        .join(Book.genres)
        .where(Genre.genre_id == genre_id)
        .options(joinedload(Book.genres)))  # Жадная загрузка жанров

    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def sqlite_get_reviews_with_users_book_by_book_id(session: AsyncSession, book_id: int) -> list[Review]:
    result = await session.execute(
        select(Review).options(selectinload(Review.user), selectinload(Review.book)).where(Review.book_id == book_id))
    return result.scalars().all()


async def sqlite_get_reviews_with_user_books_by_user_id(session: AsyncSession, user_id: int) -> list[Review]:
    result = await session.execute(
        select(Review).options(selectinload(Review.user), selectinload(Review.book)).where(Review.user_id == user_id))
    return result.scalars().all()


async def sqlite_get_review_with_user_book_by_review_id(session: AsyncSession, review_id: int):
    result = await session.scalar(select(Review).options(selectinload(Review.user), selectinload(Review.book)).where(
        Review.review_id == review_id))
    return result


async def sqlite_get_audiobooks_with_book_user_by_uploader_id(session: AsyncSession, uploader_id: int):
    result = await session.execute(
        select(Audiobook).options(selectinload(Audiobook.uploader), selectinload(Audiobook.book)).where(
            Audiobook.uploader_id == uploader_id, Audiobook.audio_url.is_not(None)))
    return result.scalars().all()


async def sqlite_get_audiobooks_with_book_user_by_book_id(session: AsyncSession, book_id: int):
    result = await session.execute(
        select(Audiobook).options(selectinload(Audiobook.uploader), selectinload(Audiobook.book)).where(
            Audiobook.book_id == book_id, Audiobook.audio_url.is_not(None)))
    return result.scalars().all()


async def sqlite_get_audiobook_with_book_user_by_audiobook_id(session: AsyncSession, audiobook_id):
    return await session.scalar(
        select(Audiobook).options(selectinload(Audiobook.uploader), selectinload(Audiobook.book)).where(
            Audiobook.audiobook_id == audiobook_id, Audiobook.audio_url.is_not(None)))


async def sqlite_get_audiobook_ids_by_book_id(session: AsyncSession, book_id: int) -> list[int]:
    result = await session.execute(
        select(Audiobook.audiobook_id)
        .where(Audiobook.book_id == book_id, Audiobook.audio_url.is_not(None))
    )
    return [row[0] for row in result.all()]
