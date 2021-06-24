from .ZRBRBot import ZRBRBot
from .cogs import weekly_races


def create_bot(config, db):
    bot = ZRBRBot(config)
    bot.add_cog(weekly_races.Weekly(bot, config, db))
    return bot
