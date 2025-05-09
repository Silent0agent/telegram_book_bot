from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.lexicon import LEXICON

def create_start_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON['start_search'],
            callback_data='start_search'
        ),
        InlineKeyboardButton(
            text=LEXICON['search_user_books'],
            callback_data='search_user_books'
        ),
        InlineKeyboardButton(
            text=LEXICON['user_bookmarks'],
            callback_data='bookmarks'
        ),
        InlineKeyboardButton(
            text=LEXICON['user_reviews'],
            callback_data='user_reviews'
        ),
        width=1
    )
    return kb_builder.as_markup()