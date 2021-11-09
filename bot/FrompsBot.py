import discord
from discord.ext import commands

from util import get_discord_name
from .exceptions import FrompsBotException
from .converters import TimeConverter, DatetimeConverter, GameConverter

import logging
logger = logging.getLogger(__name__)


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


class FrompsBot(commands.Bot):
    class FrompsBotHelpCommand(commands.DefaultHelpCommand):
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

    def __init__(
            self,
            token,
            channels,
            *,
            cleanup_signup_channels=False,
            ping_on_error=False,
            busy_emoji='⌚',
            success_emoji='✅',
            error_emoji='❌',
            **kwargs
    ):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            intents=intents,
            help_command=FrompsBot.FrompsBotHelpCommand(),
            **kwargs
        )

        self.token = token
        self.channels = channels

        self.signup_channels = []
        self.cleanup_signup_channels = cleanup_signup_channels
        self.ping_on_error = ping_on_error

        self.busy_emoji = busy_emoji
        self.success_emoji = success_emoji
        self.error_emoji = error_emoji

    async def on_ready(self):
        try:
            channels = self.channels
            for guild_id in channels:
                guild = discord.utils.find(lambda guild: guild.id == guild_id, self.guilds)
                if guild is None:
                    raise ValueError("Configuration Error: This bot is not on a guild with id '{}'".format(guild_id))
                signup_channel = discord.utils.find(
                    lambda channel: channel.id == channels[guild_id]['signup'], guild.channels)
                if signup_channel is None:
                    raise ValueError("Configuration Error: Sever {} does not have a channel with id '{}'".format(
                        guild.name, channels[guild_id]['signup']))
                self.signup_channels.append(signup_channel)
        except Exception:
            await self.close()
            raise

    async def on_message(self, message):
        if message.author.id == self.user.id or (
                not isinstance(message.channel, discord.DMChannel) and message.channel not in self.signup_channels):
            return
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
                    "Este comando não deve ser utilizado neste canal privado.")
                return

        elif channel in self.signup_channels:
            if command is None:
                if self.cleanup_signup_channels:
                    await message.delete()
                return

            if command.__original_kwargs__.get('dm_only', False):
                if self.cleanup_signup_channels:
                    await message.delete()
                await message.author.send("O comando '%s' deve ser usado neste canal privado." % ctx.invoked_with)
                return

        async with message.channel.typing():
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

        if isinstance(error, commands.errors.CommandInvokeError) and isinstance(error.original, FrompsBotException):
            if error.original.reply_on_private:
                await ctx.author.send(error.original)
            else:
                await ctx.reply(error.original)

        elif isinstance(error, commands.MissingRequiredArgument):
            param_map = {}
            if ctx.cog is not None:
                param_map = getattr(ctx.cog, 'param_map', param_map)
            await ctx.reply("Você deve informar %s. Consulte o comando 'ajuda' para mais informações." % param_map.get(
                error.param.name, error.param.name))

        elif isinstance(error, commands.TooManyArguments):
            await ctx.reply(
                "Você deve fornecer apenas os parâmetros requeridos pelo comando."
                " Consulte o comando 'ajuda' para mais informações."
            )

        elif isinstance(error, commands.errors.ConversionError):
            converter = error.converter
            if isinstance(converter, GameConverter):
                await ctx.reply("O código informado não corresponde a um jogo conhecido.")
            elif isinstance(converter, DatetimeConverter):
                await ctx.reply("A data e hora fornecidos devem estar no formato '%s'." % converter.description_format)
            elif isinstance(converter, TimeConverter):
                await ctx.reply("O tempo fornecido deve estar no formato '%s'." % converter.description_format)
            else:
                await handle_unknown_exception()

        elif isinstance(error, commands.errors.CommandNotFound):
            await ctx.reply("Comando desconhecido.")

        elif isinstance(error, commands.errors.BadBoolArgument):
            await ctx.reply("%s não é um valor reconhecido." % error.argument)

        else:
            await handle_unknown_exception()

    def event(self, coro):
        raise Exception("This decorator is disabled. Use 'listen()' instead")

    def run(self, *args, **kwargs):
        super().run(self.token, *args, **kwargs)
