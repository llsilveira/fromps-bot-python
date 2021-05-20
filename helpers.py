import os
import yaml
import re
import discord
from discord.ext import commands
from datetime import datetime

from datatypes import Games
from exceptions import SeedBotException


def get_discord_name(discord_user):
    return "%s#%s" % (discord_user.name, discord_user.discriminator)


def get_resource(resource_name):
    resource_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
    return os.path.join(resource_path, resource_name)


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

    def check(self, user, game):
        if not self.is_monitor(user):
            raise SeedBotException("Este comando deve ser executado apenas por monitores.")

        if not self.is_monitor(user, game):
            raise SeedBotException("Você não é monitor de %s." % game)


class SeedHashHandler:
    _url_matcher = re.compile("https?://")

    def __init__(self, bot):
        self.bot = bot

    def get_hash(self, game, hash_str):
        if game is Games.MMR:
            if not SeedHashHandler._url_matcher.match(hash_str):
                raise SeedBotException("O código de verificação de %s deve ser a URL da imagem." % game)
            return hash_str

        if game is Games.OOTR or game is Games.ALTTPR:
            return self.build_emoji_hash(game, hash_str)

        return hash_str

    def build_emoji_hash(self, game, hash_str):
        items = hash_str.split("/")
        emoji_list = list(map(
            lambda item: str(discord.utils.get(self.bot.emojis, name=SeedHashHandler._get_emoji(game, item))),
            items
        ))
        return " ".join(emoji_list)

    @staticmethod
    def _get_emoji(game, item):
        try:
            return SeedHashHandler._get_map()[game][SeedHashHandler._translate(item)]
        except KeyError:
            raise SeedBotException("Não foi possível encontrar o emoji para '%s'." % item)

    @staticmethod
    def _get_map():
        if not hasattr(SeedHashHandler, '_emoji_map'):
            emoji_dict = SeedHashHandler._load()
            emoji_map = {Games[game_name]: emoji_map for game_name, emoji_map in emoji_dict.items()}
            SeedHashHandler._emoji_map = emoji_map

        return SeedHashHandler._emoji_map

    @staticmethod
    def _load():
        with open(get_resource('emoji_map.yaml'), 'r') as emoji_map_file:
            return yaml.safe_load(emoji_map_file)

    @staticmethod
    def _translate(item):
        return str.lower(item).replace(" ", "")


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

