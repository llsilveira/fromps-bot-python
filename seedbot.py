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
async def on_message(message):
    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    await ctx.message.remove_reaction('⌚', ctx.bot.user)

    if isinstance(error, discord.ext.commands.errors.CommandInvokeError) \
            and isinstance(error.original, SeedBotException):
        await ctx.reply(error.original)
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.reply("O argumento '%s' é obrigatório." % error.param.name)
    elif isinstance(error, commands.errors.ConversionError):
        #TODO especificar o erro por tipo de parâmetro
        pass
    elif isinstance(error, commands.errors.CheckFailure):
        #TODO testar se foi uso de comando privilegiado e logar
        pass
    else:
        await ctx.reply("Ocorreu um erro inesperado.")
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
