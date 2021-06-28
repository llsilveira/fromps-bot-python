from .ZRBRBot import ZRBRBot
from .exceptions import ZRBRBotException

from .cogs.weekly_races import Weekly


def create_bot(config, db):
    bot = ZRBRBot(config)
    bot.add_cog(Weekly(bot, config, db))
    return bot


__all__ = [
    'ZRBRBot',
    'ZRBRBotException',
    'create_bot',
]
