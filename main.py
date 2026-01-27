__all__ = ()

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config_data.config import config
from database import db_session
from database.init_db import init_genres
from handlers import (
    add_book_handlers,
    audiobook_handlers,
    bookmarks_handlers,
    main_handlers,
    other_handlers,
    read_book_handlers,
    review_handlers,
    search_handlers,
)
from keyboards.main_menu import set_main_menu
from middlewares.outer import (
    DatabaseMiddleware,
    SearchValidationMiddleware,
    StateResetMiddleware,
    StateValidationMiddleware,
    UserMiddleware,
)

# Инициализируем логгер
logger = logging.getLogger(__name__)


async def close_connections():
    """Закрываем все соединения с БД"""
    try:
        from database.db_session import close_connection_pool

        await close_connection_pool()
    except Exception as e:
        logger.error(f"Error closing connections: {e}")


async def shutdown(dp: Dispatcher, bot: Bot):
    """Корректное завершение работы"""
    logger.info("Shutting down bot...")

    # Останавливаем polling
    await dp.stop_polling()

    # Закрываем сессию бота
    await bot.session.close()

    # Закрываем соединения с БД
    await close_connections()

    logger.info("Bot shutdown complete")


# Функция конфигурирования и запуска бота
async def main():
    # Конфигурируем логирование
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s "
        "[%(asctime)s] - %(name)s - %(message)s",
    )

    # Выводим в консоль информацию о начале запуска бота
    logger.info("Starting bot")

    storage = MemoryStorage()
    await db_session.global_init("database/books.db")
    database_session = await db_session.create_session()
    await init_genres(database_session)
    await database_session.close()

    session = (
        AiohttpSession(proxy=config.proxy_url) if config.proxy_url else None
    )

    # Инициализируем бот и диспетчер
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )

    dp = Dispatcher(storage=storage)
    # Настраиваем главное меню бота
    await set_main_menu(bot)

    # Регистрируем мидлвари в диспетчере
    dp.update.middleware(DatabaseMiddleware())
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    dp.callback_query.middleware(StateValidationMiddleware())
    dp.message.middleware(SearchValidationMiddleware())
    dp.message.middleware(StateResetMiddleware())
    dp.callback_query.middleware(SearchValidationMiddleware())

    # Регистрируем роутеры в диспетчере
    dp.include_router(main_handlers.router)
    dp.include_router(add_book_handlers.router)
    dp.include_router(review_handlers.router)
    dp.include_router(audiobook_handlers.router)
    dp.include_router(search_handlers.router)
    dp.include_router(bookmarks_handlers.router)
    dp.include_router(read_book_handlers.router)
    dp.include_router(other_handlers.router)

    # Пропускаем накопившиеся апдейты
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.exception(f"Bot stopped with error: {e}")
    finally:
        # Гарантируем закрытие ресурсов
        await shutdown(dp, bot)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
