import logging
from aiogram import F, Router
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Book, Review
from keyboards.reviews_kb import create_reviews_keyboard
from lexicon.lexicon import LEXICON
from services.database_services import sqlite_get_reviews_with_users_book_by_book_id, \
    sqlite_get_reviews_with_user_books_by_user_id, sqlite_get_review_with_user_book_by_review_id
from states.states import FSMCreateReview

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(or_f(F.data.startswith('book_reviews'),
                            F.data == 'user_reviews'))
async def process_book_review(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    if callback.data == 'user_reviews':
        reviews = await sqlite_get_reviews_with_user_books_by_user_id(session, callback.from_user.id)
        if not reviews:
            await callback.message.answer(LEXICON['no_user_reviews'])
            return
    elif callback.data.startswith('book_reviews'):
        book_id = int(callback.data.split('_')[-1])
        book = await session.scalar(
            select(Book)
            .where(Book.book_id == book_id)
        )
        if not book:
            await callback.message.answer(LEXICON['book_not_found'])
            return
        reviews = await sqlite_get_reviews_with_users_book_by_book_id(session, book_id)
        if not reviews:
            await callback.message.answer(LEXICON['no_book_reviews'])
            return

    reviews_results_dict = {'reviews': reviews,
                            'current_page': 1,
                            }
    review = reviews[0]
    rating = review.rating
    rating = f"{round(rating, 2)} {LEXICON[f'rating_{round(rating)}']}"
    review_uploader = review.user
    is_user_review = review.user_id == callback.from_user.id
    new_message = await callback.message.answer(
        f"Пользователь: {review_uploader.first_name} {review_uploader.last_name}\n"
        f"Книга: {review.book.author} — {review.book.title}\n"
        f"Оценка: {rating}\n"
        f"Мнение о книге: {review.text}",
        reply_markup=create_reviews_keyboard(1, len(reviews), review,
                                             is_user_review=is_user_review))
    await state.update_data(reviews_results=reviews_results_dict,
                            active_review_results_message_id=new_message.message_id)


@router.callback_query(F.data.in_(['reviews_list_backward', 'reviews_list_forward']))
async def process_move_reviews_list(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    active_review_results_message_id = data.get("active_review_results_message_id")

    if callback.message.message_id != active_review_results_message_id:
        await callback.answer(LEXICON['old_message_alert'], show_alert=True)
        return

    reviews_results_dict = data['reviews_results']
    if callback.data == 'reviews_list_backward':
        reviews_results_dict['current_page'] -= 1
    elif callback.data == 'reviews_list_forward':
        reviews_results_dict['current_page'] += 1
    current_page = reviews_results_dict['current_page']
    review = reviews_results_dict['reviews'][current_page - 1]
    if not review:
        await callback.message.answer(LEXICON['review_not_found'])
        return
    rating = review.rating
    rating = f"{round(rating, 2)} {LEXICON[f'rating_{round(rating)}']}"
    review_uploader = review.user
    is_user_review = review.user_id == callback.from_user.id
    new_message = await callback.message.edit_text(
        f"Пользователь: {review_uploader.first_name} {review_uploader.last_name}\n"
        f"Книга: {review.book.author} — {review.book.title}\n"
        f"Оценка: {rating}\n"
        f"Мнение о книге: {review.text}",
        reply_markup=create_reviews_keyboard(current_page, len(reviews_results_dict['reviews']), review,
                                             is_user_review=is_user_review))
    await state.update_data(reviews_results=reviews_results_dict,
                            active_review_results_message_id=new_message.message_id)


@router.callback_query(F.data.startswith('view_user_review'))
async def process_view_review(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    review_id = int(callback.data.split('_')[-1])
    review = await sqlite_get_review_with_user_book_by_review_id(session, review_id)
    if not review:
        await callback.message.answer(LEXICON['review_not_found'])
        return
    review_uploader = review.user
    rating = review.rating
    rating = f"{round(rating, 2)} {LEXICON[f'rating_{round(rating)}']}"
    await callback.message.answer(
        f"Пользователь: {review_uploader.first_name} {review_uploader.last_name}\n"
        f"Книга: {review.book.author} — {review.book.title}\n"
        f"Оценка: {rating}\n"
        f"Мнение о книге: {review.text}",
        reply_markup=
        InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=LEXICON['redact_review'], callback_data=f'create_review_{review.book_id}')
        ], [InlineKeyboardButton(text=LEXICON['delete_review'], callback_data=f'delete_review_{review_id}')]]))


@router.callback_query(F.data.startswith('delete_review'))
async def process_delete_review(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    review_id = int(callback.data.split('_')[-1])
    review = await session.scalar(select(Review).where(Review.review_id == review_id))
    if not review:
        await callback.message.answer(LEXICON['review_not_found'])
        return
    if review.user_id != callback.from_user.id:
        await callback.message.answer(LEXICON['no_access_to_delete_review'])
        return
    await session.delete(review)
    await session.commit()
    await callback.message.answer(LEXICON['review_delete_success'])


@router.callback_query(F.data.startswith('create_review'))
async def process_add_review(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    book_id = int(callback.data.split('_')[-1])
    book = await session.scalar(select(Book).where(Book.book_id == book_id))
    if not book:
        await callback.message.answer(LEXICON['book_not_found'])
        return
    await state.update_data(add_review={'book_id': book_id})
    await callback.message.answer(
        'Вы вошли в режим создания/редактирования отзыва. Для выхода из него наберите команду\n/cancel_create_review')
    await callback.message.answer(LEXICON['fill_review_rating'])
    await state.set_state(FSMCreateReview.rating)


@router.message(StateFilter(*FSMCreateReview.__all_states__), Command('cancel_create_review'))
async def process_cancel_add_review(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        if 'add_review' in data:
            del data['add_review']
            await state.update_data(data)
        await message.answer(LEXICON['canceled_create_review'])
        await state.set_state(default_state)
    except Exception as e:
        logger.exception(f"Error canceling review creation: {e}")
        await message.answer("❌ Произошла ошибка при отмене создания отзыва")


@router.message(StateFilter(FSMCreateReview.rating))
async def process_add_review_rating(message: Message, state: FSMContext):
    try:
        rating = message.text.replace(',', '.').strip()

        if not rating:
            await message.answer(LEXICON['ask_for_review_rating'])
            return

        try:
            rating = float(rating)
            if not 1 <= rating <= 5:
                raise ValueError
        except ValueError:
            await message.answer(LEXICON['wrong_rating'])
            return

        data = await state.get_data()
        add_review_dict = data.get('add_review', {})
        add_review_dict['fill_rating'] = rating
        await state.update_data(add_review=add_review_dict)

        await message.answer(text=LEXICON['fill_review_text'])
        await state.set_state(FSMCreateReview.text)

    except Exception as e:
        logger.exception(f"Error processing review rating: {e}")
        await message.answer("❌ Произошла ошибка при обработке оценки")


@router.message(StateFilter(FSMCreateReview.text))
async def process_add_review_text(message: Message, state: FSMContext, session: AsyncSession):
    try:
        text = message.text.strip()
        if not text:
            await message.answer(LEXICON['empty_review_warning'])
            return

        data = await state.get_data()
        add_review_dict = data.get('add_review', {})

        if 'book_id' not in add_review_dict or 'fill_rating' not in add_review_dict:
            await message.answer(LEXICON['review_data_damaged'])
            await state.set_state(default_state)
            return

        # Дополнительная проверка на существующий отзыв
        existing_reviews = await session.execute(
            select(Review).where(
                Review.user_id == message.from_user.id,
                Review.book_id == add_review_dict['book_id']
            )
        )
        existing_reviews = existing_reviews.scalars().all()

        if existing_reviews:
            for review in existing_reviews:
                await session.delete(review)
            await session.commit()
        # Создаем новый отзыв
        review = Review(
            user_id=message.from_user.id,
            book_id=add_review_dict['book_id'],
            rating=add_review_dict['fill_rating'],
            text=text
        )

        session.add(review)
        await session.commit()

        # Формируем клавиатуру для возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text='Перейти к обложке',
                callback_data=f"view_book_{add_review_dict['book_id']}"
            )
        ]])

        await message.answer(
            text=LEXICON['create_review_success'],
            reply_markup=keyboard
        )

        # Очищаем состояние
        if 'add_review' in data:
            del data['add_review']
            await state.update_data(data)
        await state.set_state(default_state)

    except Exception as e:
        await session.rollback()
        logger.exception(f"Error saving review: {e}")
        await message.answer("❌ Произошла ошибка при сохранении отзыва")
