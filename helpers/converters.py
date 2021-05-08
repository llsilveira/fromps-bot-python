from discord.ext import commands
from datetime import time, datetime


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
