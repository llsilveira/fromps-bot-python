from discord.ext import commands
from datetime import datetime

from datatypes import Games


def get_discord_name(discord_user):
    return "%s#%s" % (discord_user.name, discord_user.discriminator)


class MonitorChecker:
    def __init__(self, cfg):
        self.monitors = {Games[key]: monitor for (key, monitor) in cfg['monitors'].items()}

    def is_monitor(self, user, game=None):
        user_name = get_discord_name(user)

        if game is not None:
            if game not in self.monitors.keys():
                return False
            return user_name in self.monitors[game]

        for monitor_list in self.monitors.values():
            if user_name in monitor_list:
                return True
        return False


class DatetimeConverter(commands.Converter):
    def __init__(self, parse_format, description_format):
        self.parse_format = parse_format
        self.description_format = description_format
        super().__init__()

    async def convert(self, ctx, argument):
        return datetime.strptime(argument, self.parse_format)


class TimeConverter(DatetimeConverter):
    def __init__(self, parse_format, description_format):
        super().__init__(parse_format, description_format)

    async def convert(self, ctx, argument):
        var = await super().convert(ctx, argument)
        return var.time()


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

