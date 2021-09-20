from .FrompsBot import FrompsBot
from .exceptions import FrompsBotException

from .cogs.weekly_races import Weekly


def create_bot(db, config):
    bot = FrompsBot(**config['bot'])
    bot.add_cog(Weekly(bot, db, **config['weeklies']))
    return bot


__all__ = [
    'FrompsBot',
    'FrompsBotException',
    'create_bot',
]
