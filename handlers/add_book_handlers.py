__all__ = ()

import asyncio
import logging
from math import ceil

from aiogram import Bot, F, Router
from aiogram.enums import ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Book, Genre
from keyboards.genres_kb import create_genres_keyboard
from lexicon import LEXICON
from services.file_handling import (
    cleanup_book_files,
    get_book_text,
    prepare_book,
    save_book_files,
)
from services.gtts_api_services import generate_and_save_audiobook
from states.states import FSMAddBook

router = Router()
logger = logging.getLogger(__name__)

# Общие константы для валидации
MAX_TITLE_LENGTH = 200
MAX_AUTHOR_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 1000


@router.callback_query(F.data == "add_book")
async def process_fill_book(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(LEXICON["entered_add_book_mode"])
    await callback.message.answer(LEXICON["fill_title"])
    await state.set_state(FSMAddBook.fill_title)


@router.message(
    StateFilter(*FSMAddBook.__all_states__),
    Command("cancel_add_book"),
)
async def process_cancel_add_book(message: Message, state: FSMContext):
    await message.answer(LEXICON["canceled_add_book"])
    data = await state.update_data()
    if data.get("add_book"):
        del data["add_book"]

    if data.get("active_add_book_message_id"):
        del data["active_add_book_message_id"]

    await state.update_data(data)
    await state.set_state(default_state)


@router.message(
    StateFilter(FSMAddBook.fill_title),
    F.content_type == ContentType.TEXT,
)
async def process_fill_book_title(message: Message, state: FSMContext):
    title = message.text.strip()

    # Валидация названия
    if not title:
        await message.answer(LEXICON["empty_title_warning"])
        return

    if len(title) > MAX_TITLE_LENGTH:
        await message.answer(
            LEXICON["title_too_long_error"].format(
                max_length=MAX_AUTHOR_LENGTH,
            ),
        )
        return

    await state.update_data(add_book={"title": title})
    await message.answer(LEXICON["fill_author"])
    await state.set_state(FSMAddBook.fill_author)


@router.message(
    StateFilter(FSMAddBook.fill_author),
    F.content_type == ContentType.TEXT,
)
async def process_fill_book_author(message: Message, state: FSMContext):
    author = message.text.strip()

    # Валидация автора
    if not author:
        await message.answer(LEXICON["empty_author_warning"])
        return

    if len(author) > MAX_AUTHOR_LENGTH:
        await message.answer(
            LEXICON["author_too_long_error"].format(
                max_length=MAX_AUTHOR_LENGTH,
            ),
        )
        return

    data = await state.get_data()
    add_book_dict = data.get("add_book", {})
    add_book_dict["author"] = author
    await state.update_data(add_book=add_book_dict)
    await message.answer(LEXICON["fill_description"])
    await state.set_state(FSMAddBook.fill_description)


@router.message(
    StateFilter(FSMAddBook.fill_description),
    F.content_type == ContentType.TEXT,
)
async def process_fill_book_description(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    description = message.text.strip()

    # Валидация описания
    if not description:
        await message.answer(LEXICON["empty_description_warning"])
        return

    if len(description) > MAX_DESCRIPTION_LENGTH:
        await message.answer(
            LEXICON["description_too_long_error"].format(
                max_length=MAX_DESCRIPTION_LENGTH,
            ),
        )
        return

    data = await state.get_data()
    add_book_dict = data.get("add_book", {})
    add_book_dict["description"] = description

    all_genres = await session.execute(select(Genre))
    all_genres = all_genres.scalars().all()

    if not all_genres:
        await message.answer(LEXICON["no_genres_in_database"])
        await state.set_state(default_state)
        return

    add_book_dict["genres_list_page"] = 1
    add_book_dict["genres_list_length"] = ceil(len(all_genres) / 16)

    new_message = await message.answer(
        LEXICON["fill_genres"],
        reply_markup=create_genres_keyboard(
            [],
            add_book_dict["genres_list_page"],
            add_book_dict["genres_list_length"],
            *all_genres[:16],
        ),
    )

    await state.update_data(
        add_book=add_book_dict,
        active_add_book_message_id=new_message.message_id,
    )
    await state.set_state(FSMAddBook.fill_genres)


# Обработка некорректного ввода для текстовых полей
@router.message(
    StateFilter(
        FSMAddBook.fill_title,
        FSMAddBook.fill_author,
        FSMAddBook.fill_description,
    ),
    ~(F.content_type == ContentType.TEXT),
)
async def process_wrong_content_type(message: Message):
    await message.answer(LEXICON["ask_for_text_message"])


@router.callback_query(
    StateFilter(FSMAddBook.fill_genres),
    F.data.startswith("remove_genre"),
)
async def process_remove_genre(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
):
    await callback.answer()
    data = await state.get_data()

    active_add_book_message_id = data.get("active_add_book_message_id")
    if callback.message.message_id != active_add_book_message_id:
        await callback.answer(LEXICON["old_message_alert"], show_alert=True)
        return

    add_book_dict = data.get("add_book")
    if not add_book_dict:
        await callback.message.answer(LEXICON["add_book_error"])
        return

    genres_list_page = add_book_dict["genres_list_page"]
    chosen_genres_ids = add_book_dict.get("chosen_genres_ids", [])
    if int(callback.data.split("_")[-1]) in chosen_genres_ids:
        chosen_genres_ids.remove(int(callback.data.split("_")[-1]))

    all_genres = await session.execute(select(Genre))
    all_genres = all_genres.scalars().all()

    genres_start_slice = (genres_list_page - 1) * 16
    genres_stop_slice = (genres_list_page - 1) * 16 + 16

    await callback.message.edit_text(
        LEXICON["fill_genres"],
        reply_markup=create_genres_keyboard(
            add_book_dict.get("chosen_genres_ids", []),
            add_book_dict["genres_list_page"],
            add_book_dict["genres_list_length"],
            *all_genres[genres_start_slice:genres_stop_slice],
        ),
    )
    await state.update_data(add_book=add_book_dict)


@router.callback_query(
    StateFilter(FSMAddBook.fill_genres),
    F.data.in_(["genres_list_forward", "genres_list_backward"]),
)
async def process_choose_genre(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
):
    await callback.answer()
    data = await state.get_data()

    active_add_book_message_id = data.get("active_add_book_message_id")
    if callback.message.message_id != active_add_book_message_id:
        await callback.answer(LEXICON["old_message_alert"], show_alert=True)
        return

    add_book_dict = data.get("add_book")
    if not add_book_dict:
        await callback.message.answer(LEXICON["add_book_error"])
        return

    if callback.data == "genres_list_forward":
        add_book_dict["genres_list_page"] += 1
    elif callback.data == "genres_list_backward":
        add_book_dict["genres_list_page"] -= 1

    genres_list_page = add_book_dict["genres_list_page"]
    all_genres = await session.execute(select(Genre))
    all_genres = all_genres.scalars().all()
    if not all_genres:
        await callback.message.answer(LEXICON["no_genres_in_database"])
        await state.set_state(default_state)
        return

    genres_start_slice = (genres_list_page - 1) * 16
    genres_stop_slice = (genres_list_page - 1) * 16 + 16

    await callback.message.edit_text(
        LEXICON["fill_genres"],
        reply_markup=create_genres_keyboard(
            add_book_dict.get("chosen_genres_ids", []),
            add_book_dict["genres_list_page"],
            add_book_dict["genres_list_length"],
            *all_genres[genres_start_slice:genres_stop_slice],
        ),
    )
    await state.update_data(add_book=add_book_dict)


@router.callback_query(
    StateFilter(FSMAddBook.fill_genres),
    F.data.startswith("choose_genre_"),
)
async def process_select_genre(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
):
    """Обрабатывает выбор жанра из списка."""
    await callback.answer()
    data = await state.get_data()

    active_add_book_message_id = data.get("active_add_book_message_id")
    if callback.message.message_id != active_add_book_message_id:
        await callback.answer(LEXICON["old_message_alert"], show_alert=True)
        return

    add_book_dict = data.get("add_book")
    if not add_book_dict:
        await callback.message.answer(LEXICON["add_book_error"])
        return

    # Получаем ID выбранного жанра
    try:
        genre_id = int(callback.data.split("_")[-1])
    except (IndexError, ValueError):
        await callback.answer(LEXICON["unknown_error"], show_alert=True)
        return

    # Инициализируем список выбранных жанров, если его нет
    if "chosen_genres_ids" not in add_book_dict:
        add_book_dict["chosen_genres_ids"] = []

    # Добавляем жанр в список выбранных
    chosen_genres = add_book_dict["chosen_genres_ids"]
    if genre_id not in chosen_genres:
        chosen_genres.append(genre_id)

    add_book_dict["chosen_genres_ids"] = chosen_genres

    # Получаем все жанры для отображения
    all_genres = await session.execute(select(Genre))
    all_genres = all_genres.scalars().all()

    genres_list_page = add_book_dict.get("genres_list_page", 1)
    genres_start_slice = (genres_list_page - 1) * 16
    genres_stop_slice = genres_start_slice + 16

    await callback.message.edit_text(
        LEXICON["fill_genres"],
        reply_markup=create_genres_keyboard(
            add_book_dict["chosen_genres_ids"],
            genres_list_page,
            add_book_dict["genres_list_length"],
            *all_genres[genres_start_slice:genres_stop_slice],
        ),
    )

    await state.update_data(add_book=add_book_dict)


@router.callback_query(
    StateFilter(FSMAddBook.fill_genres),
    F.data == "confirm_genres",
)
async def process_confirm_genres(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Подтверждение выбранных жанров и переход к выбору публичности."""
    await callback.answer()
    data = await state.get_data()
    add_book_dict = data.get("add_book")

    if not add_book_dict:
        await callback.message.answer(LEXICON["add_book_error"])
        return

    # Создаем клавиатуру для выбора публичности
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LEXICON["fill_is_public_true"],
                    callback_data="fill_is_public_true",
                ),
                InlineKeyboardButton(
                    text=LEXICON["fill_is_public_false"],
                    callback_data="fill_is_public_false",
                ),
            ],
        ],
    )

    new_message = await callback.message.answer(
        LEXICON["fill_is_public"],
        reply_markup=keyboard,
    )

    await state.update_data(active_add_book_message_id=new_message.message_id)

    await state.set_state(FSMAddBook.fill_is_public)


@router.callback_query(
    StateFilter(FSMAddBook.fill_is_public),
    F.data.in_(["fill_is_public_true", "fill_is_public_false"]),
)
async def process_fill_is_public(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Обрабатывает выбор публичности книги."""
    await callback.answer()
    data = await state.get_data()
    add_book_dict = data.get("add_book")
    if not add_book_dict:
        await callback.message.answer(LEXICON["add_book_error"])
        return

    add_book_dict["is_public"] = callback.data == "fill_is_public_true"

    await state.update_data(add_book=add_book_dict)
    await callback.message.answer(LEXICON["upload_cover"])
    await state.set_state(FSMAddBook.upload_cover)


@router.message(StateFilter(FSMAddBook.upload_cover))
async def process_fill_book_cover(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer(LEXICON["upload_cover_error"])
        return

    data = await state.get_data()
    add_book_dict = data.get("add_book")
    if not add_book_dict:
        await message.answer(LEXICON["add_book_error"])
        return

    add_book_dict["cover"] = message.photo[-1]
    await message.answer(LEXICON["upload_text_file"])
    await state.update_data(add_book=add_book_dict)
    await state.set_state(FSMAddBook.upload_text_file)


@router.message(StateFilter(FSMAddBook.upload_text_file))
async def process_upload_text_file(
    message: Message,
    bot: Bot,
    state: FSMContext,
    session: AsyncSession,
):
    # Проверка документа
    if not message.document or not message.document.file_name.endswith(".txt"):
        await message.answer(LEXICON["upload_text_file_error"])
        return

    data = await state.get_data()
    add_book_dict = data.get("add_book")
    if not add_book_dict:
        await message.answer(LEXICON["add_book_error"])
        return

    try:
        # 1. Сохранение данных книги в БД
        book = Book(
            title=add_book_dict["title"],
            author=add_book_dict["author"],
            description=add_book_dict["description"],
            is_public=add_book_dict["is_public"],
            uploader_id=message.from_user.id,
        )

        # Добавление жанров
        for genre_id in sorted(add_book_dict.get("chosen_genres_ids", [])):
            genre = await session.get(Genre, genre_id)
            if genre:
                book.genres.append(genre)

        session.add(book)
        await session.commit()

        # 2. Сохранение файлов через отдельный модуль
        await save_book_files(
            bot=bot,
            book=book,
            text_file_id=message.document.file_id,
            cover_file_id=add_book_dict["cover"].file_id,
        )

        # 3. Финализация
        await prepare_book(book.book_id)

        # 4 Аудио
        asyncio.create_task(
            generate_and_save_audiobook(
                bot=bot,
                book=book,
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                book_text=await get_book_text(book.book_id),
                session=session,
            ),
        )

        # Очистка состояния
        new_data = {
            k: v
            for k, v in data.items()
            if k not in ["add_book", "active_add_book_message_id"]
        }
        await state.set_data(new_data)
        await state.set_state(default_state)

        await message.answer(
            LEXICON["add_book_success"],
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=LEXICON["search_user_books"],
                            callback_data="search_user_books",
                        ),
                    ],
                ],
            ),
        )

    except Exception as e:
        await session.rollback()
        error_msg = f"Error adding book: {type(e).__name__} - {str(e)}"
        logger.exception(error_msg)

        # Удаление частично созданных файлов
        if "book" in locals():
            await cleanup_book_files(book.book_id)

        await message.answer(LEXICON["add_book_error"])
