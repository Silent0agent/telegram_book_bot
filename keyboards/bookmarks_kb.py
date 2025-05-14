from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Bookmark
from lexicon.lexicon import LEXICON


def create_bookmarks_keyboard(*bookmarks: Bookmark) -> InlineKeyboardMarkup:
    # Создаем объект клавиатуры
    kb_builder = InlineKeyboardBuilder()
    # Наполняем клавиатуру кнопками-закладками в порядке возрастания
    for bookmark in sorted(bookmarks, key=lambda x: x.created_at, reverse=True):
        kb_builder.row(InlineKeyboardButton(
            text=f'{bookmark.book.title} - стр. {bookmark.page_number} - {bookmark.note}',
            callback_data=f'open_bookmark_{bookmark.bookmark_id}'
        ))
    # Добавляем в клавиатуру в конце две кнопки "Редактировать" и "Отменить"
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON['edit_bookmarks_button'],
            callback_data='edit_bookmarks'
        ),
        InlineKeyboardButton(
            text=LEXICON['cancel'],
            callback_data='cancel_bookmarks'
        ),
        width=2
    )
    return kb_builder.as_markup()


def create_edit_keyboard(*bookmarks: Bookmark) -> InlineKeyboardMarkup:
    # Создаем объект клавиатуры
    kb_builder = InlineKeyboardBuilder()
    # Наполняем клавиатуру кнопками-закладками в порядке возрастания
    for bookmark in bookmarks:
        kb_builder.row(InlineKeyboardButton(
            text=f'{LEXICON["del"]} {bookmark.book.title} - страница {bookmark.page_number} - {bookmark.note}',
            callback_data=f'delete_bookmark_{bookmark.bookmark_id}'
        ))
    # Добавляем в конец клавиатуры кнопку "Отменить"
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON['cancel'],
            callback_data='bookmarks'
        )
    )
    return kb_builder.as_markup()
