from discord.ext import commands
from datetime import datetime

from database import model
from datatypes import Games, EntryStatus, WeeklyStatus
from helpers import get_discord_name, GameConverter, TimeConverter, DatetimeConverter, MonitorChecker, SeedHashHandler
from exceptions import SeedBotException
import embeds

import yaml
import logging
logger = logging.getLogger(__name__)


class Weekly(commands.Cog, name="Semanais"):
    def __init__(self, bot, config, database):
        self.bot = bot
        self.config = config
        self.db = database
        self.monitor_checker = MonitorChecker(config)
        self.hash_handler = SeedHashHandler(self.bot)

        # Load instructions file
        with open(self.config['instructions_file'], 'r') as instructions_file:
            try:
                instructions = yaml.safe_load(instructions_file)
            except Exception as e:
                logger.exception(e)
                raise
        self.instructions = {'ALL': instructions['ALL']}
        self.instructions.update({
            Games[game_name]: instruction for game_name, instruction in instructions.items() if game_name != 'ALL'
        })

    @commands.command(
        name='semanais',
        aliases=['weeklies'],
        help="Listar as semanais abertas."
    )
    async def weeklies(self, ctx):
        with self.db.Session() as session:
            weeklies = self.db.list_open_weeklies(session)
            embed = embeds.list_embed(weeklies)
            await ctx.message.reply(embed=embed)

    @commands.command(
        name='seed',
        aliases=['semente'],
        help='Solicitar a seed da semanal de sua escolha. O código do jogo é informado na lista de semanais abertas.',
        brief='Solicitar a seed da semanal de sua escolha.',
        ignore_extra=False
    )
    async def seed(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo

        with self.db.Session() as session:
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

            embed = embeds.seed_embed(weekly, self.instructions)
            await ctx.author.send(embed=embed)
            logger.info("The seed for %s was sent to %s", game, get_discord_name(author))

    @commands.command(
        name="time",
        aliases=['tempo'],
        help="Enviar o tempo final da seed jogada.\nO tempo deve estar no formato 'H:MM:SS'.\nVocê deve anexar, na mesma mensagem, o print com a tela do jogo e o seu timer.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Enviar o tempo final da seed jogada.",
        ignore_extra=False
    )
    async def time(self, ctx, tempo: TimeConverter("%H:%M:%S", "H:MM:SS")):
        time = tempo

        with self.db.Session() as session:
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
        aliases=['desistir'],
        help="Desistir da participação na semanal atual.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Desistir da participação na semanal atual."
    )
    async def forfeit(self, ctx, *, ok: str = None):
        with self.db.Session() as session:
            author_id = ctx.author.id
            entry = self.db.get_registered_entry(session, author_id)
            if entry is None:
                raise SeedBotException("Você já registrou seu tempo ou não está participando de uma semanal.")

            if ok is None or str.lower(ok) != "ok":
                raise SeedBotException(
                    "Confirme sua desistência da semanal de %s ação enviando o comando '%s%s ok' aqui." % (entry.weekly.game, ctx.prefix, ctx.invoked_with)
                )

            self.db.forfeit_player(session, entry.weekly, author_id)
            await ctx.message.reply("Você não está mais participando da semanal de %s." % entry.weekly.game)
            logger.info("%s has forfeited from %s.", get_discord_name(ctx.author), entry.weekly.game)

    @commands.command(
        name="vod",
        aliases=['video', 'gravacao'],
        help=" Enviar o VOD da seed jogada.\nVocê deve informar o jogo para o qual está enviando do seu VOD e a URL. O código do jogo é informado na lista de semanais abertas.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Enviar o VOD da seed jogada",
        ignore_extra=False
    )
    async def vod(self, ctx, codigo_do_jogo: GameConverter(), url_do_vod: str):
        game = codigo_do_jogo
        vod_url = url_do_vod

        with self.db.Session() as session:
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
        aliases=['entradas', 'inscricoes'],
        hidden=True,
        ignore_extra=False
    )
    async def entries(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo
        self.monitor_checker.check(ctx.author, game)

        with self.db.Session() as session:
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
        aliases=['criarsemanal'],
        help="Criar uma nova semanal.\nVocê não poderá criar uma semanal para um jogo que ainda não foi fechado.\nSe o código de verificação fornecido for uma URL, esta será tratada como uma imagem.\nSe algum parâmetro contiver espaços, ele deverá estar \"entre aspas\".\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Criar uma nova semanal.",
        ignore_extra=False,
        hidden=True,
    )
    async def weeklycreate(
            self,
            ctx,
            codigo_do_jogo: GameConverter,
            url_da_seed,
            codigo_de_verificacao: str,
            limite_para_envios: DatetimeConverter("%d/%m/%Y-%H:%M", "dd/mm/aaaa-HH:MM")
    ):
        game = codigo_do_jogo
        seed_url = url_da_seed
        hash_str = self.hash_handler.get_hash(game, codigo_de_verificacao)
        submission_end = limite_para_envios
        self.monitor_checker.check(ctx.author, game)

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is not None:
                raise SeedBotException("Há uma semanal aberta para %s. Feche-a primeiro antes de criar uma nova." % game)

            self.db.create_weekly(session, game, seed_url, hash_str, submission_end)
            await ctx.message.reply("Semanal de %s criada com sucesso!" % game)
            logger.info("A new weekly for %s was created.", game)

    @commands.command(
        name="weeklytestcreate",
        help="Testa a criação de uma semanal.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Testa a criação de uma semanal.",
        ignore_extra=False,
        hidden=True,
    )
    async def weeklytestcreate(
            self,
            ctx,
            codigo_do_jogo: GameConverter,
            url_da_seed,
            codigo_de_verificacao: str,
            limite_para_envios: DatetimeConverter("%d/%m/%Y-%H:%M", "dd/mm/aaaa-HH:MM")
    ):
        game = codigo_do_jogo
        seed_url = url_da_seed
        hash_str = self.hash_handler.get_hash(game, codigo_de_verificacao)
        submission_end = limite_para_envios
        self.monitor_checker.check(ctx.author, game)

        weekly = model.Weekly(
            game=game,
            status=WeeklyStatus.OPEN,
            seed_url=seed_url,
            seed_hash=hash_str,
            created_at=datetime.now(),
            submission_end=submission_end
        )
        embed = embeds.seed_embed(weekly, self.instructions)
        await ctx.author.send(embed=embed)

    @commands.command(
        name="weeklyclose",
        aliases=['encerrarsemanal'],
        help="Encerra completamente uma semanal.\nExecute este comando apenas quando a semanal estiver completamente concluída, pois não será mais possível listar as entradas após isto.\nAo executar este comando, todos os jogadores que não tiverem concluído completamente sua participação (enviando o tempo e o VOD), receberão o status 'DNF'\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Encerra completamente uma semanal.",
        ignore_extra=False,
        hidden=True,
    )
    async def weeklyclose(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo
        self.monitor_checker.check(ctx.author, game)

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise SeedBotException("A semanal de %s não está aberta." % game)

            self.db.close_weekly(session, weekly)
            await ctx.message.reply("Semanal de %s fechada com sucesso!" % game)
            logger.info("The weekly for %s was closed.", game)
