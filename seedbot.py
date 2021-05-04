#!/usr/bin/env python3
# This example requires the 'members' privileged intents

import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command()
async def mmseed(ctx):
    await ctx.message.author.send('ou aqui')

@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel):
        channel = bot.get_channel(int(780745477842403338))
        await channel.send(f"{message.author} sent:\n```{message.content}```\n{message.attachments[0].url}")
    await bot.process_commands(message)

bot.run('TOKEN')
