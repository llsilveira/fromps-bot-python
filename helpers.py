from discord.ext import commands
from datetime import datetime
import functools


def get_discord_name(discord_user):
    return "%s#%s" % (discord_user.name, discord_user.discriminator)


def feedback_reactions(*, busy_emoji="⌚", success_emoji="✅", fail_emoji="🚫"):
    def decorator(f):
        @functools.wraps(f)
        async def wrapper(*args, **kwargs):
            context = args[0]
            if not isinstance(context, commands.Context):
                context = args[1]

            message = context.message
            await message.add_reaction(busy_emoji)
            try:
                result = await f(*args, **kwargs)
                if result is None or result:
                    await message.add_reaction(success_emoji)
                else:
                    await message.add_reaction(fail_emoji)
            except Exception as e:
                await message.add_reaction(fail_emoji)
                raise e
            finally:
                await message.remove_reaction(busy_emoji, context.bot.user)
        return wrapper
    return decorator


class DatetimeConveter(commands.Converter):
    def __init__(self, format):
        self.format = format

    async def convert(self, ctx, argument):
        return datetime.strptime(argument, self.format)


class TimeConverter(commands.Converter):
    def __init__(self, format):
        self.format = format

    async def convert(self, ctx, argument):
        return datetime.strptime(argument, self.format).time()
