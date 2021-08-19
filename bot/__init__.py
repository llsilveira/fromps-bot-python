from .FrompsBot import FrompsBot
from .exceptions import FrompsBotException

from .cogs.weekly_races import Weekly


def create_bot(config, db):
    bot = FrompsBot(config)
    bot.add_cog(Weekly(bot, config, db))
    return bot


__all__ = [
    'FrompsBot',
    'FrompsBotException',
    'create_bot',
]
