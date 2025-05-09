from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Book
from lexicon.lexicon import LEXICON


def create_choose_search_keyboard() -> InlineKeyboardMarkup:
    # Создаем объект клавиатуры
    kb_builder = InlineKeyboardBuilder()
    buttons = ['search_by_title_and_author', 'search_by_title', 'search_by_author', 'search_by_description',
               'search_by_genre', 'search_all']
    # Наполняем клавиатуру кнопками-закладками в порядке возрастания
    for button in buttons:
        kb_builder.row(InlineKeyboardButton(
            text=f'{LEXICON[button]}',
            callback_data=button
        ))
    return kb_builder.as_markup()


def create_found_keyboard(current_list_page, length_search_results, *books: Book, add_book=False) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    # Наполняем клавиатуру кнопками-закладками в порядке возрастания
    for i in range(len(books)):
        kb_builder.add(InlineKeyboardButton(
            text=f'{i + 1}',
            callback_data=f'view_book_{books[i].book_id}'
        ))
    pagination_buttons: list[InlineKeyboardButton] = []
    if current_list_page != 1:
        pagination_buttons.append(InlineKeyboardButton(text='<', callback_data='search_results_backward'))
    pagination_buttons.append(
        InlineKeyboardButton(text=f'{current_list_page}/{length_search_results}', callback_data='...'))
    if current_list_page != length_search_results:
        pagination_buttons.append(InlineKeyboardButton(text='>', callback_data='search_results_forward'))
    kb_builder.row(*pagination_buttons, width=3)
    if add_book:
        kb_builder.row(InlineKeyboardButton(text=LEXICON['add_book'], callback_data='add_book'))
    return kb_builder.as_markup()
