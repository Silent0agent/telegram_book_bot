import logging
from typing import Union
from aiogram import F, Router
from aiogram.filters import Command, or_f, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database.models import Bookmark, Book, Page, Review, Audiobook, book_genre
from keyboards.book_view_kb import create_book_view_keyboard
from keyboards.book_pagination_kb import create_book_pagination_keyboard
from lexicon.lexicon import LEXICON
from services.database_services import sqlite_get_total_book_pages, sqlite_get_page_by_book_id_and_page_num, \
    sqlite_get_bookmark_or_none, sqlite_get_book_with_genres_audio_reviews_by_book_id, \
    sqlite_get_audiobook_ids_by_book_id
from services.file_handling import load_cover, delete_book_files
from services.handlers_services import show_page

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith('delete_book_'))
async def process_delete_book(callback: CallbackQuery, session: AsyncSession):
    try:
        await callback.answer()
        book_id = int(callback.data.split('_')[-1])

        # Получаем книгу вместе со связанными объектами
        book = await session.scalar(
            select(Book)
            .where(Book.book_id == book_id)
        )

        if not book:
            await callback.message.answer(LEXICON['book_not_found'])
            return

        if book.uploader_id != callback.from_user.id:
            await callback.message.answer(LEXICON['no_access_to_delete_book'])
            return
        audiobook_ids = await sqlite_get_audiobook_ids_by_book_id(session, book_id)
        delete_book_files(book_id, audiobook_ids)

        # Удаляем связанные объекты явно
        await session.execute(delete(Bookmark).where(Bookmark.book_id == book_id))
        await session.execute(delete(Audiobook).where(Audiobook.book_id == book_id))
        await session.execute(delete(Review).where(Review.book_id == book_id))
        await session.execute(delete(Page).where(Page.book_id == book_id))
        await session.execute(delete(book_genre).where(book_genre.c.book_id == book_id))
        await session.delete(book)
        await session.commit()

        await callback.message.answer(LEXICON['book_delete_success'])

    except Exception as e:
        await session.rollback()
        logger.exception(f"Ошибка при удалении книги: {e}")
        await callback.message.answer('Произошла ошибка при удалении книги')


@router.callback_query(F.data.startswith('view_book'))
async def process_book_cover(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    book_id = int(callback.data.split('_')[-1])
    book_view = await sqlite_get_book_with_genres_audio_reviews_by_book_id(session, book_id)
    if not book_view:
        await callback.message.answer(LEXICON['book_not_found'])
        return
    genres_string = ', '.join([i.name for i in book_view.genres])
    if not genres_string:
        genres_string = 'Нет жанров'
    rating = book_view.average_rating
    if rating == 0.0:
        rating = 'Нет отзывов'
    else:
        rating = f"{round(rating, 2)} {LEXICON[f'rating_{round(rating)}']}"
    text = (f'Название: {book_view.title}\n'
            f'Автор: {book_view.author}\n'
            f'Описание: {book_view.description}\n'
            f'Жанры: {genres_string}\n'
            f'Рейтинг: {rating}')
    cover_file = await load_cover(book_view.book_id)
    review = await session.scalar(select(Review).where(
        Review.book_id == book_view.book_id,
        Review.user_id == callback.from_user.id
    ))
    is_user_book = book_view.uploader_id == callback.from_user.id
    await callback.message.answer_photo(
        photo=cover_file,
        caption=text,
        reply_markup=create_book_view_keyboard(book_view.book_id, is_user_book=is_user_book,
                                               user_review=review))


@router.callback_query(or_f(
    F.data.startswith('read_book'),
    F.data.startswith('open_bookmark')
))
async def process_book_or_bookmark(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession
):
    await callback.answer()

    try:
        # Определяем тип действия (чтение книги или открытие закладки)
        action = callback.data.split('_')[0]
        object_id = callback.data.split('_')[-1]
        object_id = int(object_id)

        if action == 'read':  # read_book_{book_id}
            # Режим открытия книги с первой страницы
            book_id = object_id
            page_num = 1
            bookmark = None
        else:  # open_bookmark_{bookmark_id}
            # Режим открытия закладки
            bookmark = await session.scalar(select(Bookmark).where(Bookmark.bookmark_id == object_id))
            if not bookmark:
                await callback.message.answer(LEXICON['bookmark_not_found'])
                return

            book_id = bookmark.book_id
            page_num = bookmark.page_number

        # Общая логика для обоих случаев
        book = await session.scalar(select(Book).where(Book.book_id == book_id))
        if not book:
            await callback.message.answer(LEXICON['book_not_found'])
            return

        total_pages = await sqlite_get_total_book_pages(session, book_id)
        if total_pages < 1:
            await callback.message.answer(LEXICON['no_pages_in_book'])
            return

        page = await sqlite_get_page_by_book_id_and_page_num(
            session,
            book_id, page_num
        )
        if not page:
            await callback.message.answer(f"❌ Страница {page_num} не найдена")
            return

        # Проверяем актуальную закладку (если открываем не через закладку)
        if action == 'read':
            bookmark = await sqlite_get_bookmark_or_none(
                session,
                user_id=callback.from_user.id,
                book_id=book_id,
                page_number=page_num
            )

        # Создаем клавиатуру
        keyboard = create_book_pagination_keyboard(
            page_num,
            total_pages,
            bookmark
        )

        # Отправляем новое сообщение
        new_message = await callback.message.answer(
            text=page.text,
            reply_markup=keyboard
        )

        # Обновляем состояние
        await state.update_data(
            current_book={
                'book': book,
                'current_page': page_num,
                'total_pages': total_pages
            },
            active_reading_message_id=new_message.message_id
        )

    except ValueError as e:
        await callback.message.answer("⚠️ Неверный формат команды")
        logger.exception(e)
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
        await callback.message.answer("⚠️ Произошла ошибка")


@router.callback_query(F.data.in_(['book_backward', 'book_forward']))
async def process_current_book(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    data = await state.get_data()
    active_reading_message_id = data.get("active_reading_message_id")

    if callback.message.message_id != active_reading_message_id:
        await callback.answer(LEXICON['old_message_alert'], show_alert=True)
        return

    current_book_dict = data['current_book']
    if callback.data == 'book_backward':
        current_book_dict['current_page'] -= 1
    elif callback.data == 'book_forward':
        current_book_dict['current_page'] += 1
    current_page = current_book_dict['current_page']
    total_pages = current_book_dict['total_pages']
    book_id = current_book_dict['book'].book_id

    page = await sqlite_get_page_by_book_id_and_page_num(session, book_id, current_page)
    bookmark = await sqlite_get_bookmark_or_none(session, callback.from_user.id,
                                                 book_id, current_page)

    if not page:
        await callback.message.answer(LEXICON['page_not_found'])
        return

    await callback.message.edit_text(
        text=page.text,
        reply_markup=create_book_pagination_keyboard(current_page, total_pages, bookmark)
    )
    await state.update_data(current_book=current_book_dict)


@router.message(Command('page'))
@router.callback_query(F.data.startswith('page_'))
async def process_page(
        event: Union[Message, CallbackQuery],
        state: FSMContext,
        session: AsyncSession,
        command: CommandObject = None
):
    # Определяем номер страницы
    if isinstance(event, Message):
        if not command or not command.args or not command.args.isdigit():
            await event.answer(LEXICON['command_page_hint'])
            return
        page_num = int(command.args)
    else:
        page_num = int(event.data.split('_')[1])
        await event.answer()

    await show_page(event, page_num, state, session)


@router.callback_query(F.data == 'add_bookmark')
async def process_add_bookmark(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()

    active_reading_message_id = data.get("active_reading_message_id")
    if callback.message.message_id != active_reading_message_id:
        await callback.answer(LEXICON['old_message_alert'], show_alert=True)
        return

    current_book_dict = data['current_book']
    current_page = current_book_dict['current_page']
    total_pages = current_book_dict['total_pages']
    book_id = current_book_dict['book'].book_id
    page = await sqlite_get_page_by_book_id_and_page_num(session, book_id, current_book_dict['current_page'])
    if not page:
        await callback.message.answer(LEXICON['page_not_found'])
        return
    bookmark = Bookmark(user_id=callback.from_user.id,
                        book_id=book_id,
                        page_number=current_page,
                        note=page.text[:100])
    session.add(bookmark)
    await session.commit()
    await callback.message.edit_text(
        text=page.text,
        reply_markup=create_book_pagination_keyboard(current_page, total_pages, bookmark)
    )
    await state.update_data(current_book=current_book_dict)


@router.callback_query(F.data.startswith('book_delete_bookmark'))
async def process_delete_bookmark_in_book(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    bookmark_id = int(callback.data.split('_')[-1])
    bookmark = session.scalar(select(Bookmark).where(Bookmark.bookmark_id == bookmark_id))
    await session.delete(bookmark)
    await session.commit()
    data = await state.get_data()

    active_reading_message_id = data.get("active_reading_message_id")
    if callback.message.message_id != active_reading_message_id:
        await callback.answer(LEXICON['old_message_alert'], show_alert=True)
        return

    current_book_dict = data['current_book']
    current_page = current_book_dict['current_page']
    total_pages = current_book_dict['total_pages']
    book_id = current_book_dict['book'].book_id
    page = await sqlite_get_page_by_book_id_and_page_num(session, (book_id, current_book_dict['current_page']))

    if not page:
        await callback.message.answer(LEXICON['page_not_found'])
        return

    await callback.message.edit_text(
        text=page.text,
        reply_markup=create_book_pagination_keyboard(current_page, total_pages, None)
    )
    await state.update_data(current_book=current_book_dict)
