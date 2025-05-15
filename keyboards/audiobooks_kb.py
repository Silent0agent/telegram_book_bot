from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.lexicon import LEXICON


def create_audiobooks_keyboard(current_list_page, list_length, audiobook, is_user_audiobook=False) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    inline_buttons = []
    if current_list_page != 1:
        inline_buttons.append(
            InlineKeyboardButton(text=LEXICON['pagination_backward'], callback_data='audiobooks_list_backward'))
    inline_buttons.append(InlineKeyboardButton(text=f"{current_list_page}/{list_length}",
                                               callback_data='...'))
    if current_list_page != list_length:
        inline_buttons.append(
            InlineKeyboardButton(text=LEXICON['pagination_forward'], callback_data='audiobooks_list_forward'))
    kb_builder.row(*inline_buttons, width=3)
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON['listen_audiobook'],
            callback_data=f'listen_audiobook_{audiobook.audiobook_id}'
        )
    )
    if is_user_audiobook:
        kb_builder.row(InlineKeyboardButton(text=LEXICON['delete_audiobook'],
                                        callback_data=f'delete_audiobook_{audiobook.audiobook_id}'))
    return kb_builder.as_markup()
