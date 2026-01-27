__all__ = ()

import asyncio
import logging
from pathlib import Path

import aiofiles
from aiogram import Bot
from gtts import gTTS, gTTSError
from sqlalchemy import select

from database.db_session import create_session
from database.models import Audiobook, Book
from lexicon import LEXICON

logger = logging.getLogger(__name__)


async def async_tts_save(text: str, lang: str, path: Path):
    """Асинхронное сохранение TTS в файл через ThreadPool"""
    loop = asyncio.get_running_loop()
    try:
        tts = gTTS(text=text, lang=lang)
        await loop.run_in_executor(
            None,
            lambda: tts.save(str(path)),
        )
        return True
    except gTTSError as e:
        if "429" in str(e):
            logger.warning(f"TTS API rate limit exceeded: {e}")
        else:
            logger.exception(f"TTS API error: {e}")

        return False
    except Exception as e:
        logger.exception(f"Unexpected TTS error: {e}")
        return False


async def generate_and_save_audiobook(
    bot: Bot,
    book_id: int,
    user_id: int,
    chat_id: int,
    book_text: str,
    chunk_size: int = 500,
    delay: float = 1.0,
    max_retries: int = 3,
):
    """Асинхронная генерация аудиокниги с обработкой ограничений API"""
    session = None
    audiobook = None
    base_dir = Path("media/audiobooks")
    output_path = None
    main_file = None

    try:
        # Создаем новую сессию для этой задачи
        session = await create_session()

        # Получаем книгу по ID
        book = await session.get(Book, book_id)
        if not book:
            logger.error(f"Book with id {book_id} not found")
            return None

        if len(book_text) >= 100_000:
            await bot.send_message(
                chat_id,
                LEXICON["gtts_text_too_long"],
            )
            return None

        await bot.send_message(
            chat_id,
            LEXICON["gtts_start_generating"].format(book_title=book.title),
        )

        # Создаем запись аудиокниги в БД
        audiobook = Audiobook(
            book_id=book.book_id,
            title=LEXICON["generated_audiobook_title"].format(
                book_title=book.title,
            ),
            uploader_id=user_id,
        )
        session.add(audiobook)
        await session.flush()
        await session.refresh(audiobook)

        # Подготовка путей
        base_dir.mkdir(parents=True, exist_ok=True)
        output_path = base_dir / f"{audiobook.audiobook_id}.mp3"
        temp_files = []

        # Явно открываем файл в режиме записи
        main_file = await aiofiles.open(output_path, "wb")

        chunks = [
            book_text[slice(i, i + chunk_size)]
            for i in range(0, len(book_text), chunk_size)
        ]

        for i, chunk in enumerate(chunks):
            temp_path = base_dir / f"temp_{audiobook.audiobook_id}_{i}.mp3"
            temp_files.append(temp_path)
            retry_count = 0
            success = False

            while retry_count < max_retries and not success:
                try:
                    success = await async_tts_save(chunk, "ru", temp_path)

                    if not success:
                        retry_count += 1
                        wait_time = delay * (2**retry_count)
                        logger.warning(
                            f"Retry {retry_count}/{max_retries}, "
                            f"waiting {wait_time}s...",
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    async with aiofiles.open(temp_path, "rb") as temp_file:
                        await main_file.write(await temp_file.read())

                except Exception as e:
                    logger.exception(f"Error processing chunk {i}: {e}")
                    retry_count += 1
                    await asyncio.sleep(delay * 2)
                    continue

            if not success:
                logger.error(
                    f"Failed to process chunk {i} after {max_retries} retries",
                )
                # Закрываем основной файл перед удалением
                if main_file:
                    await main_file.close()
                # Удаляем все временные файлы
                for file in temp_files:
                    try:
                        file.unlink(missing_ok=True)
                    except Exception as e:
                        logger.exception(
                            f"Error deleting temp file {file}: {e}",
                        )
                # Удаляем выходной файл, если он был частично создан
                if output_path.exists():
                    try:
                        output_path.unlink()
                    except Exception as e:
                        logger.exception(f"Error deleting output file: {e}")
                # Откатываем БД
                await session.rollback()
                # Уведомляем пользователя
                await bot.send_message(
                    chat_id,
                    LEXICON["gtts_api_failure"],
                )
                return None

            try:
                temp_path.unlink(missing_ok=True)
            except Exception as e:
                logger.exception(f"Error deleting temp file: {e}")

            await asyncio.sleep(delay)

        # Закрываем основной файл перед сохранением в БД
        if main_file:
            await main_file.close()

        # Сохранение пути к файлу
        audiobook.audio_url = str(output_path)
        session.add(audiobook)
        await session.commit()

        # Проверка, что книга еще существует
        if not await session.scalar(
            select(Book).where(Book.book_id == book_id),
        ):
            output_path.unlink(missing_ok=True)
            return None

        # Уведомление пользователю
        await bot.send_message(
            chat_id,
            LEXICON["audiobook_generated"].format(book_title=book.title),
        )
        return output_path

    except Exception as e:
        logger.exception(f"Audiobook generation failed: {e}")
        # Закрываем основной файл, если он был открыт
        if main_file:
            await main_file.close()
        # Удаляем созданные файлы
        if output_path and output_path.exists():
            try:
                output_path.unlink()
            except Exception as e:
                logger.exception(f"Error deleting output file: {e}")
        # Удаляем временные файлы
        for file in base_dir.glob(
            (
                f"temp_{audiobook.audiobook_id}_*.mp3"
                if audiobook
                else "temp_*.mp3"
            ),
        ):
            try:
                file.unlink()
            except Exception as e:
                logger.exception(f"Error deleting temp file {file}: {e}")
        # Откатываем БД, если сессия активна
        if session:
            await session.rollback()
        # Уведомляем пользователя
        try:
            await bot.send_message(
                chat_id,
                LEXICON["gtts_api_failure"],
            )
        except Exception:
            logger.exception("Failed to send error notification to user")

        return None
    finally:
        # Всегда закрываем сессию
        if session:
            await session.close()
