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
        return GameConverter.get_reverse_map().get(str.lower(argument), None)
