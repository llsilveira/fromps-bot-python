import discord
from discord.ext import commands
from datetime import datetime

from datatypes import EntryStatus
from helpers import get_discord_name, GameConverter, MonitorChecker
from exceptions import SeedBotException

import logging
logger = logging.getLogger(__name__)


class Weekly(commands.Cog, name="Semanais"):
    def __init__(self, bot, config, database):
        self.bot = bot
        self.config = config
        self.db = database
        self.monitor_checker = MonitorChecker(config)

    @commands.command(
        name='semanais',
        help="Listar as semanais abertas"
    )
    async def weeklies(self, ctx, *args):
        with self.db.Session() as session:
            weeklies = self.db.list_open_weeklies(session)
            weeklies = [w for w in weeklies if w.submission_end > datetime.now()]

            if len(weeklies) == 0:
                raise SeedBotException("Nenhuma semanal aberta no momento.")

            embed = discord.Embed(
                title="Semanais da ZRBR",
            )

            codes = []
            games = []
            times = []

            for w in weeklies:
                codes.append(str.upper(w.game.keys[0]))
                games.append(str(w.game))
                times.append(w.submission_end.strftime("%d/%m/%Y %H:%M"))

            embed.add_field(name="Código", value="\n".join(codes))
            embed.add_field(name="Jogo", value="\n".join(games))
            embed.add_field(name="Enviar até", value="\n".join(times))

            #reply = "Semanais abertas\nCodigo - Jogo\n"
            #for w in weeklies:
            #    reply += "%s - %s (aberta até %s às %s)\n" % (
            #        str.upper(w.game.keys[0]), w.game,
            #        w.submission_end.strftime("%d/%m/%Y"), w.submission_end.strftime("%H:%M")
            #    )
            await ctx.message.reply(embed=embed)



    @commands.command(
        name='seed',
        help="Solicitar seed da semanal"
    )
    async def seed(self, ctx, *args):
        with self.db.Session() as session:
            if len(args) != 1:
                raise SeedBotException("O formato correto deste comando é: %s%s <codigo_do_jogo>" % (ctx.prefix, ctx.invoked_with))

            game = GameConverter.convert(args[0])
            if game is None:
                raise SeedBotException("Jogo desconhecido.")

            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise SeedBotException("A semanal de %s não está aberta." % game)

            if datetime.now() >= weekly.submission_end:
                raise SeedBotException("As submissões para a semanal de %s foram encerradas." % game)

            author = ctx.author
            entry = self.db.get_player_entry(session, weekly, author.id)
            if entry is None:
                registered = self.db.get_registered_entry(session, author.id)
                if registered is not None:
                    game = registered.weekly.game
                    raise SeedBotException(
                        "Você deve registrar o seu tempo ou desistir da semanal de %s antes de participar de outra. " % game
                    )
                self.db.register_player(session, weekly, author.id, get_discord_name(author))
            elif entry.status != EntryStatus.REGISTERED:
                raise SeedBotException(
                    "Você já participou da semanal de %s. Caso tenha concluído a seed mas ainda não enviou o seu VOD, você pode fazê-lo utilizando o comando %svod" % (game, ctx.prefix)
                )

            embed = discord.Embed(
                title="ZRBR Semanal - %s" % game,
                description="""
                SEED: %s
                HASH: %s
                
                PROCEDIMENTOS PARA A SUBMISSÃO:
                1) Jogue a seed acima e, ao terminá-la, faça um print contendo a tela do jogo e o seu timer.
                2) Envie o comando "%stime <tempo_final>" neste chat privado com o seu tempo final e anexe o print acima na mesma mensagem. 
                3) Envie o vídeo para o lugar que se sinta mais confortável e utilize o comando "%svod <link_para_o_vod>" aqui mesmo para submetê-lo.
                A submissão do tempo e do vod se encerram no dia %s às %s.
                """ % (weekly.seed_url, weekly.seed_hash, ctx.prefix, ctx.prefix, weekly.submission_end.strftime("%d/%m/%Y"),
                       weekly.submission_end.strftime("%H:%M")),
                color=0xFF0000
            )
            await ctx.author.send(embed=embed)
            logger.info("The seed for %s was sent to %s", game, get_discord_name(author))

    @commands.command(
        name="time",
        help="*Apenas no privado* Enviar o tempo final da seed jogada"
    )
    async def time(self, ctx, *args):
        with self.db.Session() as session:
            if len(args) != 1:
                raise SeedBotException("O formato correto deste comando é: %s%s H:MM:SS" % (ctx.prefix, ctx.invoked_with))

            try:
                time = datetime.strptime(args[0], "%H:%M:%S").time()
            except Exception:
                raise SeedBotException("O tempo deve estar no formato 'H:MM:SS'")

            author_id = ctx.author.id
            entry = self.db.get_registered_entry(session, author_id)
            if entry is None:
                raise SeedBotException("Você já registrou seu tempo ou não está participando de uma semanal aberta.")

            if datetime.now() >= entry.weekly.submission_end:
                raise SeedBotException("As submissões de tempo para a semanal de %s foram encerradas." % entry.weekly.game)

            if len(ctx.message.attachments) != 1:
                raise SeedBotException(
                    "Você deve enviar o print mostrando a tela final do jogo e o seu timer juntamente com este comando."
                )

            self.db.submit_time(session, entry.weekly, author_id, time, ctx.message.attachments[0].url)
            await ctx.message.reply(
                "Seu tempo de %s na semanal de %s foi registrado! Não esqueça de submeter o seu VOD através do comando "
                "'%svod' até %s às %s." % (
                    time.strftime("%H:%M:%S"),
                    entry.weekly.game,
                    ctx.prefix,
                    entry.weekly.submission_end.strftime("%d/%m/%Y"),
                    entry.weekly.submission_end.strftime("%H:%M")
                )
            )
            logger.info(
                "The time and print for %s was received from %s.", entry.weekly.game, get_discord_name(ctx.author))

    @commands.command(
        name="forfeit",
        help="*Apenas no privado* Desistir da participação na semanal atual"
    )
    async def forfeit(self, ctx, *args):
        with self.db.Session() as session:
            author_id = ctx.author.id
            entry = self.db.get_registered_entry(session, author_id)
            if entry is None:
                raise SeedBotException("Você já registrou seu tempo ou não está participando de uma semanal.")

            if len(args) < 1 or len(args) > 1 or str.lower(args[0]) != "ok":
                raise SeedBotException(
                    "Confirme sua desistência da semanal de %s ação enviando o comando '%sforfeit ok' aqui." % (entry.weekly.game, ctx.prefix)
                )

            self.db.forfeit_player(session, entry.weekly, author_id)
            await ctx.message.reply("Você não está mais participando da semanal de %s." % entry.weekly.game)
            logger.info("%s has forfeited from %s.", get_discord_name(ctx.author), entry.weekly.game)

    @commands.command(
        name="vod",
        help="*Apenas no privado* Enviar o vod da seed jogada"
    )
    async def vod(self, ctx, *args):
        with self.db.Session() as session:
            if len(args) != 2:
                raise SeedBotException("O formato correto deste comando é: %s%s <codigo_do_jogo> <vod_url>" % (ctx.prefix, ctx.invoked_with))

            game = GameConverter.convert(args[0])
            if game is None:
                raise SeedBotException("Jogo desconhecido.")
            vod_url = args[1]

            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise SeedBotException("Não há uma semanal de %s em andamento." % game)

            author_id = ctx.author.id
            entry = self.db.get_player_entry(session, weekly, author_id)
            if entry is None:
                raise SeedBotException("Você ainda não solicitou a seed da semanal de %s." % game)

            if entry.status == EntryStatus.REGISTERED:
                raise SeedBotException("Você deve submeter o seu tempo através do comando '%stime' antes de enviar o seu VOD." % ctx.prefix)
            elif entry.status == EntryStatus.DNF:
                raise SeedBotException("Você não está mais participando desta semanal.")

            self.db.submit_vod(session, weekly, author_id, vod_url)
            await ctx.message.reply("VOD recebido com sucesso! Agradecemos a sua participação!")
            logger.info("The VOD for %s was received from %s.", entry.weekly.game, get_discord_name(ctx.author))

    @commands.command(
        name="entries",
        hidden=True
    )
    async def entries(self, ctx, *args):
        with self.db.Session() as session:
            if not self.monitor_checker.is_monitor(ctx.author):
                raise SeedBotException("Este comando deve ser executado apenas por monitores.")

            if len(args) != 1:
                raise SeedBotException("O formato correto deste comando é: %s%s <codigo_do_jogo>" % (ctx.prefix, ctx.invoked_with))

            game = GameConverter.convert(args[0])
            if game is None:
                raise SeedBotException("Jogo desconhecido.")

            if not self.monitor_checker.is_monitor(ctx.author, game):
                raise SeedBotException("Você não é monitor de %s." % game)

            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise SeedBotException("Não há uma semanal de %s em andamento." % game)

            reply = ""
            for e in weekly.entries:
                reply += "Player: %s\nStatus: %s\n" % (e.discord_name, e.status.name)
                if e.status in [EntryStatus.TIME_SUBMITTED, EntryStatus.DONE]:
                    reply += "Tempo: %s\nPrint: <%s>\n" % (e.finish_time, e.print_url)
                if e.status == EntryStatus.DONE:
                    reply += "VOD: <%s>\n" % e.vod_url
                reply += "\n"
            if len(reply) > 0:
                await ctx.message.reply(reply)
            else:
                await ctx.message.reply("Nenhuma entrada resgistrada.")


    @commands.command(
        name="weeklycreate",
        hidden=True
    )
    async def weeklycreate(self, ctx, *args):
        with self.db.Session() as session:
            if not self.monitor_checker.is_monitor(ctx.author):
                raise SeedBotException("Este comando deve ser executado apenas por monitores.")

            if len(args) != 4:
                raise SeedBotException("O formato correto deste comando é: %s%s <codigo_do_jogo> <seed> <hash> <dd/mm/aaaa-HH:MM>" % (ctx.prefix, ctx.invoked_with))

            game = GameConverter.convert(args[0])
            if game is None:
                raise SeedBotException("Jogo desconhecido.")

            if not self.monitor_checker.is_monitor(ctx.author, game):
                raise SeedBotException("Você não é monitor de %s." % game)

            try:
                submission_end = datetime.strptime(args[3], "%d/%m/%Y-%H:%M")
            except Exception:
                raise SeedBotException("O tempo limite para submissões deve estar no formato 'dd/mm/aaaa-HH:MM'")

            weekly = self.db.get_open_weekly(session, game)
            if weekly is not None:
                raise SeedBotException("Há uma semanal aberta para %s. Feche-a primeiro antes de criar uma nova." % game)

            self.db.create_weekly(session, game, args[1], args[2], submission_end)
            await ctx.message.reply("Semanal de %s criada com sucesso!" % game)
            logger.info("A new weekly for %s was created.", game)


    @commands.command(
        name="weeklyclose",
        hidden=True
    )
    async def weeklyclose(self, ctx, *args):
        with self.db.Session() as session:
            if not self.monitor_checker.is_monitor(ctx.author):
                raise SeedBotException("Este comando deve ser executado apenas por monitores.")

            if len(args) != 1:
                raise SeedBotException("O formato correto deste comando é: %s%s <codigo_do_jogo>" % (ctx.prefix, ctx.invoked_with))

            game = GameConverter.convert(args[0])
            if game is None:
                raise SeedBotException("Jogo desconhecido.")

            if not self.monitor_checker.is_monitor(ctx.author, game):
                raise SeedBotException("Você não é monitor de %s." % game)

            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise SeedBotException("A semanal de %s não está aberta." % game)

            self.db.close_weekly(session, weekly)
            await ctx.message.reply("Semanal de %s fechada com sucesso!" % game)
            logger.info("The weekly for %s was closed.", game)
