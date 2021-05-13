#!/usr/bin/env python3

import config

import discord
from discord.ext import commands
from exceptions import SeedBotException
from database import Database
from cogs.weekly import Weekly
import re

cfg = config.load_conf()
db = Database(**cfg['database'])

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=cfg['bot']['command_prefix'], intents=intents)

filter_signup = re.compile(r'^' + re.escape(cfg['bot']['command_prefix']) + r"(seed).*$")
filter_dm = re.compile(
    r'^' + re.escape(cfg['bot']['command_prefix']) + r"(time|forfeit|vod|entries|weeklycreate|weeklyclose).*$"
)
signup_channel = cfg['bot']['signup_channel']
testing = cfg['general'].get('testing', False)


@bot.event
async def on_message(message):

    # ignore messages sent by this bot or that were not sent to this bot's DM channel or to the signup channel
    if message.author.id == bot.user.id or (
            not isinstance(message.channel, discord.DMChannel) and message.channel.id != signup_channel):
        return

    signup_command = filter_signup.match(message.content)
    dm_command = filter_dm.match(message.content)

    # ignore any message that is not a command supposed to be sent in private
    if isinstance(message.channel, discord.DMChannel):
        if not dm_command:

            # inform the author if it is a command supposed to be sent on the signup channel
            if signup_command:
                await message.reply(
                    "O comando '%s' deve ser usado no canal #%s." % (
                        signup_command.group(0), bot.get_channel(signup_channel).name))

            return

    # ignore any message that is not a command supposed to be sent on the signup channel
    elif message.channel.id == signup_channel:
        if not signup_command:

            # The message is deleted to maintain the channel clean and spoiler free. For testing purposes, only commands
            # that are supposed to be sent in private are deleted when testing mode is active
            if not testing or dm_command:
                await message.delete()

            # inform the author if the command should be sent in private
            if dm_command:
                await message.author.send(
                    "O comando '%s' deve ser usado neste canal privado." % dm_command.group(0))

            return

    async with message.channel.typing():
        await bot.process_commands(message)


@bot.event
async def on_ready():
    print('Logged in as %s<%s>' % (bot.user.name, bot.user.id))
    print('------')


@bot.event
async def on_command_error(ctx, error):
    await ctx.message.remove_reaction('⌚', ctx.bot.user)

    if isinstance(error, commands.errors.CommandInvokeError) and isinstance(error.original, SeedBotException):
        await ctx.reply(error.original)
    elif isinstance(error, commands.errors.CheckFailure):
        pass
    else:
        print(type(error))
        print(error)
        raise(error)
        #TODO logar


@bot.event
async def on_command(ctx):
    await ctx.message.add_reaction('⌚')


@bot.event
async def on_command_completion(ctx):
    await ctx.message.add_reaction('✅')
    await ctx.message.remove_reaction('⌚', ctx.bot.user)


bot.add_cog(Weekly(bot, cfg['bot'], db))
if __name__ == '__main__':
    bot.run(cfg['bot']['token'])
