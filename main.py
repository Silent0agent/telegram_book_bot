__all__ = ()

import asyncio
import logging

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


# Функция конфигурирования и запуска бота
async def main():
    if config.log_level not in logging._nameToLevel:
        config.log_level = "INFO"
    # Конфигурируем логирование
    logging.basicConfig(
        level=config.log_level,
        format="%(filename)s:%(lineno)d #%(levelname)-8s "
        "[%(asctime)s] - %(name)s - %(message)s",
    )

    # Выводим в консоль информацию о начале запуска бота
    logger.info("Starting bot")

    storage = MemoryStorage()
    await db_session.global_init("database/books.db")
    database_session = await db_session.create_session()
    await init_genres(database_session)

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

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


asyncio.run(main())
