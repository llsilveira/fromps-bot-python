from discord.ext import commands
from datetime import datetime
from datatypes import Games
import functools


def get_discord_name(discord_user):
    return "%s#%s" % (discord_user.name, discord_user.discriminator)


class DatetimeConverter(commands.Converter):
    def __init__(self, format):
        self.format = format

    async def convert(self, ctx, argument):
        return datetime.strptime(argument, self.format)


class TimeConverter(commands.Converter):
    def __init__(self, format):
        self.format = format

    async def convert(self, ctx, argument):
        return datetime.strptime(argument, self.format).time()


class GameConverter(commands.Converter):
    @staticmethod
    def get_reverse_map():
        if not hasattr(GameConverter, 'reverse_map'):
            reverse_map = {}
            for game in Games:
                for key in game.keys:
                    reverse_map[key] = game
            GameConverter.reverse_map = reverse_map
        return GameConverter.reverse_map

    async def convert(self, ctx, argument):
        return GameConverter.get_reverse_map()[argument]