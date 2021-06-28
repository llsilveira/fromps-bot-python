import discord
from discord.ext import commands

from helpers import get_discord_name
from .exceptions import ZRBRBotException
from .converters import TimeConverter, DatetimeConverter, GameConverter

import logging
logger = logging.getLogger(__name__)


param_map = {
    "codigo_do_jogo": "o código do jogo",
    "tempo": "o tempo",
    "url_do_vod": "a URL do seu VOD",
    "url_da_seed": "a URL da seed",
    "codigo_de_verificacao": "o código de verificação",
    "limite_para_envios": "o limite para envios"
}


async def ping_on_error(user, ctx, error):
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


class ZRBRBot(commands.Bot):
    class ZRBRHelpCommand(commands.DefaultHelpCommand):
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
            return "Envie '{0}{1} comando' para mais informações sobre um comando.".format(self.clean_prefix,
                                                                                           command_name)

    def __init__(self, config):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix=config['command_prefix'],
            intents=intents,
            help_command=ZRBRBot.ZRBRHelpCommand()
        )

        self.ping_on_error = config.get('ping_on_error', False)
        self.signup_channel_id = config.get('signup_channel_id')
        self.cleanup_signup_channel = config.get('cleanup_signup_channel', False)

        self.busy_emoji = config.get('busy_emoji', '⌚')
        self.success_emoji = config.get('success_emoji', '✅')
        self.error_emoji = config.get('error_emoji', '❌')

    async def on_message(self, message):
        if message.author.id == self.user.id or (
                not isinstance(message.channel, discord.DMChannel) and message.channel.id != self.signup_channel_id):
            return

        async with message.channel.typing():
            await self.process_commands(message)

    async def invoke(self, ctx):
        message = ctx.message
        channel = message.channel
        command = ctx.command

        if isinstance(channel, discord.DMChannel):
            if command is None:
                return

            if command.__original_kwargs__.get('signup_only', False):
                await message.reply(
                    "Este comando deve ser usado no canal #%s." % self.get_channel(self.signup_channel_id).name)
                return

        elif channel.id == self.signup_channel_id:
            if command is None:
                if self.cleanup_signup_channel:
                    await message.delete()
                return

            if command.__original_kwargs__.get('dm_only', False):
                if self.cleanup_signup_channel:
                    await message.delete()
                await message.author.send("O comando '%s' deve ser usado neste canal privado." % ctx.invoked_with)
                return

        await super().invoke(ctx)

    async def on_command(self, ctx):
        await ctx.message.add_reaction(self.busy_emoji)

    async def on_command_completion(self, ctx):
        await ctx.message.add_reaction(self.success_emoji)
        await ctx.message.remove_reaction(self.busy_emoji, self.user)

    async def on_command_error(self, ctx, error):
        await ctx.message.add_reaction(self.error_emoji)
        await ctx.message.remove_reaction(self.busy_emoji, self.user)

        async def handle_unknown_exception():
            logger.exception(error)

            await ctx.reply("Ocorreu um erro inesperado.")
            if hasattr(self, 'ping_on_error'):
                user = await self.fetch_user(self.ping_on_error)
                await ping_on_error(user, ctx, error)

        if isinstance(error, commands.errors.CommandInvokeError) and isinstance(error.original, ZRBRBotException):
            await ctx.reply(error.original)

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Você deve informar %s. Consulte o comando 'ajuda' para mais informações." % param_map[
                error.param.name])

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
            await ctx.reply("Comando desconhecido.")

        elif isinstance(error, commands.errors.BadBoolArgument):
            await ctx.reply("%s não é um valor reconhecido." % error.argument)

        else:
            await handle_unknown_exception()
