from datatypes import Games


def get_discord_name(discord_user):
    return "%s#%s" % (discord_user.name, discord_user.discriminator)


class GameConverter:
    @staticmethod
    def get_reverse_map():
        if not hasattr(GameConverter, 'reverse_map'):
            reverse_map = {}
            for game in Games:
                for key in game.keys:
                    reverse_map[key] = game
            GameConverter.reverse_map = reverse_map
        return GameConverter.reverse_map

    @staticmethod
    def convert(argument):
        return GameConverter.get_reverse_map().get(argument, None)