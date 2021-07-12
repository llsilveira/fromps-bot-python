import re


def get_discord_name(discord_user):
    return "%s#%s" % (discord_user.name, discord_user.discriminator)


def remove_emojis(message, *, keep_delimiter=True):
    sub = r':\g<1>:' if keep_delimiter else r'\g<1>'
    return re.sub(r'<:([^:]*):[^>]*>', sub, message)
