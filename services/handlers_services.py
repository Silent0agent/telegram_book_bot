from typing import Union

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.book_pagination_kb import create_book_pagination_keyboard
from services.database_services import sqlite_get_page_by_book_id_and_page_num, sqlite_get_bookmark_or_none


async def show_page(
        event: Union[Message, CallbackQuery],
        page_num: int,
        state: FSMContext,
        session: AsyncSession
):
    """Общая функция для отображения страницы книги"""
    data = await state.get_data()
    current_book_dict = data.get('current_book')

    if not current_book_dict:
        await event.answer("❌ Сначала откройте книгу")
        return None

    total_pages = current_book_dict['total_pages']
    if not 1 <= page_num <= total_pages:
        await event.answer(f"📖 В книге всего {total_pages} страниц")
        return None

    # Получаем данные страницы
    book_id = current_book_dict['book'].book_id
    page = await sqlite_get_page_by_book_id_and_page_num(session, book_id, page_num)
    if not page:
        await event.answer("❌ Страница не найдена")
        return None

    # Создаем клавиатуру
    bookmark = await sqlite_get_bookmark_or_none(
        session, event.from_user.id, book_id, page_num
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
        current_book={**current_book_dict, 'current_page': page_num}
    )

    return msg