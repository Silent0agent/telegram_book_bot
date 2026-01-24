__all__ = ()

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.enums import ContentType
from aiogram.filters import Command, or_f, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import (
    Audio,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Audiobook, Book
from keyboards.audiobooks_kb import create_audiobooks_keyboard
from lexicon import LEXICON
from services.database_services import (
    sqlite_get_audiobook_with_book_user_by_audiobook_id,
    sqlite_get_audiobooks_with_book_user_by_book_id,
    sqlite_get_audiobooks_with_book_user_by_uploader_id,
)
from services.file_handling import delete_audiobook_file, save_audiobook
from states.states import FSMAddAudiobook

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("listen_audiobook_"))
async def send_audiobook(callback: CallbackQuery, session: AsyncSession):
    try:
        audiobook_id = int(callback.data.split("_")[-1])

        # Получаем данные аудиокниги
        audiobook = await sqlite_get_audiobook_with_book_user_by_audiobook_id(
            session,
            audiobook_id,
        )

        if not audiobook:
            await callback.answer(
                LEXICON["audiobook_not_found"],
                show_alert=True,
            )
            return

        # Проверяем существование файла
        audio_path = Path(audiobook.audio_url)
        if not await asyncio.to_thread(audio_path.exists):
            await callback.answer(LEXICON["file_unavailable"], show_alert=True)
            return

        await callback.message.answer(LEXICON["wait_for_listen_audio"])

        # Отправляем аудиофайл
        await callback.message.answer_audio(
            audio=FSInputFile(audio_path),
            title=f"{audiobook.book.title} | {audiobook.title}",
            performer=audiobook.book.author,
        )
        await callback.answer()

    except Exception as e:
        logger.exception(f"Error sending audiobook: {e}")
        await callback.answer(LEXICON["add_audiobook_error"], show_alert=True)


@router.callback_query(
    or_f(F.data.startswith("view_audiobooks"), F.data == "user_audiobooks"),
)
async def process_book_audiobooks(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
):
    await callback.answer()
    if callback.data == "user_audiobooks":
        audiobooks = await sqlite_get_audiobooks_with_book_user_by_uploader_id(
            session,
            callback.from_user.id,
        )
        if not audiobooks:
            await callback.message.answer(LEXICON["no_user_audiobooks"])
            return
    elif callback.data.startswith("view_audiobooks"):
        book_id = int(callback.data.split("_")[-1])
        book = await session.scalar(
            select(Book).where(Book.book_id == book_id),
        )
        if not book:
            await callback.message.answer(LEXICON["book_not_found"])
            return

        audiobooks = await sqlite_get_audiobooks_with_book_user_by_book_id(
            session,
            book_id,
        )
        if not audiobooks:
            await callback.message.answer(LEXICON["no_book_audiobooks"])
            return

    audiobooks_results_dict = {
        "audiobooks": audiobooks,
        "current_page": 1,
    }
    audiobook = audiobooks[0]
    uploader = audiobook.uploader
    uploaded_by_label = LEXICON["book_uploaded_by_label"]
    title_with_author_label = LEXICON["book_title_with_author_label"]
    audiobook_title_label = LEXICON["audiobook_label"]
    new_message = await callback.message.answer(
        f"{uploaded_by_label}: "
        f"{uploader.first_name if uploader.first_name else ''} "
        f"{uploader.last_name if uploader.last_name else ''}\n"
        f"{title_with_author_label}: "
        f"{audiobook.book.author} — {audiobook.book.title}\n"
        f"{audiobook_title_label}: {audiobook.title}\n",
        reply_markup=create_audiobooks_keyboard(
            1,
            len(audiobooks),
            audiobook,
            is_user_audiobook=uploader.user_id == callback.from_user.id,
        ),
    )
    await state.update_data(
        audiobooks_results=audiobooks_results_dict,
        active_audiobook_results_message_id=new_message.message_id,
    )


@router.callback_query(
    F.data.in_(["audiobooks_list_backward", "audiobooks_list_forward"]),
)
async def process_move_audiobooks_list(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()
    data = await state.get_data()
    active_audiobook_results_message_id = data.get(
        "active_audiobook_results_message_id",
    )

    if callback.message.message_id != active_audiobook_results_message_id:
        await callback.answer(LEXICON["old_message_alert"], show_alert=True)
        return

    audiobooks_results_dict = data["audiobooks_results"]
    if callback.data == "audiobooks_list_backward":
        audiobooks_results_dict["current_page"] -= 1
    elif callback.data == "audiobooks_list_forward":
        audiobooks_results_dict["current_page"] += 1

    current_page = audiobooks_results_dict["current_page"]
    audiobook = audiobooks_results_dict["audiobooks"][current_page - 1]
    if not audiobook:
        await callback.message.answer(LEXICON["audiobook_not_found"])
        return

    uploader = audiobook.uploader
    is_user_audiobook = uploader.user_id == callback.from_user.id

    uploaded_by_label = LEXICON["book_uploaded_by_label"]
    title_with_author_label = LEXICON["book_title_with_author_label"]
    audiobook_title_label = LEXICON["audiobook_label"]
    new_message = await callback.message.edit_text(
        f"{uploaded_by_label}: "
        f"{uploader.first_name if uploader.first_name else ''} "
        f"{uploader.last_name if uploader.last_name else ''}\n"
        f"{title_with_author_label}: "
        f"{audiobook.book.author} — {audiobook.book.title}\n"
        f"{audiobook_title_label}: {audiobook.title}\n",
        reply_markup=create_audiobooks_keyboard(
            current_page,
            len(audiobooks_results_dict["audiobooks"]),
            audiobook,
            is_user_audiobook=is_user_audiobook,
        ),
    )
    await state.update_data(
        audiobooks_results=audiobooks_results_dict,
        active_audiobook_results_message_id=new_message.message_id,
    )


@router.callback_query(F.data.startswith("view_user_audiobook"))
async def process_view_audiobook(
    callback: CallbackQuery,
    session: AsyncSession,
):
    await callback.answer()
    audiobook_id = int(callback.data.split("_")[-1])
    audiobook = await sqlite_get_audiobook_with_book_user_by_audiobook_id(
        session,
        audiobook_id,
    )
    if not audiobook:
        await callback.message.answer(LEXICON["audiobook_not_found"])
        return

    uploader = audiobook.uploader

    uploaded_by_label = LEXICON["book_uploaded_by_label"]
    title_with_author_label = LEXICON["book_title_with_author_label"]
    audiobook_title_label = LEXICON["audiobook_label"]
    await callback.message.answer(
        f"{uploaded_by_label}: "
        f"{uploader.first_name if uploader.first_name else ''} "
        f"{uploader.last_name if uploader.last_name else ''}\n"
        f"{title_with_author_label}: "
        f"{audiobook.book.author}: — {audiobook.book.title}\n"
        f"{audiobook_title_label}: {audiobook.title}\n",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=LEXICON["listen_audiobook"],
                        callback_data=f"listen_audiobook_{audiobook_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=LEXICON["delete_audiobook"],
                        callback_data=f"delete_audiobook_{audiobook_id}",
                    ),
                ],
            ],
        ),
    )


@router.callback_query(F.data.startswith("delete_audiobook"))
async def process_delete_audiobook(
    callback: CallbackQuery,
    session: AsyncSession,
):
    await callback.answer()
    audiobook_id = int(callback.data.split("_")[-1])
    audiobook = await session.scalar(
        select(Audiobook).where(
            Audiobook.audiobook_id == audiobook_id,
            Audiobook.audio_url.is_not(None),
        ),
    )
    if not audiobook:
        await callback.message.answer(LEXICON["audiobook_not_found"])
        return

    if audiobook.uploader_id != callback.from_user.id:
        await callback.message.answer(LEXICON["no_access_to_delete_audiobook"])
        return

    await session.delete(audiobook)
    await session.commit()
    delete_audiobook_file(audiobook_id)
    await callback.message.answer(LEXICON["audiobook_delete_success"])


@router.callback_query(F.data.startswith("add_audiobook"))
async def process_add_audiobook(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
):
    await callback.answer()
    book_id = int(callback.data.split("_")[-1])
    book = await session.scalar(select(Book).where(Book.book_id == book_id))
    if not book:
        await callback.message.answer(LEXICON["book_not_found"])
        return

    await state.update_data(add_audiobook={"book_id": book_id})
    await callback.message.answer(LEXICON["entered_add_audiobook_mode"])
    await callback.message.answer(LEXICON["fill_audiobook_title"])
    await state.set_state(FSMAddAudiobook.fill_title)


@router.message(
    StateFilter(*FSMAddAudiobook.__all_states__),
    Command("cancel_add_audiobook"),
)
async def process_cancel_add_audiobook(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        if "add_audiobook" in data:
            del data["add_audiobook"]
            await state.update_data(data)

        await message.answer(LEXICON["canceled_add_audiobook"])
        await state.set_state(default_state)
    except Exception as e:
        logger.exception(f"Error canceling audiobook creation: {e}")
        await message.answer(LEXICON["cancel_add_audiobook_error"])


@router.message(StateFilter(FSMAddAudiobook.fill_title))
async def process_add_audiobook_title(message: Message, state: FSMContext):
    try:
        if message.content_type != ContentType.TEXT:
            await message.answer(LEXICON["ask_for_text_message"])
            return

        title = message.text

        if not title:
            await message.answer(LEXICON["empty_title_warning"])
            return

        data = await state.get_data()
        add_audiobook_dict = data.get("add_audiobook", {})
        add_audiobook_dict["fill_title"] = title
        await state.update_data(add_review=add_audiobook_dict)

        await message.answer(text=LEXICON["upload_audio"])
        await state.set_state(FSMAddAudiobook.upload_audio)

    except Exception as e:
        logger.exception(f"Error processing review rating: {e}")
        await message.answer(LEXICON["add_audiobook_title_error"])


@router.message(StateFilter(FSMAddAudiobook.upload_audio))
async def process_add_audiobook_audio(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
):
    try:
        # Проверка наличия аудио
        if not message.audio:
            await message.answer(LEXICON["ask_for_audio_message"])
            return

        audio: Audio = message.audio
        data = await state.get_data()
        add_audiobook_dict = data.get("add_audiobook", {})

        # Валидация данных
        if (
            "book_id" not in add_audiobook_dict
            or "fill_title" not in add_audiobook_dict
        ):
            await message.answer(LEXICON["audiobook_data_damaged"])
            await state.set_state(default_state)
            return

        # Создаем объект аудиокниги (пока без сохранения в БД)
        new_audiobook = Audiobook(
            book_id=add_audiobook_dict["book_id"],
            title=add_audiobook_dict["fill_title"],
            uploader_id=message.from_user.id,
        )

        # Добавляем в сессию (чтобы получить ID)
        session.add(new_audiobook)
        await session.flush()  # Получаем ID до commit
        await session.refresh(new_audiobook)

        # Сохраняем файл
        try:
            file_path = await save_audiobook(
                bot,
                audio,
                new_audiobook.audiobook_id,
            )
            new_audiobook.audio_url = str(file_path)
        except Exception as e:
            await session.rollback()
            raise e
        # Фиксируем изменения в БД
        await session.commit()

        newaudiobook_id = new_audiobook.audiobook_id

        # Успешное завершение
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=LEXICON["go_to_audiobook"],
                        callback_data=f"view_user_audiobook_{newaudiobook_id}",
                    ),
                ],
            ],
        )

        await message.answer(
            LEXICON["add_audiobook_success"],
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.exception(f"Error saving audiobook: {e}")
        await message.answer(
            LEXICON["add_audiobook_error"],
        )
    finally:
        # Всегда очищаем состояние
        if "add_audiobook" in data:
            del data["add_audiobook"]
            await state.update_data(data)

        await state.set_state(default_state)
