__all__ = ()

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Bookmark
from lexicon import LEXICON


# Функция, генерирующая клавиатуру для страницы книги
def create_book_pagination_keyboard(
    page_num,
    length_book,
    bookmark: Bookmark | None,
) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    pagination_buttons: list[InlineKeyboardButton] = []
    # Наполняем клавиатуру кнопками-закладками в порядке возрастания
    if page_num != 1:
        pagination_buttons.append(
            InlineKeyboardButton(
                text=LEXICON["pagination_backward"],
                callback_data="book_backward",
            ),
        )

    if bookmark:
        pagination_buttons.append(
            InlineKeyboardButton(
                text=f"{page_num}/{length_book} 🔖✅",
                callback_data=f"book_delete_bookmark_{bookmark.bookmark_id}",
            ),
        )
    else:
        pagination_buttons.append(
            InlineKeyboardButton(
                text=f"{page_num}/{length_book} 📌➕",
                callback_data="add_bookmark",
            ),
        )

    if page_num != length_book:
        pagination_buttons.append(
            InlineKeyboardButton(
                text=LEXICON["pagination_forward"],
                callback_data="book_forward",
            ),
        )

    kb_builder.row(*pagination_buttons, width=3)
    return kb_builder.as_markup()
