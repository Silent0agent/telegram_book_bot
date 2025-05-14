import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config_data.config import Config, load_config
from database import db_session
from database.db_session import create_session
from database.init_db import init_genres
from handlers import other_handlers, main_handlers, read_book_handlers, search_handlers, \
    add_book_handlers, bookmarks_handlers, review_handlers, audiobook_handlers
from keyboards.main_menu import set_main_menu
from middlewares.outer import DatabaseMiddleware, UserMiddleware, StateValidationMiddleware, \
    SearchValidationMiddleware, StateResetMiddleware

# Инициализируем логгер
logger = logging.getLogger(__name__)


# Функция конфигурирования и запуска бота
async def main():
    # Конфигурируем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')

    # Выводим в консоль информацию о начале запуска бота
    logger.info('Starting bot')

    # Загружаем конфиг в переменную config
    config: Config = load_config()
    storage = MemoryStorage()
    await db_session.global_init('database/books.db')
    session = await create_session()
    await init_genres(session)
    # Инициализируем бот и диспетчер
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
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
