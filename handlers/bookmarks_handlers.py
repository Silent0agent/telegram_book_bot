from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Bookmark
from keyboards.bookmarks_kb import create_edit_keyboard
from keyboards.start_kb import create_start_keyboard
from lexicon.lexicon import LEXICON
from services.database_services import sqlite_get_bookmarks_with_books_by_user_id

router = Router()


@router.callback_query(F.data.in_(['edit_bookmarks', 'cancel_bookmarks']))
async def process_choose_bookmarks_operation(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    if callback.data == 'edit_bookmarks':
        bookmarks = await sqlite_get_bookmarks_with_books_by_user_id(session, callback.from_user.id)
        await callback.message.edit_text(LEXICON[callback.data], reply_markup=create_edit_keyboard(*bookmarks))
    elif callback.data == 'cancel_bookmarks':
        await callback.message.edit_text(LEXICON['/start'], reply_markup=create_start_keyboard())


@router.callback_query(F.data.startswith('delete_bookmark'))
async def process_delete_bookmark(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    bookmark_id = int(callback.data.split('_')[-1])
    bookmark = await session.scalar(select(Bookmark).where(Bookmark.bookmark_id == bookmark_id))
    await session.delete(bookmark)
    await session.commit()
    bookmarks = await sqlite_get_bookmarks_with_books_by_user_id(session, callback.from_user.id)
    if bookmarks:
        await callback.message.edit_text(LEXICON['edit_bookmarks'], reply_markup=create_edit_keyboard(*bookmarks))
    else:
        await callback.message.edit_text(LEXICON['no_bookmarks'])
