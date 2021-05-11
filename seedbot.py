#!/usr/bin/env python3

import config

import discord
from discord.ext import commands
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

bot.add_cog(Weekly(bot, cfg['bot'], db))
if __name__ == '__main__':
    bot.run(cfg['bot']['token'])
