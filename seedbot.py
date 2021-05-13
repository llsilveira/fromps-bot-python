#!/usr/bin/env python3

import config

import discord
from discord.ext import commands
from exceptions import SeedBotException
from database import Database
from cogs.weekly import Weekly

cfg = config.load_conf()
db = Database(**cfg['database'])

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=cfg['bot']['command_prefix'], intents=intents)


@bot.event
async def on_ready():
    print('Logged in as %s<%s>' % (bot.user.name, bot.user.id))
    print('------')


@bot.event
async def on_command_error(ctx, error):
    await ctx.message.remove_reaction('⌚', ctx.bot.user)

    if isinstance(error, commands.errors.CommandNotFound):
        pass
    elif isinstance(error, commands.errors.CommandInvokeError) \
            and isinstance(error.original, SeedBotException):
        error = error.original
        if error.send_reply:
            if error.reply_on_private:
                await ctx.author.send(error)
            else:
                await ctx.reply(error)
        if error.delete_origin:
            await ctx.message.delete()
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
