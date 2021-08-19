from discord import File
from discord.ext import commands
import yaml

from database import model
from datatypes import Games, EntryStatus, WeeklyStatus

from util import get_discord_name, time_to_timedelta, timedelta_to_str
from util.ImageHashGenerator import ImageHashGenerator
from bot.converters import GameConverter, TimeConverter, DatetimeConverter
from bot.exceptions import FrompsBotException

from . import embeds

from datetime import datetime, time
import io
import functools

import logging
logger = logging.getLogger(__name__)


def log(f):
    @functools.wraps(f)
    async def log_wrapper(*args, **kwargs):
        ctx = args[1]
        message = get_discord_name(ctx.author) + " sent: '" + ctx.message.content + "'."
        try:
            result = await f(*args, **kwargs)
        except Exception as e:
            message += " Command raised an error as result: " + type(e).__name__ + "('" + str(e) + "')."
            raise
        else:
            message += " Command returned without errors."
        finally:
            logger.info(message)
        return result
    return log_wrapper


class Weekly(commands.Cog, name="Semanais"):
    def __init__(self, bot, config, database):
        self.bot = bot
        self.db = database
        self.monitors = {Games[key]: monitor for (key, monitor) in config['monitors'].items()}
        self.img_hash_generator = ImageHashGenerator()

        # Load instructions file
        with open(config['instructions_file'], 'r') as instructions_file:
            try:
                instructions = yaml.safe_load(instructions_file)
            except Exception as e:
                logger.exception(e)
                raise
        self.instructions = {'ALL': instructions['ALL']}
        self.instructions.update({
            Games[game_name]: instruction for game_name, instruction in instructions.items() if game_name != 'ALL'
        })

        self.param_map = {
            "codigo_do_jogo": "o código do jogo",
            "tempo": "o tempo",
            "url_do_vod": "a URL do seu VOD",
            "url_da_seed": "a URL da seed",
            "codigo_de_verificacao": "o código de verificação",
            "limite_para_envios": "o limite para envios"
        }

    @commands.command(
        name='semanais',
        aliases=['weeklies'],
        help="Listar as semanais abertas."
    )
    async def weeklies(self, ctx):
        with self.db.Session() as session:
            weeklies = sorted(self.db.list_open_weeklies(session), key=lambda w: w.submission_end)
            embed = embeds.list_embed(weeklies)
            await ctx.message.reply(embed=embed)

    @commands.command(
        name='seed',
        aliases=['semente'],
        help='Solicitar a seed da semanal de sua escolha. O código do jogo é informado na lista de semanais abertas.',
        brief='Solicitar a seed da semanal de sua escolha.',
        ignore_extra=False,
        signup_only=True
    )
    @log
    async def seed(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("A semanal de %s não está aberta." % game)

            if datetime.now() >= weekly.submission_end:
                raise FrompsBotException("As inscrições para a semanal de %s foram encerradas." % game)

            author = ctx.author
            entry = self.db.get_player_entry(session, weekly, author.id)
            if entry is None:
                registered = self.db.get_registered_entry(session, author.id)
                if registered is not None:
                    game = registered.weekly.game
                    raise FrompsBotException(
                        "Você deve registrar o seu tempo ou desistir da semanal de %s antes de participar de outra. " % game
                    )
                self.db.register_player(session, weekly, author.id, get_discord_name(author))
            elif entry.status != EntryStatus.REGISTERED:
                raise FrompsBotException(
                    "Você já participou da semanal de %s. Caso tenha concluído a seed mas ainda não enviou o seu VOD, você pode fazê-lo utilizando o comando %svod" % (game, ctx.prefix)
                )

            embed = embeds.seed_embed(ctx, weekly, self.instructions)
            await ctx.author.send(embed=embed)

    @commands.command(
        name="time",
        aliases=['tempo'],
        help="Enviar o tempo final da seed jogada.\nO tempo deve estar no formato 'H:MM:SS'.\nVocê deve anexar, na mesma mensagem, o print com a tela do jogo e o seu timer.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Enviar o tempo final da seed jogada.",
        ignore_extra=False,
        dm_only=True
    )
    @log
    async def time(self, ctx, tempo: TimeConverter()):
        finish_time = tempo

        with self.db.Session() as session:
            author_id = ctx.author.id
            entry = self.db.get_registered_entry(session, author_id)
            if entry is None:
                raise FrompsBotException("Você já registrou seu tempo ou não está participando de uma semanal aberta.")

            # Submissions of time are not limited for now
            # if datetime.now() >= entry.weekly.submission_end:
            #    raise FrompsBotException("As submissões de tempo para a semanal de %s foram encerradas." % entry.weekly.game)

            if len(ctx.message.attachments) != 1:
                raise FrompsBotException(
                    "Você deve enviar o print mostrando a tela final do jogo e o seu timer juntamente com este comando."
                )

            self.db.submit_time(session, entry, finish_time, ctx.message.attachments[0].url)
            await ctx.message.reply(
                "Seu tempo de %s na semanal de %s foi registrado! "
                "Não esqueça de enviar o seu vídeo através do comando %svod." % (
                    finish_time.strftime("%H:%M:%S"),
                    entry.weekly.game,
                    ctx.prefix,
                )
            )

    @commands.command(
        name="forfeit",
        aliases=['desistir'],
        help="Desistir da participação na semanal atual.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Desistir da participação na semanal atual.",
        dm_only=True
    )
    @log
    async def forfeit(self, ctx, *, ok: str = None):
        with self.db.Session() as session:
            author_id = ctx.author.id
            entry = self.db.get_registered_entry(session, author_id)
            if entry is None:
                raise FrompsBotException("Você já registrou seu tempo ou não está participando de uma semanal.")

            if ok is None or str.lower(ok) != "ok":
                raise FrompsBotException(
                    "Confirme sua desistência da semanal de %s enviando o comando '%s%s ok' neste chat privado." % (entry.weekly.game, ctx.prefix, ctx.invoked_with)
                )

            self.db.forfeit_player(session, entry.weekly, author_id)
            await ctx.message.reply("Você não está mais participando da semanal de %s." % entry.weekly.game)

    @commands.command(
        name="vod",
        aliases=['video', 'gravacao'],
        help=" Enviar o VOD da seed jogada.\nVocê deve informar o jogo para o qual está enviando do seu VOD e a URL. O código do jogo é informado na lista de semanais abertas.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Enviar o VOD da seed jogada",
        ignore_extra=False,
        dm_only=True
    )
    @log
    async def vod(self, ctx, codigo_do_jogo: GameConverter(), url_do_vod: str):
        game = codigo_do_jogo
        vod_url = url_do_vod

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("Não há uma semanal de %s em andamento." % game)

            # Submissions of VOD are not limited for now
            # if datetime.now() >= weekly.submission_end:
            #    raise FrompsBotException("Os envios para a semanal de %s foram encerradas." % weekly.game)

            author_id = ctx.author.id
            entry = self.db.get_player_entry(session, weekly, author_id)
            if entry is None:
                raise FrompsBotException("Você ainda não solicitou a seed da semanal de %s." % game)

            if entry.status == EntryStatus.REGISTERED:
                raise FrompsBotException("Você deve submeter o seu tempo através do comando '%stime' antes de enviar o seu VOD." % ctx.prefix)
            elif entry.status == EntryStatus.DONE:
                raise FrompsBotException("Você já enviou o seu VOD para a semanal de %s." % game)
            elif entry.status == EntryStatus.DNF:
                raise FrompsBotException("Você não está mais participando desta semanal.")

            self.db.submit_vod(session, entry, vod_url)
            await ctx.message.reply("VOD recebido com sucesso! Agradecemos a sua participação!")

    @commands.command(
        name="comment",
        aliases=['comentario'],
        help="Enviar um comentário de até 250 caracteres sobre a participação na semanal.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Enviar um comentário de até 250 caracteres sobre a participação na semanal.",
        dm_only=True
    )
    async def comment(self, ctx, codigo_do_jogo: GameConverter(), *, comentario: str = None):
        game = codigo_do_jogo
        comment = comentario

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("Não há uma semanal de %s em andamento." % game)

            author_id = ctx.author.id
            entry = self.db.get_player_entry(session, weekly, author_id)
            if entry is None:
                raise FrompsBotException("Você ainda não solicitou a seed da semanal de %s." % game)

            if comment is not None and len(comment) > 250:
                raise FrompsBotException("Seu comentário deve ter no máximo 250 caracteres.")

            self.db.submit_comment(session, entry, comment)
            if comment is None:
                await ctx.message.reply("Comentário removido com sucesso!")
            else:
                await ctx.message.reply("Comentário recebido com sucesso!")

    @commands.command(
        name="entries",
        aliases=['entradas', 'inscricoes', 'e'],
        hidden=True,
        ignore_extra=False,
        dm_only=True
    )
    @log
    async def entries(self, ctx, codigo_do_jogo: GameConverter(), verbose: str = ""):
        game = codigo_do_jogo
        verbose = str.lower(verbose) in ['t', 'true', 'y', 'yes', 's', 'sim', '1', 'on', 'v', '-v', 'verbose', '--verbose']
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("Não há uma semanal de %s em andamento." % game)

            entries = sorted(weekly.entries, key=lambda e: e.finish_time if e.finish_time is not None else time(23, 59))

            if len(entries) > 0:
                reply = ""
                for e in entries:

                    user = self.bot.get_user(e.discord_id)
                    nicknames = []
                    for guild in self.bot.guilds:
                        member = guild.get_member(user.id)
                        if member is not None:
                            name = member.display_name
                            if user.name != name and name not in nicknames:
                                nicknames.append(name)

                    name = get_discord_name(user)
                    if len(nicknames) > 0:
                        name += " (Aka: {})".format(", ".join(nicknames))

                    reply_entry = "Player: %s\nStatus: %s\n" % (name, e.status.name)
                    if e.status in [EntryStatus.TIME_SUBMITTED, EntryStatus.DONE]:
                        finish_time = str(e.finish_time)
                        if not verbose:
                            finish_time = "||" + finish_time + "||"
                        reply_entry += "Tempo: %s\nPrint: <%s>\n" % (finish_time, e.print_url)
                    if e.status == EntryStatus.DONE:
                        reply_entry += "VOD: <%s>\n" % e.vod_url
                    if e.comment is not None:
                        comment = e.comment if verbose else "||" + e.comment + "||"
                        reply_entry += "Comentário: %s\n" % comment

                    if verbose:
                        formatstr = "%d/%m/%Y %H:%M"
                        reply_entry += "Registro: %s\n" % e.registered_at.strftime(formatstr)
                        if e.status in [EntryStatus.TIME_SUBMITTED, EntryStatus.DONE]:
                            reply_entry += "Envio do tempo: %s (%s)\n" % (
                                e.time_submitted_at.strftime(formatstr),
                                timedelta_to_str(e.time_submitted_at - e.registered_at - time_to_timedelta(e.finish_time)))
                            if e.status is EntryStatus.DONE:
                                reply_entry += "Envio do VOD: %s\n" % e.vod_submitted_at.strftime(formatstr)

                    reply_entry += "\n"

                    if len(reply) + len(reply_entry) <= 1800:
                        reply += reply_entry
                    else:
                        await ctx.message.reply(reply)
                        reply = reply_entry

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
        dm_only=True
    )
    @log
    async def weeklycreate(
            self,
            ctx,
            codigo_do_jogo: GameConverter(),
            url_da_seed,
            codigo_de_verificacao: str,
            limite_para_envios: DatetimeConverter()
    ):
        game = codigo_do_jogo
        seed_url = url_da_seed
        hash_str = codigo_de_verificacao
        submission_end = limite_para_envios
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is not None:
                raise FrompsBotException("Há uma semanal aberta para %s. Feche-a primeiro antes de criar uma nova." % game)

            if game in [Games.ALTTPR, Games.OOTR]:
                hash_str = await self.genhash(ctx, game, hash_str)

            self.db.create_weekly(session, game, seed_url, hash_str, submission_end)
            await ctx.message.reply("Semanal de %s criada com sucesso!" % game)

    @commands.command(
        name="weeklytest",
        aliases=['testarsemanal'],
        help="Testa a criação de uma semanal.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Testa a criação de uma semanal.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    async def weeklytest(
            self,
            ctx,
            codigo_do_jogo: GameConverter(),
            url_da_seed,
            codigo_de_verificacao: str,
            limite_para_envios: DatetimeConverter()
    ):
        game = codigo_do_jogo
        seed_url = url_da_seed
        hash_str = codigo_de_verificacao
        submission_end = limite_para_envios
        self._check_monitor(ctx.author, game)

        if game in [Games.ALTTPR, Games.OOTR]:
            hash_str = await self.genhash(ctx, game, hash_str)

        weekly = model.Weekly(
            game=game,
            status=WeeklyStatus.OPEN,
            seed_url=seed_url,
            seed_hash=hash_str,
            created_at=datetime.now(),
            submission_end=submission_end
        )
        embed = embeds.seed_embed(ctx, weekly, self.instructions)
        await ctx.author.send(embed=embed)

    @commands.command(
        name="weeklyclose",
        aliases=['encerrarsemanal'],
        help="Encerra completamente uma semanal.\nExecute este comando apenas quando a semanal estiver completamente concluída, pois não será mais possível listar as entradas após isto.\nAo executar este comando, todos os jogadores que não tiverem concluído completamente sua participação (enviando o tempo e o VOD), receberão o status 'DNF'\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Encerra completamente uma semanal.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    @log
    async def weeklyclose(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("A semanal de %s não está aberta." % game)

            self.db.close_weekly(session, weekly)
            await ctx.message.reply("Semanal de %s fechada com sucesso!" % game)

    @commands.command(
        name="weeklyreopen",
        aliases=['reabrirsemanal'],
        help="Reabre a última semanal fechada.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Reabre a última semanal fechada.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    @log
    async def weeklyreopen(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is not None:
                raise FrompsBotException("A semanal de %s não está fechada." % game)
            weekly = self.db.get_last_closed_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("Não há uma semanal de %s fechada." % game)
            self.db.reopen_weekly(session, weekly)
            await ctx.message.reply("Semanal de %s reaberta com sucesso!" % game)

    @commands.command(
        name="weeklyupdate",
        aliases=['alterarsemanal'],
        help="Alterar uma semanal.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Alterar uma semanal.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    @log
    async def weeklyupdate(
            self,
            ctx,
            codigo_do_jogo: GameConverter(),
            url_da_seed,
            codigo_de_verificacao: str,
            limite_para_envios: DatetimeConverter()
    ):
        game = codigo_do_jogo
        seed_url = url_da_seed
        hash_str = codigo_de_verificacao
        submission_end = limite_para_envios
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("Não há uma semanal aberta para %s." % game)

            if len(weekly.entries) > 0 and weekly.seed_url != seed_url:
                raise FrompsBotException("Existem entradas registradas para esta semanal, portanto não é possível alterar a URL da seed.")

            if game in [Games.ALTTPR, Games.OOTR]:
                hash_str = await self.genhash(ctx, game, hash_str)

            self.db.update_weekly(session, weekly, seed_url, hash_str, submission_end)
            await ctx.message.reply("Semanal de %s atualizada com sucesso!" % game)

    @commands.command(
        name="entryupdate",
        aliases=['alterarentrada'],
        help="Altera uma entrada da semanal.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Altera uma entrada da semanal.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    @log
    async def entryupdate(
            self,
            ctx,
            codigo_do_jogo: GameConverter(),
            jogador: str,
            parametro: str,
            valor: str
    ):
        game = codigo_do_jogo
        player = jogador
        parameter = str.lower(parametro)
        value = valor
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("Não há uma semanal de %s em andamento." % game)

            entry = self.db.get_player_entry_by_name(session, weekly, jogador)
            if entry is None:
                raise FrompsBotException("%s não está participando da semanal de %s." % (player, game))

            if entry.status == EntryStatus.DNF:
                raise FrompsBotException("%s não está mais participando da semanal de %s." % (player, game))

            if parameter == 'time':
                converter = TimeConverter()
                try:
                    finish_time = await converter.convert(ctx, value)
                except:
                    raise FrompsBotException("O tempo fornecido deve estar no formato '%s'." % converter.description_format)

                if entry.status not in [EntryStatus.TIME_SUBMITTED, EntryStatus.DONE]:
                    raise FrompsBotException("%s ainda não enviou seu tempo para a semanal de %s." % (player, game))

                self.db.update_time(session, entry, finish_time)

            elif parameter == 'vod':
                if entry.status is not EntryStatus.DONE:
                    raise FrompsBotException("%s ainda não enviou seu VOD para a semanal de %s." % (player, game))

                self.db.update_vod(session, entry, value)

            else:
                raise FrompsBotException("Parâmetro desconhecido: %s." % parametro)

            await ctx.message.reply("Entrada de %s para a semanal de %s alterada com sucesso!" % (player, game))

    async def genhash(self, ctx, game, hash_str):
        try:
            img_bytes = self.img_hash_generator.generate(game, hash_str)
        except ValueError as e:
            raise FrompsBotException(str(e))

        with io.BytesIO(img_bytes) as img:
            message = await ctx.reply("", file=File(img, "hash.png"))
            if len(message.attachments) != 1:
                raise FrompsBotException("Erro ao enviar a imagem pelo Discord.")
            return message.attachments[0].url

    def _check_monitor(self, user, game=None):
        user_name = get_discord_name(user)

        if game is not None:
            if game in self.monitors.keys() and user_name in self.monitors[game]:
                return
            raise FrompsBotException("Você não é monitor de %s." % game)

        for monitor_list in self.monitors.values():
            if user_name in monitor_list:
                return
        raise FrompsBotException("Este comando deve ser executado apenas por monitores.")
