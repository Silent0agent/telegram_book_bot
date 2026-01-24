__all__ = ()

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Review
from lexicon import LEXICON


def create_book_view_keyboard(
    book_id: int,
    is_user_book=False,
    user_review: Review | None = None,
) -> InlineKeyboardMarkup:
    # Создаем объект клавиатуры
    kb_builder = InlineKeyboardBuilder()
    # Наполняем клавиатуру кнопками-закладками в порядке возрастания
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON["read_book"],
            callback_data=f"read_book_{book_id}",
        ),
        InlineKeyboardButton(
            text=LEXICON["view_book_audiobooks"],
            callback_data=f"view_audiobooks_{book_id}",
        ),
    )
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON["add_audiobook"],
            callback_data=f"add_audiobook_{book_id}",
        ),
    )
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON["view_book_reviews"],
            callback_data=f"book_reviews_{book_id}",
        ),
    )
    if user_review:
        kb_builder.row(
            InlineKeyboardButton(
                text=LEXICON["user_review"],
                callback_data=f"view_user_review_{user_review.review_id}",
            ),
        )
    else:
        kb_builder.row(
            InlineKeyboardButton(
                text=LEXICON["create_review"],
                callback_data=f"create_review_{book_id}",
            ),
        )

    if is_user_book:
        kb_builder.row(
            InlineKeyboardButton(
                text=LEXICON["delete_book"],
                callback_data=f"delete_book_{book_id}",
            ),
        )

    return kb_builder.as_markup()
