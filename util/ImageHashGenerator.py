import io
import yaml
from PIL import Image

from datatypes import Games
from util import get_resource


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
