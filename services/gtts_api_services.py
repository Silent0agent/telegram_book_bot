import logging
from pathlib import Path
import asyncio

from gtts import gTTS
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
    except Exception as e:
        logger.exception(f"TTS error: {e}")
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
    try:
        if len(book_text) > 100_000:
            await bot.send_message(
                chat_id,
                "📚 Книга слишком большая для автоматической генерации. "
                "Вы можете добавить аудиоверсию вручную через меню книги."
            )
            return

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
        base_dir = Path("media/audiobooks")
        base_dir.mkdir(parents=True, exist_ok=True)
        output_path = base_dir / f"{audiobook.audiobook_id}.mp3"

        # Генерация аудио по частям
        async with aiofiles.open(output_path, "wb") as main_file:
            chunks = [book_text[i:i + chunk_size] for i in range(0, len(book_text), chunk_size)]

            for i, chunk in enumerate(chunks):
                temp_path = base_dir / f"temp_{audiobook.audiobook_id}_{i}.mp3"
                retry_count = 0
                success = False

                # Повторные попытки при ошибках
                while retry_count < max_retries and not success:
                    try:
                        success = await async_tts_save(chunk, "ru", temp_path)
                        if not success:
                            retry_count += 1
                            await asyncio.sleep(delay * 2)  # Увеличиваем задержку при повторе
                            continue

                        # Объединение частей
                        async with aiofiles.open(temp_path, "rb") as temp_file:
                            await main_file.write(await temp_file.read())

                    except Exception as e:
                        if "too many requests" in str(e).lower():
                            retry_count += 1
                            wait_time = delay * (2 ** retry_count)  # Экспоненциальная задержка
                            logging.info(f"Rate limit hit, waiting {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                        else:
                            logger.exception(f"Error processing chunk {i}: {e}")
                            break

                # Очистка временного файла
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception as e:
                    logger.exception(f"Error deleting temp file: {e}")

                await asyncio.sleep(delay)  # Базовая задержка между запросами

        # Проверка, что книга еще существует
        if not await session.scalar(select(Book).where(Book.book_id == book.book_id)):
            output_path.unlink(missing_ok=True)
            return

        # Сохранение пути к файлу
        audiobook.audio_url = str(output_path)
        await session.commit()

        # Уведомление пользователю
        await bot.send_message(
            chat_id,
            f"🎧 Аудиокнига '{book.title}' готова!")
        return output_path

    except Exception as e:
        logger.exception(f"Audiobook generation failed: {e}")
        try:
            await bot.send_message(
                chat_id,
                "⚠️ Не удалось сгенерировать аудиокнигу. Сервис синтеза речи перегружен. "
                "Попробуйте позже или загрузите аудиофайл вручную."
            )
        except:
            pass

        # Удаляем запись из БД, если не удалось сгенерировать
        await session.rollback()
        return None
