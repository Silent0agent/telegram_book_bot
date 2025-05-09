from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.lexicon import LEXICON


def create_reviews_keyboard(current_list_page, list_length, review, is_user_review=False) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    inline_buttons = []
    if current_list_page != 1:
        inline_buttons.append(InlineKeyboardButton(text='<', callback_data='reviews_list_backward'))
    inline_buttons.append(InlineKeyboardButton(text=f"{current_list_page}/{list_length}",
                                               callback_data='...'))
    if current_list_page != list_length:
        inline_buttons.append(InlineKeyboardButton(text='>', callback_data='reviews_list_forward'))
    kb_builder.row(*inline_buttons, width=3)
    if is_user_review:
        kb_builder.row(
            InlineKeyboardButton(
                text=LEXICON['redact_review'],
                callback_data=f'create_review_{review.book_id}'
            )
        )
        kb_builder.row(InlineKeyboardButton(text='Удалить отзыв', callback_data=f'delete_review_{review.review_id}'))
    return kb_builder.as_markup()
