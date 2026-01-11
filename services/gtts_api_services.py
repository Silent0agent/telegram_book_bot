import logging
from pathlib import Path
import asyncio

from gtts import gTTS, gTTSError  # Явно импортируем gTTSError
import aiofiles
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Book, Audiobook
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def async_tts_save(text: str, lang: str, path: Path):
    """Асинхронное сохранение TTS в файл через ThreadPool"""
    loop = asyncio.get_running_loop()
    try:
        tts = gTTS(text=text, lang=lang)
        await loop.run_in_executor(
            None,  # Используем стандартный ThreadPool
            lambda: tts.save(str(path))
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
        session: AsyncSession,
        book: Book,
        user_id: int,
        chat_id: int,
        book_text: str,
        chunk_size: int = 500,
        delay: float = 1.0,
        max_retries: int = 3
):
    """Полностью асинхронная генерация аудиокниги с обработкой ограничений API"""
    audiobook = None
    base_dir = Path("media/audiobooks")
    output_path = None
    main_file = None

    try:
        if len(book_text) >= 100_000:
            await bot.send_message(
                chat_id,
                'ℹ️ Текст вашей книги слишком большой для генерации аудио. Вы можете добавить свою аудио-версию книги'
                ' через её меню.'
            )
            return None
        else:
            await bot.send_message(chat_id,
                                   f'ℹ️ Началась генерация аудиокниги {book.title}, она будет идти в фоновом процессе,'
                                   f'поэтому вы можете взаимодействовать с ботом.')
        # Создаем запись аудиокниги в БД
        audiobook = Audiobook(
            book_id=book.book_id,
            title=f"Аудиоверсия книги {book.title} (генерированная)",
            uploader_id=user_id
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

        chunks = [book_text[i:i + chunk_size] for i in range(0, len(book_text), chunk_size)]

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
                        wait_time = delay * (2 ** retry_count)
                        logger.warning(f"Retry {retry_count}/{max_retries}, waiting {wait_time}s...")
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
                logger.error(f"Failed to process chunk {i} after {max_retries} retries")
                # Закрываем основной файл перед удалением
                if main_file:
                    await main_file.close()
                # Удаляем все временные файлы
                for file in temp_files:
                    try:
                        file.unlink(missing_ok=True)
                    except Exception as e:
                        logger.exception(f"Error deleting temp file {file}: {e}")
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
                    "⚠️ Сервис синтеза речи перегружен и не отвечает. "
                    "Попробуйте позже или загрузите аудиофайл вручную."
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
        if not await session.scalar(select(Book).where(Book.book_id == book.book_id)):
            output_path.unlink(missing_ok=True)
            return None

        # Уведомление пользователю
        await bot.send_message(
            chat_id,
            f"🎧 Аудиокнига '{book.title}' готова!"
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
        for file in base_dir.glob(f"temp_{audiobook.audiobook_id}_*.mp3" if audiobook else "temp_*.mp3"):
            try:
                file.unlink()
            except Exception as e:
                logger.exception(f"Error deleting temp file {file}: {e}")
        # Откатываем БД
        await session.rollback()
        # Уведомляем пользователя
        try:
            await bot.send_message(
                chat_id,
                "⚠️ Не удалось сгенерировать аудиокнигу. Сервис синтеза речи перегружен. "
                "Вы можете ввести аудиофайл вручную."
            )
        except Exception as e:
            logger.exception("Failed to send error notification to user")

        return None
