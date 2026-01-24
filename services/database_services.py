__all__ = ()

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.models import Audiobook, Book, Bookmark, Genre, Page, Review


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    return (
        text.lower()
        .replace("ё", "е")
        .translate(str.maketrans("", "", "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"))
    )


def _process_search_query(query: str) -> list[str]:
    """Обрабатывает поисковый запрос: нормализует и разбивает на слова."""
    normalized_query = (
        query.lower()
        .replace("ё", "е")
        .translate(str.maketrans("", "", "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"))
        .strip()
    )

    return [word for word in normalized_query.split() if word]


async def _filter_books_by_fields(
    session: AsyncSession,
    search_words: list[str],
    fields: list[str],
    skip_if_empty: bool = False,
) -> list[Book]:
    if not search_words:
        return []

    # Получаем все книги
    all_books = (await session.execute(select(Book))).scalars().all()

    results = []
    for book in all_books:
        # Собираем нормализованные значения полей
        field_values = []

        for field in fields:
            value = getattr(book, field)

            # Пропускаем пустые поля, если требуется
            if skip_if_empty and not value:
                continue

            field_values.append(normalize_text(value))

        # Пропускаем книгу, если все поля пустые
        if not field_values:
            continue

        # Объединяем все поля в одну строку для поиска
        book_data = " ".join(field_values)

        # Проверяем, содержатся ли ВСЕ слова запроса где-то в данных книги
        if all(word in book_data for word in search_words):
            results.append(book)

    return results


async def sqlite_search_books_by_any_field(session: AsyncSession, query: str):
    """Поиск по названию ИЛИ автору."""
    search_words = _process_search_query(query)
    return await _filter_books_by_fields(
        session=session,
        search_words=search_words,
        fields=["title", "author"],
    )


async def sqlite_search_books_by_title(session: AsyncSession, query: str):
    """Поиск только по названию."""
    search_words = _process_search_query(query)
    return await _filter_books_by_fields(
        session=session,
        search_words=search_words,
        fields=["title"],
    )


async def sqlite_search_books_by_author(session: AsyncSession, query: str):
    """Поиск только по автору."""
    search_words = _process_search_query(query)
    return await _filter_books_by_fields(
        session=session,
        search_words=search_words,
        fields=["author"],
    )


async def sqlite_search_books_by_description(
    session: AsyncSession,
    query: str,
):
    """Поиск только по описанию."""
    search_words = _process_search_query(query)
    return await _filter_books_by_fields(
        session=session,
        search_words=search_words,
        fields=["description"],
        skip_if_empty=True,  # Пропускаем книги без описания
    )


# Остальные функции остаются без изменений...
async def sqlite_get_book_with_pages_by_book_id(
    session: AsyncSession,
    book_id: int,
):
    stmt = (
        select(Book)
        .where(Book.book_id == book_id)
        .options(joinedload(Book.pages))
    )

    result = await session.execute(stmt)
    return result.scalars().first()


async def sqlite_get_book_with_genres_audio_reviews_by_book_id(
    session: AsyncSession,
    book_id: int,
):
    return await session.scalar(
        select(Book)
        .options(
            selectinload(Book.genres),
            selectinload(Book.audiobooks),
            selectinload(Book.reviews),
        )
        .where(Book.book_id == book_id),
    )


async def sqlite_get_total_book_pages(session: AsyncSession, book_id: int):
    return await session.scalar(
        select(func.count(Page.page_id)).where(Page.book_id == book_id),
    )


async def sqlite_get_bookmarks_with_books_by_user_id(
    session: AsyncSession,
    user_id: int,
):
    bookmarks = await session.execute(
        select(Bookmark)
        .options(selectinload(Bookmark.book))
        .where(Bookmark.user_id == user_id),
    )
    return bookmarks.scalars().all()


async def sqlite_get_page_by_book_id_and_page_num(
    session: AsyncSession,
    book_id: int,
    page_num: int,
):
    return await session.scalar(
        select(Page).where(
            (Page.book_id == book_id) & (Page.num == page_num),
        ),
    )


async def sqlite_get_bookmark_or_none(
    session: AsyncSession,
    user_id: int,
    book_id: int,
    page_number: int,
) -> Bookmark | None:
    result = await session.execute(
        select(Bookmark).where(
            (Bookmark.user_id == user_id)
            & (Bookmark.book_id == book_id)
            & (Bookmark.page_number == page_number),
        ),
    )
    return result.scalar_one_or_none()


async def sqlite_get_books_by_genre(
    session: AsyncSession,
    genre_id: int,
) -> list[Book]:
    stmt = (
        select(Book)
        .join(Book.genres)
        .where(Genre.genre_id == genre_id)
        .options(joinedload(Book.genres))
    )

    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def sqlite_get_reviews_with_users_book_by_book_id(
    session: AsyncSession,
    book_id: int,
) -> list[Review]:
    result = await session.execute(
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.book_id == book_id),
    )
    return result.scalars().all()


async def sqlite_get_reviews_with_user_books_by_user_id(
    session: AsyncSession,
    user_id: int,
) -> list[Review]:
    result = await session.execute(
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.user_id == user_id),
    )
    return result.scalars().all()


async def sqlite_get_review_with_user_book_by_review_id(
    session: AsyncSession,
    review_id: int,
):
    return await session.scalar(
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.review_id == review_id),
    )


async def sqlite_get_audiobooks_with_book_user_by_uploader_id(
    session: AsyncSession,
    uploader_id: int,
):
    result = await session.execute(
        select(Audiobook)
        .options(
            selectinload(Audiobook.uploader),
            selectinload(Audiobook.book),
        )
        .where(
            Audiobook.uploader_id == uploader_id,
            Audiobook.audio_url.is_not(None),
        ),
    )
    return result.scalars().all()


async def sqlite_get_audiobooks_with_book_user_by_book_id(
    session: AsyncSession,
    book_id: int,
):
    result = await session.execute(
        select(Audiobook)
        .options(
            selectinload(Audiobook.uploader),
            selectinload(Audiobook.book),
        )
        .where(Audiobook.book_id == book_id, Audiobook.audio_url.is_not(None)),
    )
    return result.scalars().all()


async def sqlite_get_audiobook_with_book_user_by_audiobook_id(
    session: AsyncSession,
    audiobook_id,
):
    return await session.scalar(
        select(Audiobook)
        .options(
            selectinload(Audiobook.uploader),
            selectinload(Audiobook.book),
        )
        .where(
            Audiobook.audiobook_id == audiobook_id,
            Audiobook.audio_url.is_not(None),
        ),
    )


async def sqlite_get_audiobook_ids_by_book_id(
    session: AsyncSession,
    book_id: int,
) -> list[int]:
    result = await session.execute(
        select(Audiobook.audiobook_id).where(
            Audiobook.book_id == book_id,
            Audiobook.audio_url.is_not(None),
        ),
    )
    return [row[0] for row in result.all()]
