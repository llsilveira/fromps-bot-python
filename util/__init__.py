from .config import load_conf
from .logging import setup_logging

from datetime import datetime, date
import re
import os


def get_resource(resource_name):
    resource_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../resources')
    return os.path.join(resource_path, resource_name)


def get_discord_name(discord_user):
    return "%s#%s" % (discord_user.name, discord_user.discriminator)


def remove_emojis(message, *, keep_delimiter=True):
    sub = r':\g<1>:' if keep_delimiter else r'\g<1>'
    return re.sub(r'<:([^:]*):[^>]*>', sub, message)


def time_to_timedelta(time):
    return datetime.combine(date.min, time) - datetime.min


def timedelta_to_str(delta):
    total = int(delta.total_seconds())
    if total < 0:
        total = -total
        value = '-'
    else:
        value = '+'

    total, seconds = divmod(total, 60)
    total, minutes = divmod(total, 60)
    days, hours = divmod(total, 60)
    if days > 0:
        value += "{:d}d ".format(days)
    value += "{:d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    return value
