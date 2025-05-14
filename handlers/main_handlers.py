from typing import Union
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from keyboards.bookmarks_kb import create_bookmarks_keyboard
from keyboards.search_kb import create_choose_search_keyboard
from keyboards.start_kb import create_start_keyboard
from lexicon.lexicon import LEXICON
from services.database_services import sqlite_get_bookmarks_with_books_by_user_id
from services.handlers_services import show_page

router = Router()


@router.message(CommandStart())
@router.callback_query(F.data == 'restart_bot')
async def process_start_command(event: Union[Message, CallbackQuery], state: FSMContext):
    if isinstance(event, Message):
        await event.answer(LEXICON['/start'], reply_markup=create_start_keyboard())
    else:
        await event.answer()
        await event.message.answer(LEXICON['/start'], reply_markup=create_start_keyboard())
    await state.set_state(default_state)


@router.message(Command(commands='help'))
async def process_help_command(message: Message):
    await message.answer(LEXICON[message.text])


@router.message(Command('bookmarks'))
@router.callback_query(F.data == 'bookmarks')
async def process_bookmarks(event: Union[Message, CallbackQuery], state: FSMContext, session: AsyncSession):
    bookmarks = await sqlite_get_bookmarks_with_books_by_user_id(session, event.from_user.id)
    if bookmarks:
        if isinstance(event, Message):
            await event.answer(LEXICON[event.text], reply_markup=create_bookmarks_keyboard(*bookmarks))
        else:
            await event.answer()
            await event.message.edit_text(LEXICON['/bookmarks'], reply_markup=create_bookmarks_keyboard(*bookmarks))
        await state.set_state(default_state)
    else:
        if isinstance(event, Message):
            await event.answer(LEXICON['no_bookmarks'])
        else:
            await event.answer()
            await event.message.answer(LEXICON['no_bookmarks'])


@router.message(Command('continue'))
async def process_continue_book(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    current_book_dict = data.get('current_book')

    if not current_book_dict:
        await message.answer(LEXICON['no_active_book'])
        return

    # Берем последнюю открытую страницу или начинаем с первой
    page_num = current_book_dict.get('current_page', 1)

    await show_page(message, page_num, state, session)

@router.message(Command('search'))
@router.callback_query(F.data == 'start_search')
async def process_start_search(event: Union[Message, CallbackQuery]):
    if isinstance(event, Message):
        await event.answer(LEXICON['choose_search'],
                                     reply_markup=create_choose_search_keyboard())
    else:
        await event.answer()
        await event.message.edit_text(LEXICON['choose_search'],
                                         reply_markup=create_choose_search_keyboard())
