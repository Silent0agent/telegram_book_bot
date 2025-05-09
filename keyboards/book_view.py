from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Review


def create_book_view_keyboard(book_id: int, has_audio=False, is_user_book=False, user_review: Review | None=None) -> InlineKeyboardMarkup:
    # Создаем объект клавиатуры
    kb_builder = InlineKeyboardBuilder()
    # Наполняем клавиатуру кнопками-закладками в порядке возрастания
    kb_builder.row(InlineKeyboardButton(text='Читать', callback_data=f'read_book_{book_id}'),
                   InlineKeyboardButton(text='Смотреть отзывы', callback_data=f'book_reviews_{book_id}'))
    if has_audio:
        kb_builder.row(InlineKeyboardButton(text='Слушать аудио', callback_data='audio'))
    if user_review:
        kb_builder.row(InlineKeyboardButton(text='Ваш отзыв', callback_data=f'view_user_review_{user_review.review_id}'))
    else:
        kb_builder.row(InlineKeyboardButton(text='Оставить отзыв', callback_data=f'create_review_{book_id}'))
    if is_user_book:
        kb_builder.row(InlineKeyboardButton(text='Удалить книгу', callback_data=f'delete_book_{book_id}'))
    return kb_builder.as_markup()

