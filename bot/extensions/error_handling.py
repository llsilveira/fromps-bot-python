from discord.ext import commands
from bot.helpers import get_discord_name
from bot.exceptions import SeedBotException
from bot.helpers import TimeConverter, DatetimeConverter, GameConverter

import logging
logger = logging.getLogger(__name__)


def setup(bot):
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

    @bot.event
    async def on_command_error(ctx, error):
        async def handle_unknown_exception():
            logger.exception(error)

            await ctx.reply("Ocorreu um erro inesperado.")
            if hasattr(bot, 'ping_on_error'):
                user = await bot.fetch_user(bot.ping_on_error)
                await ping_on_error(user, ctx, error)

        if isinstance(error, commands.errors.CommandInvokeError) and isinstance(error.original, SeedBotException):
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
