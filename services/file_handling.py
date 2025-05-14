import logging
from pathlib import Path
from typing import Tuple

import aiofiles
import chardet
from aiogram import Bot
from aiogram.types import FSInputFile, Audio

from database.db_session import create_session
from database.models import Page, Book

PAGE_SIZE = 1050
logger = logging.getLogger(__name__)


async def save_book_files(
        bot: Bot,
        book: Book,
        text_file_id: str,
        cover_file_id: str,
        base_dir: Path = Path(__file__).parent.parent
) -> Tuple[Path, Path]:
    """
    Сохраняет файлы книги (текст и обложку)
    Возвращает пути к сохраненным файлам (text_path, cover_path)
    """
    # Создаем директории
    books_dir = base_dir / "media" / "books"
    covers_dir = base_dir / "media" / "covers"
    books_dir.mkdir(parents=True, exist_ok=True)
    covers_dir.mkdir(parents=True, exist_ok=True)

    # Пути для сохранения
    text_path = books_dir / f"{book.book_id}.txt"
    cover_path = covers_dir / f"{book.book_id}.jpg"

    # Сохраняем текст книги
    await _save_text_file(bot, text_file_id, text_path)

    # Сохраняем обложку
    await _save_cover(bot, cover_file_id, cover_path)

    return text_path, cover_path


async def _save_text_file(bot: Bot, file_id: str, save_path: Path):
    """Сохранение текстового файла с конвертацией кодировки"""
    file = await bot.get_file(file_id)
    file_bytes = (await bot.download_file(file.file_path)).read()

    # Определяем кодировку
    detected_encoding = chardet.detect(file_bytes)['encoding'] or 'utf-8'

    # Декодируем и сохраняем в UTF-8
    try:
        text_content = file_bytes.decode(detected_encoding, errors='replace')
        async with aiofiles.open(save_path, 'w', encoding='utf-8') as f:
            await f.write(text_content)
    except UnicodeError as e:
        logger.error(f"Ошибка обработки текста: {str(e)}")


async def _save_cover(bot: Bot, file_id: str, save_path: Path):
    """Сохранение обложки книги"""
    photo_file = await bot.get_file(file_id)
    photo_bytes = await bot.download_file(photo_file.file_path)

    async with aiofiles.open(save_path, 'wb') as f:
        await f.write(photo_bytes.read())


async def cleanup_book_files(book_id: int, base_dir: Path = Path(__file__).parent.parent):
    """
    Удаляет файлы книги при ошибке
    """
    text_path = base_dir / "media" / "books" / f"{book_id}.txt"
    cover_path = base_dir / "media" / "covers" / f"{book_id}.jpg"

    try:
        if text_path.exists():
            text_path.unlink()
    except Exception as e:
        logger.error(f"Ошибка при удалении текстового файла: {e}")

    try:
        if cover_path.exists():
            cover_path.unlink()
    except Exception as e:
        logger.error(f"Ошибка при удалении обложки: {e}")


# Функция, проверяющая текст на окончание многоточиями
def _check_for_ellipsis(text: str, start: int, size: int):
    punctuation_marks = [',', '.', '!', ':', ';', '?']
    if text[start:start + size][-1] in punctuation_marks:
        if text[start:start + size + 1][-1] in punctuation_marks:
            return False
    return True


# Функция, возвращающая строку с текстом страницы и ее размер
def _get_part_text(text: str, start: int, size: int) -> tuple[str, int]:
    text += ' '
    punctuation_marks = [',', '.', '!', ':', ';', '?']
    while not _check_for_ellipsis(text, start, size):
        size -= 1
    part_text = text[start:start + size] + ' '
    for i in range(1, len(part_text)):
        if part_text[-i] in punctuation_marks:
            return part_text[:-i + 1], len(part_text[:-i + 1])
    return '', 0


async def prepare_book(book_id: int) -> None:
    text = await get_book_text(book_id)

    start = 0
    count = 1

    session = await create_session()
    try:
        while start < len(text):
            page_text, part_size = _get_part_text(text, start, PAGE_SIZE)
            if page_text:
                session.add(Page(
                    book_id=book_id,
                    num=count,
                    text=page_text.strip()
                ))
                start += part_size
                count += 1
            else:
                break
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()


async def get_book_text(book_id: int):
    base_dir = Path(__file__).parent.parent
    book_dir = base_dir / "media" / "books"
    book_dir.mkdir(parents=True, exist_ok=True)
    book_path = book_dir / f'{book_id}.txt'

    # Чтение файла
    with open(book_path, 'r', encoding='utf-8') as file:
        text = file.read()
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    return text


async def load_cover(book_id: str):
    """Асинхронно загружает обложку книги"""
    base_dir = Path(__file__).parent.parent
    covers_dir = base_dir / "media" / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)
    cover_path = covers_dir / f'{book_id}.jpg'

    if not cover_path.exists():
        return None  # Или путь к дефолтной обложке
    return FSInputFile(str(cover_path))


async def save_audiobook(
        bot: Bot,
        audio: Audio,
        audiobook_id: int
) -> Path:
    """Сохраняет аудиофайл и возвращает путь к нему"""
    try:
        audiobooks_path = Path("media/audiobooks")
        audiobooks_path.mkdir(parents=True, exist_ok=True)
        file_path = audiobooks_path / f"{audiobook_id}.mp3"

        file_info = await bot.get_file(audio.file_id)
        await bot.download_file(file_info.file_path, destination=file_path)

        return file_path
    except Exception as e:
        # Удаляем файл, если он был частично сохранен
        if 'file_path' in locals():
            file_path.unlink(missing_ok=True)
        raise e


def delete_audiobook_file(audiobook_id: int) -> bool:
    """Удаляет аудиофайл по ID"""
    file_path = Path("media/audiobooks") / f"{audiobook_id}.mp3"
    try:
        file_path.unlink(missing_ok=True)
        return True
    except:
        return False


def delete_book_files(book_id: int, audiobook_ids: list):
    cover_path = Path("media/covers") / f"{book_id}.jpg"
    book_path = Path("media/books") / f"{book_id}.txt"
    try:
        cover_path.unlink(missing_ok=True)
        book_path.unlink(missing_ok=True)
        for audibook_id in audiobook_ids:
            delete_audiobook_file(audibook_id)
        return True
    except:
        return False
