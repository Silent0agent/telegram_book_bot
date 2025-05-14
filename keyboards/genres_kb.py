from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Genre
from lexicon.lexicon import LEXICON


def create_genres_keyboard(chosen_ids: list, current_list_page, list_length, *genres: Genre,
                           confirm_button=True) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for i in range(len(genres)):
        if genres[i].genre_id in chosen_ids:
            kb_builder.row(InlineKeyboardButton(
                text=f"{LEXICON['chosen']} {genres[i].name}",
                callback_data=f"remove_genre_{genres[i].genre_id}"))
        else:
            kb_builder.row(InlineKeyboardButton(
                text=genres[i].name,
                callback_data=f"choose_genre_{genres[i].genre_id}"))
    kb_builder.adjust(2)
    inline_buttons = []
    if current_list_page != 1:
        inline_buttons.append(
            InlineKeyboardButton(text=LEXICON['pagination_backward'], callback_data='genres_list_backward'))
    inline_buttons.append(InlineKeyboardButton(text=f"{current_list_page}/{list_length}",
                                               callback_data='...'))
    if current_list_page != list_length:
        inline_buttons.append(
            InlineKeyboardButton(text=LEXICON['pagination_forward'], callback_data='genres_list_forward'))
    kb_builder.row(*inline_buttons, width=3)
    if confirm_button:
        kb_builder.row(
            InlineKeyboardButton(
                text=LEXICON['confirm_genres'],
                callback_data='confirm_genres'
            )
        )
    return kb_builder.as_markup()
