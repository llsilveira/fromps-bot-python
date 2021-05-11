import discord
from discord.ext import commands
from datetime import datetime

from datatypes import Games
from helpers import get_discord_name, feedback_reactions, DatetimeConveter, TimeConverter


async def privileged(ctx):
    self = ctx.cog
    roles = self.config['roles']
    return ctx.author.id in roles['admin']


class Weekly(commands.Cog):
    def __init__(self, bot, config, database):
        self.bot = bot
        self.config = config
        self.db = database

    @commands.command(checks=[privileged], enabled=False)
    async def create(self, ctx, game: Games, seed_url: str, seed_hash: str,
                     submission_end: DatetimeConveter("%d/%m/%Y-%H:%M:%S")):
        print(game, seed_url, seed_hash, submission_end)

    @commands.command(name='seed', help="Solicitar seed da semanal")
    @feedback_reactions()
    async def seed(self, ctx):
        message = ctx.message

        if message.channel.id != self.config['channels']['signup']:
            # TODO mudar canal hardcoded
            await message.reply("Este comando deve ser enviado no canal #%s." % self.bot.get_channel(
                self.config['channels']['signup']).name)
            return False

        weekly = self.db.get_weekly(Games.MMR)
        if weekly is None:
            await message.reply("A semanal de %s não está aberta." % Games.MMR.value)
            return False

        if datetime.now() >= weekly.submission_end:
            await message.reply("As submissões para a semanal de %s foram encerradas." % Games.MMR.value)
            return False

        author = ctx.author
        entry = self.db.get_player_entry(weekly, author.id)
        if entry is None:
            self.db.register(weekly, author.id, get_discord_name(author))
        embed = discord.Embed(
            title="ZRBR Semanal - %s" % Games.MMR.value,
            description="""
            SEED: %s
            HASH: %s
            
            PROCEDIMENTOS PARA A SUBMISSÃO:
            1) Jogue a seed acima e, ao terminá-la, faça um print contendo a tela final do jogo e o seu timer.
            2) Envie o comando "!time <tempo_final>" neste chat privado com o seu tempo final e anexe o print acima na mesma mensagem. 
            3) Envie o vídeo para o lugar que se sinta mais confortável e utilize o comando "!vod <link_para_o_vod>" aqui mesmo para submetê-lo.
            A submissão do tempo e do vod se encerram em %s às %s.
            """ % (weekly.seed_url, weekly.seed_hash, weekly.submission_end.strftime("%d/%m/%Y"),
                   weekly.submission_end.strftime("%H:%M")),
            color=0xFF0000
        )
        await ctx.author.send(embed=embed)

    @commands.command(name="time", help="**No privado** Enviar o tempo final da seed jogada")
    @feedback_reactions()
    async def time(self, ctx, time: TimeConverter("%H:%M:%S")):
        message = ctx.message

        if not isinstance(message.channel, discord.DMChannel):
            await message.reply("Por favor, envie este comando no privado.")
            await message.delete()
            return False

        weekly = self.db.get_weekly(Games.MMR)
        if weekly is None:
            await message.reply("Não há uma semanal de %s em andamento." % Games.MMR.value)
            return False

        if datetime.now() >= weekly.submission_end:
            await message.reply("As submissões de tempo para a semanal de %s foram encerradas." % Games.MMR.value)
            return False

        author_id = ctx.author.id
        entry = self.db.get_player_entry(weekly, author_id)
        if entry is None:
            await message.reply("Você ainda não solicitou a seed da semanal de %s." % Games.MMR.value)
            return False

        if len(message.attachments) != 1:
            await message.reply(
                "Você deve enviar o print mostrando a tela final do jogo e o seu timer juntamente com este comando.")
            return False

        self.db.submit_time(weekly, author_id, time, message.attachments[0].url)

        await message.reply("Tempo recebido com sucesso!")

    @time.error
    async def time_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.message.reply("Você deve informar o tempo que você levou para completar a seed.")
        elif isinstance(error, commands.ConversionError):
            await ctx.message.reply("O tempo deve estar no formato 'HH:MM:SS'.")
        else:
            await ctx.message.reply("Ocorreu um erro inesperado.")
            await self.bot.on_command_error(ctx, error)

    @commands.command(name="vod", help="**No privado** Enviar o vod da seed jogada")
    @feedback_reactions()
    async def vod(self, ctx, vod_url: str):
        message = ctx.message

        if not isinstance(message.channel, discord.DMChannel):
            await message.reply("Por favor, envie este comando no privado.")
            await message.delete()
            return False

        weekly = self.db.get_weekly(Games.MMR)
        if weekly is None:
            await message.reply("Não há uma semanal de %s em andamento." % Games.MMR.value)
            return False

        author_id = ctx.author.id
        entry = self.db.get_player_entry(weekly, author_id)
        if entry is None:
            await message.reply("Você ainda não solicitou a seed da semanal de %s." % Games.MMR.value)
            return False

        if entry.finish_time is None:
            await message.reply("Você deve enviar o seu tempo através do comando '!time' antes de enviar o seu VOD.")
            return False

        self.db.submit_vod(weekly, author_id, vod_url)

        await message.reply("VOD recebido com sucesso!")

    @vod.error
    async def vod_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.message.reply("Informe o link do VOD.")
        else:
            await ctx.message.reply("Ocorreu um erro inesperado.")
            await self.bot.on_command_error(ctx, error)

    @commands.command(name="entries", checks=[privileged], hidden=True)
    @feedback_reactions()
    async def entries(self, ctx):
        message = ctx.message

        if not isinstance(message.channel, discord.DMChannel):
            await message.reply("Por favor, utilize este comando apenas no privado.")
            await message.delete()
            return False

        weekly = self.db.get_weekly(Games.MMR)
        if weekly is None:
            await message.reply("Não há uma semanal de %s em andamento." % Games.MMR.value)
            return False

        reply = ""
        for e in weekly.entries:
            reply += "Player: %s\nTempo: %s\nPrint: <%s>\nVOD: <%s>\n\n" % (
                e.discord_name, e.finish_time, e.print_url, e.vod_url
            )
        if len(reply) > 0:
            await ctx.message.reply(reply)
        else:
            await ctx.message.reply("Nenhuma entrada resgistrada.")
