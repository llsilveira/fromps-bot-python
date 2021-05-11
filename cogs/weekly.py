import discord
from discord.ext import commands
from datetime import datetime

from helpers import get_discord_name, DatetimeConverter, TimeConverter, GameConverter
from exceptions import SeedBotException


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
    async def create(self, ctx, game: GameConverter, seed_url: str, seed_hash: str,
                     submission_end: DatetimeConverter("%d/%m/%Y-%H:%M:%S")):
        print(game, seed_url, seed_hash, submission_end)

    @commands.command(name='seed', help="Solicitar seed da semanal")
    async def seed(self, ctx, game: GameConverter):
        message = ctx.message

        if message.channel.id != self.config['channels']['signup']:
            raise SeedBotException(
                "Este comando deve ser enviado no canal #%s." %
                self.bot.get_channel(self.config['channels']['signup']).name
            )

        weekly = self.db.get_weekly(game)
        if weekly is None:
            raise SeedBotException("A semanal de %s não está aberta." % game)

        if datetime.now() >= weekly.submission_end:
            raise SeedBotException("As submissões para a semanal de %s foram encerradas." % game)

        author = ctx.author
        entry = self.db.get_player_entry(weekly, author.id)
        if entry is None:
            self.db.register(weekly, author.id, get_discord_name(author))
        embed = discord.Embed(
            title="ZRBR Semanal - %s" % game,
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
    async def time(self, ctx, game: GameConverter, time: TimeConverter("%H:%M:%S")):
        message = ctx.message

        if not isinstance(message.channel, discord.DMChannel):
            await message.delete()
            raise SeedBotException("Este comando deve ser utilizado apenas no privado.")

        weekly = self.db.get_weekly(game)
        if weekly is None:
            raise SeedBotException("Não há uma semanal de %s em andamento." % game)

        if datetime.now() >= weekly.submission_end:
            raise SeedBotException("As submissões de tempo para a semanal de %s foram encerradas." % game)

        author_id = ctx.author.id
        entry = self.db.get_player_entry(weekly, author_id)
        if entry is None:
            raise SeedBotException("Você ainda não solicitou a seed da semanal de %s." % game)

        if len(message.attachments) != 1:
            raise SeedBotException(
                "Você deve enviar o print mostrando a tela final do jogo e o seu timer juntamente com este comando."
            )

        self.db.submit_time(weekly, author_id, time, message.attachments[0].url)

        await message.reply("Tempo recebido com sucesso!")

    @commands.command(name="vod", help="**No privado** Enviar o vod da seed jogada")
    async def vod(self, ctx, game: GameConverter, vod_url: str):
        message = ctx.message

        if not isinstance(message.channel, discord.DMChannel):
            await message.delete()
            raise SeedBotException("Este comando deve ser utilizado apenas no privado.")

        weekly = self.db.get_weekly(game)
        if weekly is None:
            raise SeedBotException("Não há uma semanal de %s em andamento." % game)

        author_id = ctx.author.id
        entry = self.db.get_player_entry(weekly, author_id)
        if entry is None:
            raise SeedBotException("Você ainda não solicitou a seed da semanal de %s." % game)

        if entry.finish_time is None:
            raise SeedBotException("Você deve enviar o seu tempo através do comando '!time' antes de enviar o seu VOD.")

        self.db.submit_vod(weekly, author_id, vod_url)

        await message.reply("VOD recebido com sucesso!")

    @commands.command(name="entries", checks=[privileged], hidden=True)
    async def entries(self, ctx, game: GameConverter):
        message = ctx.message

        if not isinstance(message.channel, discord.DMChannel):
            await message.delete()
            raise SeedBotException("Este comando deve ser utilizado apenas no privado.")

        weekly = self.db.get_weekly(game)
        if weekly is None:
            raise SeedBotException("Não há uma semanal de %s em andamento." % game)

        reply = ""
        for e in weekly.entries:
            reply += "Player: %s\nTempo: %s\nPrint: <%s>\nVOD: <%s>\n\n" % (
                e.discord_name, e.finish_time, e.print_url, e.vod_url
            )
        if len(reply) > 0:
            await ctx.message.reply(reply)
        else:
            await ctx.message.reply("Nenhuma entrada resgistrada.")
