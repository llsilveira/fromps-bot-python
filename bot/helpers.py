import io
import os
import yaml
from discord.ext import commands
from datetime import datetime
from PIL import Image

from datatypes import Games
from bot.exceptions import SeedBotException


def get_discord_name(discord_user):
    return "%s#%s" % (discord_user.name, discord_user.discriminator)


def get_resource(resource_name):
    resource_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../resources')
    return os.path.join(resource_path, resource_name)


class ImageHashGenerator:
    hash_img_size = (24, 24)
    hash_space = 4

    def generate(self, game, hash_str):
        items = hash_str.split("/")
        count = len(items)
        if count != 5:
            raise ValueError("O código HASH informado deve conter 5 itens.")

        width = self.hash_img_size[0]
        height = self.hash_img_size[1]
        space = self.hash_space

        with Image.new("RGBA", (count*width + (count-1)*space, height)) as img, \
                Image.open(get_resource("hash_icons.png"), "r") as source_img:
            start = 0
            for item in items:
                position = self._get_position(game, item)
                box = (
                    position[1]*width,
                    position[0]*height,
                    (position[1] + 1)*width,
                    (position[0] + 1)*height
                )
                img.paste(source_img.crop(box), (start, 0))
                start += width + space

            with io.BytesIO() as img_bytes:
                img.save(img_bytes, format="PNG", optimize=True)
                return img_bytes.getvalue()

    @staticmethod
    def _get_position(game, item):
        try:
            return ImageHashGenerator._get_map()[game][ImageHashGenerator._translate(item)]
        except KeyError:
            raise ValueError("Valor desconhecido para o hash: '%s'." % item)

    @staticmethod
    def _get_map():
        if not hasattr(ImageHashGenerator, '_icon_map'):
            icon_dict = ImageHashGenerator._load()
            _icon_map = {Games[game_name]: icon_map for game_name, icon_map in icon_dict.items()}
            ImageHashGenerator._icon_map = _icon_map

        return getattr(ImageHashGenerator, '_icon_map')

    @staticmethod
    def _load():
        with open(get_resource('icon_map.yaml'), 'r') as image_map_file:
            return yaml.safe_load(image_map_file)

    @staticmethod
    def _translate(item):
        return str.lower(item).replace(" ", "")


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


class DatetimeConverter(commands.Converter):
    def __init__(self, parse_format = "%d/%m/%Y-%H:%M", description_format = "dd/mm/aaaa-HH:MM"):
        self.parse_format = parse_format
        self.description_format = description_format
        super().__init__()

    async def convert(self, ctx, argument):
        return datetime.strptime(argument, self.parse_format)


class TimeConverter(commands.Converter):
    def __init__(self, parse_format = "%H:%M:%S", description_format = "H:MM:SS"):
        self.parse_format = parse_format
        self.description_format = description_format
        super().__init__()

    async def convert(self, ctx, argument):
        return datetime.strptime(argument, self.parse_format).time()


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

