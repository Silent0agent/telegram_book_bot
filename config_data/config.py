__all__ = ()

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from environs import Env

BASE_DIR = Path(__file__).parent.parent


@dataclass
class TgBot:
    token: str  # Токен для доступа к телеграм-боту
    admin_ids: list[int]  # Список id администраторов бота


@dataclass
class Config:
    tg_bot: TgBot
    log_level: str
    language: str
    proxy_url: Optional[str] = None


# Создаем функцию, которая будет читать файл .env и возвращать
# экземпляр класса Config с заполненными полями token и admin_ids
def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)
    return Config(
        tg_bot=TgBot(
            token=env("BOT_TOKEN"),
            admin_ids=list(map(int, env.list("ADMIN_IDS"))),
        ),
        log_level=env("LOG_LEVEL", "INFO").upper(),
        language=env("BOT_LANGUAGE", default="en"),
        proxy_url=env("PROXY_URL", default=None),
    )


config = load_config()
