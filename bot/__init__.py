from .RBRBot import RBRBot
from .exceptions import RBRBotException

from .cogs.weekly_races import Weekly


def create_bot(config, db):
    bot = RBRBot(config)
    bot.add_cog(Weekly(bot, config, db))
    return bot


__all__ = [
    'RBRBot',
    'RBRBotException',
    'create_bot',
]
