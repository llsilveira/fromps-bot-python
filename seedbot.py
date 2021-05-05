#!/usr/bin/env python3
# This example requires the 'members' privileged intents

import discord
from discord.ext import commands
from benedict import benedict

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command(name = 'alttpseed', help = 'Solicitar seed da semanal de A Link to the Past')
async def alttpseed(ctx):
    await ctx.message.author.send(g['ALTTP'])

@bot.command(name = 'ootseed', help = 'Solicitar seed da semanal de Ocarina of Time')
async def ootseed(ctx):
    await ctx.message.author.send(g['OoT'])

@bot.command(name = 'mmseed', help = 'Solicitar seed da semanal de Majora\'s Mask')
async def mmseed(ctx):
    await ctx.message.author.send(g['MM'])

@bot.command(name = 'smz3seed', help = 'Solicitar seed da semanal de SMZ3')
async def smz3seed(ctx):
    await ctx.message.author.send(g['SMZ3'])

@bot.command(name = 'pkmncrystalseed', help = 'Solicitar seed da semanal de Pokémon Crystal')
async def pkmncrystalseed(ctx):
    await ctx.message.author.send(g['PkmnCrystal'])

@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel):
        channel = bot.get_channel(int(780745477842403338))
        await channel.send(f"{message.author} sent:\n```{message.content}```\n{message.attachments[0].url}")
    await bot.process_commands(message)

g = benedict.from_yaml('games.yaml')

bot.run('TOKEN')
