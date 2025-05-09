from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User
from database.db_session import create_session
from typing import Union
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from states.states import FSMAddBook, FSMCreateReview


# Создание подключения к базе данных для пользователя
class DatabaseMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        session = await create_session()  # Создаем сессию
        data["session"] = session
        try:
            result = await handler(event, data)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Добавление пользователя в базу данных если его там ещё нет
class UserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
            event: Union[Message, CallbackQuery],
            data: Dict[str, Any]
    ) -> Any:
        session: AsyncSession = data["session"]

        # Получаем пользователя из события
        if isinstance(event, Union[Message, CallbackQuery]):
            user_id = event.from_user.id
            username = event.from_user.username
            first_name = event.from_user.first_name
            last_name = event.from_user.last_name
        else:
            # Если это не Message/CallbackQuery, пропускаем middleware
            return await handler(event, data)

        # Проверяем существование пользователя
        user = await session.get(User, user_id)

        if not user:
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)  # Обновляем атрибуты

        data["user"] = user
        return await handler(event, data)


# Обработка посторонних действий при заполнении данных о книге/отзыве
class StateValidationMiddleware(BaseMiddleware):
    def __init__(self):
        # Конфигурация для разных процессов
        self.process_config = {
            'book_adding': {
                'state_group': FSMAddBook,
                'allowed_actions': {
                    'choose_genre', 'remove_genre', 'genres_list_forward',
                    'genres_list_backward', 'confirm_genres', 'fill_is_public_true',
                    'fill_is_public_false'
                },
                'data_key': 'add_book',
                'cancel_command': '/cancel_add_book',
                'warning': "⚠️ Завершите добавление книги или отмените командой\n/cancel_add_book"
            },
            'review_adding': {
                'state_group': FSMCreateReview,
                'allowed_actions': {'fill_review_rating', 'fill_review_text'},
                'data_key': 'add_review',
                'cancel_command': '/cancel_create_review',
                'warning': "⚠️ Завершите создание отзыва или отмените командой\n/cancel_create_review"
            }
        }

    async def __call__(
            self,
            handler: Callable,
            event: Union[CallbackQuery, Message],
            data: Dict[str, Any]
    ) -> Any:
        # Пропускаем не callback-сообщения
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        state: FSMContext = data.get('state')
        if not state:
            return await handler(event, data)

        current_state = await state.get_state()
        if not current_state:
            return await handler(event, data)

        # Проверяем все процессы
        for process_name, config in self.process_config.items():
            if current_state in [s.state for s in config['state_group'].__all_states__]:
                if not self._is_allowed_action(event.data, config['allowed_actions']):
                    await event.answer(config['warning'], show_alert=True)
                    return

                if not await self._is_message_valid(event, state, config['data_key']):
                    await event.answer("Сообщение устарело", show_alert=True)
                    return

        return await handler(event, data)

    def _is_allowed_action(self, action_data: str, allowed_actions: set) -> bool:
        """Проверяет разрешенные действия для процесса"""
        return any(action_data.startswith(action) for action in allowed_actions)

    async def _is_message_valid(self, event: CallbackQuery, state: FSMContext, data_key: str) -> bool:
        """Проверяет актуальность сообщения"""
        data = await state.get_data()
        current_message_id = data.get(f'active_{data_key}_message_id')
        return current_message_id == event.message.message_id


# Обработка ввода команд, сбрасывающих состояние (данные о текущей книге и текущих результатах поиска не сбрасываются)
class StateResetMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable,
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        state: FSMContext = data.get('state')
        if not state:
            return await handler(event, data)

        # Команды, которые сбрасывают состояние
        reset_commands = ['/start', '/bookmarks']

        if any(event.text.startswith(cmd) for cmd in reset_commands):
            current_state = await state.get_state()

            # Определяем какие данные нужно очистить
            cleanup_map = {
                'FSMAddBook': ['add_book', 'active_add_book_message_id'],
                'FSMCreateReview': ['add_review'],
                # 'FSMSearchBook': ['search_by_genres', 'active_search_by_genres_message_id']
            }

            for state_group, keys in cleanup_map.items():
                if current_state and current_state.startswith(state_group):
                    # Удаляем специфичные данные
                    current_data = await state.get_data()
                    new_data = {k: v for k, v in current_data.items() if k not in keys}
                    await state.set_data(new_data)
                    break

            # Всегда сбрасываем состояние
            await state.set_state(default_state)

        return await handler(event, data)


# Обработка посторонних действий при поиске (сброс данных о поиске по жанрам)
class SearchValidationMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable,
            event: Union[Message, CallbackQuery],
            data: Dict[str, Any]
    ) -> Any:
        state: FSMContext = data.get('state')
        current_state = await state.get_state() if state else None

        # Проверяем только состояния поиска
        if current_state and current_state.startswith('FSMSearchBook'):
            # Если это сообщение (ввод текста)
            if isinstance(event, Message):
                if event.text and event.text.startswith('/'):
                    await self._reset_search_by_genres(state)
                    return await handler(event, data)
                elif not event.text:  # Если сообщение не текстовое (фото, стикер и т.д.)
                    await self._reset_search_by_genres(state)
                    await event.answer(
                        "❌ Пожалуйста, используйте только текстовые сообщения для поиска.\n❌ Поиск прерван. Начните заново.")
                    return  # Прерываем дальнейшую обработку

            # Если это callback (нажатие кнопки)
            elif isinstance(event, CallbackQuery):
                allowed_actions = {
                    'genres_list_forward', 'genres_list_backward',
                    'choose_genre'
                }

                if not any(event.data.startswith(action) for action in allowed_actions):
                    await self._reset_search_by_genres(state)
                    await event.answer("❌ Поиск прерван. Начните заново.", show_alert=True)

        return await handler(event, data)

    async def _reset_search_by_genres(self, state: FSMContext):
        """Полностью очищает состояние поиска"""
        data = await state.get_data()
        for key in ['search_by_genres', 'active_search_by_genres_message_id']:
            data.pop(key, None)
        await state.set_data(data)
        await state.set_state(default_state)
