from math import ceil
from typing import Union
from aiogram import F, Router
from aiogram.filters import StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Book, Genre
from keyboards.genres_kb import create_genres_keyboard
from keyboards.search_kb import create_found_keyboard
from lexicon.lexicon import LEXICON
from services.database_services import sqlite_search_books_by_title, \
    sqlite_search_books_by_author, sqlite_get_books_by_genre, \
    sqlite_search_books_by_any_field, sqlite_search_books_by_description
from services.handlers_services import filter_public_books
from states.states import FSMSearchBook

router = Router()


@router.callback_query(F.data.startswith('search_by'))
async def process_choose_search(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    data = callback.data
    if data == 'search_by_title_and_author':
        await callback.message.answer(LEXICON['enter_title_and_author'])
        await state.set_state(FSMSearchBook.search_by_title_and_author)
    elif data == 'search_by_title':
        await callback.message.answer(LEXICON['enter_title'])
        await state.set_state(FSMSearchBook.search_by_title)
    elif data == 'search_by_author':
        await callback.message.answer(LEXICON['enter_author'])
        await state.set_state(FSMSearchBook.search_by_author)
    elif data == 'search_by_description':
        await callback.message.answer(LEXICON['enter_description'])
        await state.set_state(FSMSearchBook.search_by_description)
    elif data == 'search_by_genre':
        all_genres = await session.execute(select(Genre))
        all_genres = all_genres.scalars().all()
        if not all_genres:
            await callback.message.answer(LEXICON['no_genres_in_database'])
            await state.set_state(default_state)
            return
        genres_list_length = ceil(len(all_genres) / 16)
        new_message = await callback.message.answer(LEXICON['choose_genre'],
                                                    reply_markup=create_genres_keyboard([], 1, genres_list_length,
                                                                                        *all_genres[:16],
                                                                                        confirm_button=False))
        await state.update_data(search_by_genres={'current_page': 1,
                                                  'length': genres_list_length},
                                active_search_by_genres_message_id=new_message.message_id)
        await state.set_state(FSMSearchBook.search_by_genre)


@router.callback_query(StateFilter(FSMSearchBook.search_by_genre),
                       F.data.in_(['genres_list_forward', 'genres_list_backward']))
async def process_choose_genre(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    data = await state.get_data()

    active_search_by_genres_message_id = data.get("active_search_by_genres_message_id")
    if callback.message.message_id != active_search_by_genres_message_id:
        await callback.answer(LEXICON['old_message_alert'], show_alert=True)
        return

    search_by_genres_dict = data.get('search_by_genres')
    if not search_by_genres_dict:
        await callback.answer(LEXICON['search_error'])
        return
    if callback.data == 'genres_list_forward':
        search_by_genres_dict['current_page'] += 1
    elif callback.data == 'genres_list_backward':
        search_by_genres_dict['current_page'] -= 1
    genres_list_page = search_by_genres_dict['current_page']
    all_genres = await session.execute(select(Genre))
    if not all_genres:
        await callback.message.answer(LEXICON['no_genres_in_database'])
        await state.set_state(default_state)
        return
    all_genres = all_genres.scalars().all()
    await callback.message.edit_text(LEXICON['fill_genres'],
                                     reply_markup=create_genres_keyboard([],
                                                                         genres_list_page,
                                                                         search_by_genres_dict['length'],
                                                                         *all_genres[
                                                                          (genres_list_page - 1) * 16:(
                                                                                                              genres_list_page - 1) * 16 + 16],
                                                                         confirm_button=False))
    await state.update_data(search_by_genres=search_by_genres_dict)


@router.callback_query(or_f(F.data == 'search_user_books', F.data == 'search_all'))
async def process_search_all(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if callback.data == 'search_user_books':
        await state.set_state(FSMSearchBook.search_user_books)
    elif callback.data == 'search_all':
        await state.set_state(FSMSearchBook.search_all)
    await process_search(callback, state, session)


@router.message(or_f(StateFilter(FSMSearchBook.search_by_title_and_author),
                     StateFilter(FSMSearchBook.search_by_title),
                     StateFilter(FSMSearchBook.search_by_author),
                     StateFilter(FSMSearchBook.search_by_description)))
@router.callback_query(StateFilter(FSMSearchBook.search_by_genre), F.data.startswith('choose_genre'))
async def process_search(event: Union[Message, CallbackQuery], state: FSMContext, session: AsyncSession):
    search_user_books = False
    if isinstance(event, Message):
        message = event
        text = event.text
    else:
        await event.answer()
        message = event.message
        text = ''
    current_state = (await state.get_state()).split(':')[-1]
    if current_state == 'search_by_title_and_author':
        books = await sqlite_search_books_by_any_field(session, text)
    elif current_state == 'search_by_title':
        books = await sqlite_search_books_by_title(session, text)
    elif current_state == 'search_by_author':
        books = await sqlite_search_books_by_author(session, text)
    elif current_state == 'search_by_description':
        books = await sqlite_search_books_by_description(session, text)
    elif current_state == 'search_by_genre':
        genre_id = int(event.data.split('_')[-1])
        books = await sqlite_get_books_by_genre(session, genre_id)
        data = await state.get_data()
        if data.get('search_by_genres'):
            del data['search_by_genres']
        if data.get("active_search_by_genres_message_id"):
            del data['active_search_by_genres_message_id']
        await state.update_data(data)
    elif current_state == 'search_all':
        books = await session.execute(select(Book))
        books = books.scalars().all()
    elif current_state == 'search_user_books':
        books = await session.execute(select(Book).where(Book.uploader_id == event.from_user.id))
        books = books.scalars().all()
        search_user_books = True
    else:
        books = None
    books = await filter_public_books(books, event.from_user.id)
    if books:
        length_search_results = ceil(len(books) / 8)
        search_results_dict = {'books': books,
                               'current_page': 1,
                               'length': length_search_results,
                               'search_user_books': search_user_books}
        texts = [f'{LEXICON[f"enumeration_{i + 1}"]} {books[i].title}  - {books[i].author}' for i in range(len(books[:8]))]
        new_message = await message.answer('\n\n'.join(texts),
                                           reply_markup=create_found_keyboard(1, length_search_results, *books[:8],
                                                                              add_book=search_user_books))
        await state.update_data(search_results=search_results_dict,
                                active_search_results_message_id=new_message.message_id)
        await state.set_state(default_state)
    else:
        if current_state == 'search_all' or current_state == 'search_user_books':
            await message.answer(LEXICON['no_books_found'], reply_markup=
            InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text=LEXICON['add_book'], callback_data='add_book')]]))
            await state.set_state(default_state)
        else:
            await message.answer(LEXICON['no_books_found'])


@router.callback_query(F.data.in_(['search_results_backward', 'search_results_forward']))
async def process_move_search_results(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()

    active_search_results_message_id = data.get("active_search_results_message_id")
    if callback.message.message_id != active_search_results_message_id:
        await callback.answer(LEXICON['old_message_alert'], show_alert=True)
        return

    search_results_dict = data.get('search_results')

    if not search_results_dict:
        await callback.message.answer(LEXICON['search_error'])
        return

    if callback.data == 'search_results_backward':
        search_results_dict['current_page'] -= 1
    elif callback.data == 'search_results_forward':
        search_results_dict['current_page'] += 1
    current_list_page = search_results_dict['current_page']
    books = search_results_dict['books'][(current_list_page - 1) * 8:(current_list_page - 1) * 8 + 8]
    length_search_results = search_results_dict['length']
    texts = [f'{LEXICON[f"enumeration_{i + 1}"]} {books[i].title}  - {books[i].author}' for i in range(len(books))]
    await callback.message.edit_text('\n\n'.join(texts),
                                     reply_markup=create_found_keyboard(current_list_page, length_search_results,
                                                                        *books,
                                                                        add_book=search_results_dict[
                                                                            'search_user_books']))
