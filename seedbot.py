#!/usr/bin/env python3

import config

import discord
from discord.ext import commands
from exceptions import SeedBotException
from database import Database
from cogs.weekly import Weekly
from helpers import GameConverter, DatetimeConverter, TimeConverter, get_discord_name

import re
import logging

logger = logging.getLogger(__name__)

cfg = config.load_conf()
db = Database(**cfg['database'])

intents = discord.Intents.default()
intents.members = True


class SeedbotHelpCommand(commands.DefaultHelpCommand):
    def __init__(self):
        super().__init__(
            command_attrs={
                "name": "ajuda",
                "help": "Mostrar esta mensagem"
            },
            commands_heading="Comandos:",
            no_category="Sem categoria",
            dm_help=True
        )

    def get_ending_note(self):
        command_name = self.invoked_with
        return "Envie '{0}{1} comando' para mais informações sobre um comando.".format(self.clean_prefix, command_name)


bot = commands.Bot(
    command_prefix=cfg['bot']['command_prefix'],
    intents=intents,
    help_command=SeedbotHelpCommand()
)

filter_command = re.compile(r'^' + re.escape(cfg['bot']['command_prefix']) + r'(.*)$')
filter_signup = re.compile(r'^' + re.escape(cfg['bot']['command_prefix']) + r'(ajuda|semanais|weeklies|semente|seed).*$')
filter_dm = re.compile(
    r'^' + re.escape(cfg['bot']['command_prefix']) + r'(ajuda|semanais|weeklies|tempo|time|desistir|forfeit|video|gravacao|vod|entradas|inscricoes|entries|criarsemanal|weeklycreate|weeklytestcreate|encerrarsemanal|weeklyclose).*$'
)
signup_channel = cfg['bot']['signup_channel']
testing = cfg['general'].get('testing', False)

param_map = {
    "codigo_do_jogo": "o código do jogo",
    "tempo": "o tempo",
    "url_do_vod": "a URL do seu VOD",
    "url_da_seed": "a URL da seed",
    "codigo_de_verificacao": "o código de verificação",
    "limite_para_envios": "o limite para envios"
}


async def ping_on_error(ctx, error):
    user = await bot.fetch_user(cfg['bot']['ping_on_error'])
    dm = user.dm_channel
    if dm is None:
        dm = await user.create_dm()
    msg = """
    Ocorreu um erro inesperado. Detalhes do erro:
    
    Mensagem: %s
    Autor: %s
    Tipo do Erro: %s
    Mensagem do Erro: %s
    """ % (ctx.message.content, get_discord_name(ctx.author), type(error), str(error))

    await dm.send(msg)


@bot.event
async def on_message(message):

    # ignore messages sent by this bot or that were not sent to this bot's DM channel or to the signup channel
    if message.author.id == bot.user.id or (
            not isinstance(message.channel, discord.DMChannel) and message.channel.id != signup_channel):
        return

    is_command = filter_command.match(message.content)
    signup_command = filter_signup.match(message.content)
    dm_command = filter_dm.match(message.content)

    # ignore any message that is not a command supposed to be sent in private
    if isinstance(message.channel, discord.DMChannel):
        if not is_command:
            return
        if not dm_command and signup_command:
            await message.reply(
                "O comando '%s' deve ser usado no canal #%s." % (
                    signup_command.group(1), bot.get_channel(signup_channel).name))
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
                    "O comando '%s' deve ser usado neste canal privado." % dm_command.group(1))
            return

    async with message.channel.typing():
        await bot.process_commands(message)


@bot.event
async def on_ready():
    print('Logged in as %s<%s>' % (bot.user.name, bot.user.id))
    print('------')
    logger.info("BOT IS READY!")


@bot.event
async def on_command_error(ctx, error):
    async def handle_unknown_exception():
        await ctx.reply("Ocorreu um erro inesperado.")
        await ping_on_error(ctx, error)
        logger.exception(error)

    await ctx.message.remove_reaction('⌚', ctx.bot.user)

    if isinstance(error, commands.errors.CommandInvokeError) and isinstance(error.original, SeedBotException):
        await ctx.reply(error.original)

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply("Você deve informar %s. Consulte o comando 'ajuda' para mais informações." % param_map[error.param.name])

    elif isinstance(error, commands.TooManyArguments):
        await ctx.reply(
            "Você deve fornecer apenas os parâmetros requeridos pelo comando. Consulte o comando 'ajuda' para mais informações."
        )

    elif isinstance(error, commands.errors.ConversionError):
        converter = error.converter
        if isinstance(converter, GameConverter):
            await ctx.reply("O código informado não corresponde a um jogo conhecido.")
        elif isinstance(converter, DatetimeConverter):
            if isinstance(converter, TimeConverter):
                msg = "O tempo fornecido deve "
            else:
                msg = "A data e hora fornecidos devem "
            msg += "estar no formato '%s'." % converter.description_format
            await ctx.reply(msg)
        else:
            await handle_unknown_exception()

    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.reply("Comando não encontrado.")

    else:
        await handle_unknown_exception()


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
