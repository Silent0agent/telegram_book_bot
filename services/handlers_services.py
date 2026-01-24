__all__ = ()

from typing import Union

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Book
from keyboards.book_pagination_kb import create_book_pagination_keyboard
from lexicon import LEXICON
from services.database_services import (
    sqlite_get_bookmark_or_none,
    sqlite_get_page_by_book_id_and_page_num,
)


async def show_page(
    event: Union[Message, CallbackQuery],
    page_num: int,
    state: FSMContext,
    session: AsyncSession,
):
    """Общая функция для отображения страницы книги"""
    data = await state.get_data()
    current_book_dict = data.get("current_book")

    if not current_book_dict:
        await event.answer(LEXICON["open_the_book_first"])
        return None

    total_pages = current_book_dict["total_pages"]
    if not 1 <= page_num <= total_pages:
        await event.answer(
            LEXICON["book_pages_amount"].format(total_pages=total_pages),
        )
        return None

    # Получаем данные страницы
    book_id = current_book_dict["book"].book_id
    page = await sqlite_get_page_by_book_id_and_page_num(
        session,
        book_id,
        page_num,
    )
    if not page:
        await event.answer(LEXICON["page_not_found"])
        return None

    # Создаем клавиатуру
    bookmark = await sqlite_get_bookmark_or_none(
        session,
        event.from_user.id,
        book_id,
        page_num,
    )
    keyboard = create_book_pagination_keyboard(page_num, total_pages, bookmark)

    # Отправляем сообщение
    if isinstance(event, CallbackQuery):
        msg = await event.message.answer(page.text, reply_markup=keyboard)
    else:
        msg = await event.answer(page.text, reply_markup=keyboard)

    # Обновляем состояние
    await state.update_data(
        active_reading_message_id=msg.message_id,
        current_book={**current_book_dict, "current_page": page_num},
    )

    return msg


async def filter_public_book(book: Book, user_id: int) -> bool:
    if not book.is_public and book.uploader_id != user_id:
        return False

    return True


async def filter_public_books(books: list[Book], user_id: int) -> list[Book]:
    filtered_books = []
    for book in books:
        if await filter_public_book(book, user_id):
            filtered_books.append(book)

    return filtered_books
