__all__ = ("LEXICON", "LEXICON_COMMANDS", "DEFAULT_GENRES")

from config_data.config import config

if config.language == "ru":
    from lexicon.ru import LEXICON, LEXICON_COMMANDS, DEFAULT_GENRES
else:
    from lexicon.en import LEXICON, LEXICON_COMMANDS, DEFAULT_GENRES
