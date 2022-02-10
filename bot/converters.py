from discord.ext import commands
from datetime import datetime

from datatypes import Games
from util import remove_emojis


class DatetimeConverter(commands.Converter):
    def __init__(self, parse_format="%d/%m/%Y-%H:%M", description_format="dd/mm/aaaa-HH:MM"):
        self.parse_format = parse_format
        self.description_format = description_format
        super().__init__()

    async def convert(self, ctx, argument):
        return datetime.strptime(remove_emojis(argument), self.parse_format)


class DateConverter(commands.Converter):
    def __init__(self, parse_format="%d/%m/%Y", description_format="dd/mm/aaaa"):
        self.parse_format = parse_format
        self.description_format = description_format
        super().__init__()

    async def convert(self, ctx, argument):
        return datetime.strptime(remove_emojis(argument), self.parse_format).date()


class TimeConverter(commands.Converter):
    def __init__(self, parse_format="%H:%M:%S", description_format="H:MM:SS"):
        self.parse_format = parse_format
        self.description_format = description_format
        super().__init__()

    async def convert(self, ctx, argument):
        return datetime.strptime(remove_emojis(argument), self.parse_format).time()


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
        game = GameConverter.get_reverse_map().get(str.lower(argument), None)
        if game is None:
            raise ValueError("Game not found!")
        return game
