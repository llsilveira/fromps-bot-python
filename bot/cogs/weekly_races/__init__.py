from discord import File
from discord.ext import commands
import yaml

from database import model
from datatypes import Games, EntryStatus, WeeklyStatus, PlayerStatus

from util import get_discord_name, time_to_timedelta, timedelta_to_str
from util.ImageHashGenerator import ImageHashGenerator
from bot.converters import GameConverter, TimeConverter, DatetimeConverter, DateConverter
from bot.exceptions import FrompsBotException

from . import embeds
from .leaderboard import update_weekly, update_leaderboard

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
    def __init__(self, bot, database, *, admins, monitors, instructions_file):
        self.bot = bot
        self.db = database
        self.monitors = {Games[key]: monitor for (key, monitor) in monitors.items()}
        self.admins = admins
        self.img_hash_generator = ImageHashGenerator()

        # Load instructions file
        with open(instructions_file, 'r') as instructions_file:
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
            "codigo_do_jogo": "o c??digo do jogo",
            "tempo": "o tempo",
            "url_do_vod": "a URL do seu VOD",
            "url_da_seed": "a URL da seed",
            "codigo_de_verificacao": "o c??digo de verifica????o",
            "limite_para_envios": "o limite para envios",
            "id_do_jogador": "o ID do jogador",
            "nome": "o nome",
            "unban": "op????o para desbanir",
            "url_dos_resultados": "URL dos resultados da leaderboard"
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
        name='setname',
        help="Altera o nome de um jogador.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Altera o nome de um jogador.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    @log
    async def setname(self, ctx, id_do_jogador: int, nome: str):
        new_name = nome
        discord_id = id_do_jogador
        self._check_admin(ctx.author)

        with self.db.Session() as session:
            player = self.db.get_player(session, discord_id)
            if player is None:
                raise FrompsBotException("Jogador n??o encontrado.")
            player.name = new_name
            session.commit()
            await ctx.message.reply("Nome do jogador '%d' alterado com sucesso." % discord_id)

    @commands.command(
        name='ban',
        help="Banir ou remover banimento de um jogador.\nPara banir um jogador informe apenas o id do jogador. Para"
             " remover um banimento, informe o id do jogador juntamente com a palavra 'remove'."
             "\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Banir um jogador.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    @log
    async def ban(self, ctx, id_do_jogador: int, remover_ban: str = ""):
        discord_id = id_do_jogador
        unban = str.lower(remover_ban) == "remover"
        self._check_admin(ctx.author)

        with self.db.Session() as session:
            player = self.db.get_player(session, discord_id)
            if player is None:
                raise FrompsBotException("Jogador n??o encontrado.")
            if unban:
                if player.status == PlayerStatus.BANNED:
                    player.status = PlayerStatus.ACTIVE
                    session.commit()
                    await ctx.message.reply("Banimento do(a) jogador(a) '%s' removido com sucesso!" % player.name)
                else:
                    await ctx.message.reply("O(a) jogador(a) '%s' n??o est?? banido(a)." % player.name)
            else:
                if player.status != PlayerStatus.BANNED:
                    player.status = PlayerStatus.BANNED
                    session.commit()
                    await ctx.message.reply("O jogador(a) '%s' foi banido(a)!" % player.name)
                else:
                    await ctx.message.reply("O(a) jogador(a) '%s' j?? est?? banido(a)." % player.name)

    @commands.command(
        name='seed',
        aliases=['semente'],
        help='Solicitar a seed da semanal de sua escolha. O c??digo do jogo ?? informado na lista de semanais abertas.',
        brief='Solicitar a seed da semanal de sua escolha.',
        ignore_extra=False
    )
    @log
    async def seed(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("A semanal de %s n??o est?? aberta." % game)

            if datetime.now() >= weekly.submission_end:
                raise FrompsBotException("As inscri????es para a semanal de %s foram encerradas." % game)

            player = self.db.get_or_create_player(session, ctx.author)
            if player.status != PlayerStatus.ACTIVE:
                raise FrompsBotException(
                    "Seu perfil cont??m restri????es. Para saber mais, contate um moderador.", reply_on_private=True
                )

            entry = self.db.get_player_entry(session, weekly.id, player.discord_id)
            commit = False
            if entry is None:
                registered = self.db.get_registered_entry(session, player)
                if registered is not None:
                    game = registered.weekly.game
                    raise FrompsBotException(
                        "Voc?? deve registrar o seu tempo ou desistir da semanal de %s"
                        " antes de participar de outra. " % game
                    )
                self.db.register_player(session, weekly, player)
                commit = True

            elif entry.status != EntryStatus.REGISTERED:
                raise FrompsBotException(
                    "Voc?? j?? participou da semanal de %s. Caso tenha conclu??do a seed mas ainda n??o enviou o seu VOD,"
                    " voc?? pode faz??-lo utilizando o comando %svod" % (game, ctx.prefix)
                )

            embed = embeds.seed_embed(ctx, weekly, self.instructions)
            await ctx.author.send(embed=embed)
            if commit:
                session.commit()

    @commands.command(
        name="time",
        aliases=['tempo'],
        help="Enviar o tempo final da seed jogada.\nO tempo deve estar no formato 'H:MM:SS'."
             "\nVoc?? deve anexar, na mesma mensagem, o print com a tela do jogo e o seu timer."
             "\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Enviar o tempo final da seed jogada.",
        ignore_extra=False,
        dm_only=True
    )
    @log
    async def time(self, ctx, tempo: TimeConverter()):
        finish_time = tempo

        with self.db.Session() as session:
            player = self.db.get_player(session, ctx.author.id)
            if player is not None:
                entry = self.db.get_registered_entry(session, player)
            if player is None or entry is None:
                raise FrompsBotException("Voc?? j?? registrou seu tempo ou n??o est?? participando de uma semanal aberta.")

            if len(ctx.message.attachments) != 1:
                raise FrompsBotException(
                    "Voc?? deve enviar o print mostrando a tela final do jogo e o seu timer juntamente com este comando."
                )

            self.db.submit_time(session, entry, finish_time, ctx.message.attachments[0].url)
            session.commit()

            await ctx.message.reply(
                "Seu tempo de %s na semanal de %s foi registrado! "
                "N??o esque??a de enviar o seu v??deo atrav??s do comando %svod." % (
                    finish_time.strftime("%H:%M:%S"),
                    entry.weekly.game,
                    ctx.prefix,
                )
            )

    @commands.command(
        name="forfeit",
        aliases=['desistir'],
        help="Desistir da participa????o na semanal atual.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Desistir da participa????o na semanal atual.",
        dm_only=True
    )
    @log
    async def forfeit(self, ctx, *, ok: str = None):
        with self.db.Session() as session:
            player = self.db.get_player(session, ctx.author.id)
            if player is not None:
                entry = self.db.get_registered_entry(session, player)
            if player is None or entry is None:
                raise FrompsBotException("Voc?? j?? registrou seu tempo ou n??o est?? participando de uma semanal.")

            if ok is None or str.lower(ok) != "ok":
                raise FrompsBotException(
                    "Confirme sua desist??ncia da semanal de %s enviando o comando '%s%s ok' neste chat privado." %
                    (entry.weekly.game, ctx.prefix, ctx.invoked_with)
                )

            self.db.forfeit(session, entry)
            session.commit()

            await ctx.message.reply("Voc?? n??o est?? mais participando da semanal de %s." % entry.weekly.game)

    @commands.command(
        name="vod",
        aliases=['video', 'gravacao'],
        help="Enviar o VOD da seed jogada.\nVoc?? deve informar o jogo para o qual est?? enviando do seu VOD e a URL."
             " O c??digo do jogo ?? informado na lista de semanais abertas."
             "\nEste comando deve ser utilizado APENAS NO PRIVADO.",
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
                raise FrompsBotException("N??o h?? uma semanal de %s em andamento." % game)

            player = self.db.get_player(session, ctx.author.id)
            if player is not None:
                entry = self.db.get_player_entry(session, weekly.id, player.discord_id)
            if player is None or entry is None:
                raise FrompsBotException("Voc?? ainda n??o solicitou a seed da semanal de %s." % game)

            if entry.status == EntryStatus.REGISTERED:
                raise FrompsBotException(
                    "Voc?? deve submeter o seu tempo atrav??s do comando '%stime' antes de enviar o seu VOD." % ctx.prefix
                )
            elif entry.status == EntryStatus.DONE:
                raise FrompsBotException("Voc?? j?? enviou o seu VOD para a semanal de %s." % game)
            elif entry.status == EntryStatus.DNF:
                raise FrompsBotException("Voc?? n??o est?? mais participando desta semanal.")

            self.db.submit_vod(session, entry, vod_url)
            session.commit()

            await ctx.message.reply("VOD recebido com sucesso! Agradecemos a sua participa????o!")

    @commands.command(
        name="comment",
        aliases=['comentario'],
        help="Enviar um coment??rio de at?? 250 caracteres sobre a participa????o na semanal."
             "\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Enviar um coment??rio de at?? 250 caracteres sobre a participa????o na semanal.",
        dm_only=True
    )
    async def comment(self, ctx, codigo_do_jogo: GameConverter(), *, comentario: str = None):
        game = codigo_do_jogo
        comment = comentario

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("N??o h?? uma semanal de %s em andamento." % game)

            player = self.db.get_player(session, ctx.author.id)
            if player is not None:
                entry = self.db.get_player_entry(session, weekly.id, player.discord_id)
            if player is None or entry is None:
                raise FrompsBotException("Voc?? ainda n??o solicitou a seed da semanal de %s." % game)

            if comment is not None and len(comment) > 250:
                raise FrompsBotException("Seu coment??rio deve ter no m??ximo 250 caracteres.")

            self.db.submit_comment(session, entry, comment)
            session.commit()

            if comment is None:
                await ctx.message.reply("Coment??rio removido com sucesso!")
            else:
                await ctx.message.reply("Coment??rio recebido com sucesso!")

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
        verbose = str.lower(verbose) in [
            't', 'true', 'y', 'yes', 's', 'sim', '1', 'on', 'v', '-v', 'verbose', '--verbose'
        ]
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("N??o h?? uma semanal de %s em andamento." % game)

            entries = sorted(weekly.entries, key=lambda e: e.finish_time if e.finish_time is not None else time(23, 59))

            if len(entries) > 0:
                reply = ""
                for e in entries:
                    player = e.player
                    user = self.bot.get_user(player.discord_id)
                    if user is None:
                        try:
                            user = await self.bot.fetch_user(player.discord_id)
                        except Exception:
                            pass
                    nicknames = []
                    for guild in self.bot.guilds:
                        member = guild.get_member(player.discord_id)
                        if member is not None:
                            name = member.display_name
                            if player.name != name and name not in nicknames:
                                nicknames.append(name)

                    name = player.name
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
                        reply_entry += "Coment??rio: %s\n" % comment

                    if verbose:
                        formatstr = "%d/%m/%Y %H:%M"
                        reply_entry += "Registro: %s\n" % e.registered_at.strftime(formatstr)
                        if e.status in [EntryStatus.TIME_SUBMITTED, EntryStatus.DONE]:
                            reply_entry += "Envio do tempo: %s (%s)\n" % (
                                e.time_submitted_at.strftime(formatstr),
                                timedelta_to_str(
                                    e.time_submitted_at - e.registered_at - time_to_timedelta(e.finish_time)
                                )
                            )
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
        help="Criar uma nova semanal.\nVoc?? n??o poder?? criar uma semanal para um jogo que ainda n??o foi fechado."
             "\nSe o c??digo de verifica????o fornecido for uma URL, esta ser?? tratada como uma imagem."
             "\nSe algum par??metro contiver espa??os, ele dever?? estar \"entre aspas\"."
             "\nEste comando deve ser utilizado APENAS NO PRIVADO.",
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
                raise FrompsBotException(
                    "H?? uma semanal aberta para %s. Feche-a primeiro antes de criar uma nova." % game
                )

            if game in [Games.ALTTPR, Games.OOTR]:
                hash_str = await self.genhash(ctx, game, hash_str)

            lb = self.db.get_open_leaderboard(session, game)
            self.db.create_weekly(session, game, seed_url, hash_str, submission_end, lb)
            session.commit()

            if lb is None:
                msg = "Semanal de %s criada com sucesso!" % game
            else:
                count = len(lb.weeklies)
                msg = "Semanal #%d da leaderboard de %s criada com sucesso!" % (count, game)
            await ctx.message.reply(msg)

    @commands.command(
        name="weeklytest",
        aliases=['testarsemanal'],
        help="Testa a cria????o de uma semanal.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Testa a cria????o de uma semanal.",
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
        help="Encerra completamente uma semanal.\nExecute este comando apenas quando a semanal estiver completamente"
             " conclu??da, pois n??o ser?? mais poss??vel listar as entradas ap??s isto.\nAo executar este comando, todos"
             " os jogadores que n??o tiverem conclu??do completamente sua participa????o (enviando o tempo e o VOD),"
             " receber??o o status 'DNF'\nEste comando deve ser utilizado APENAS NO PRIVADO.",
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
                raise FrompsBotException("A semanal de %s n??o est?? aberta." % game)

            self.db.close_weekly(session, weekly)
            if weekly.leaderboard is not None:
                update_weekly(self.db, session, weekly)

            session.commit()
            await ctx.message.reply("Semanal de %s fechada com sucesso!" % game)

    @commands.command(
        name="weeklyreopen",
        aliases=['reabrirsemanal'],
        help="Reabre a ??ltima semanal fechada.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Reabre a ??ltima semanal fechada.",
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
                raise FrompsBotException("A semanal de %s n??o est?? fechada." % game)
            weekly = self.db.get_last_closed_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("N??o h?? uma semanal de %s fechada." % game)
            self.db.reopen_weekly(session, weekly)
            session.commit()

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
                raise FrompsBotException("N??o h?? uma semanal aberta para %s." % game)

            if len(weekly.entries) > 0 and weekly.seed_url != seed_url:
                raise FrompsBotException(
                    "Existem entradas registradas para esta semanal, portanto n??o ?? poss??vel alterar a URL da seed."
                )

            if game in [Games.ALTTPR, Games.OOTR]:
                hash_str = await self.genhash(ctx, game, hash_str)

            self.db.update_weekly(session, weekly, seed_url, hash_str, submission_end)
            session.commit()

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
            id_jogador: int,
            parametro: str,
            valor: str
    ):
        game = codigo_do_jogo
        player_id = id_jogador
        parameter = str.lower(parametro)
        value = valor
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            weekly = self.db.get_open_weekly(session, game)
            if weekly is None:
                raise FrompsBotException("N??o h?? uma semanal de %s em andamento." % game)

            player = self.db.get_player(session, player_id)
            if player is not None:
                entry = self.db.get_player_entry(session, weekly.id, player.discord_id)
            if player is None or entry is None:
                raise FrompsBotException("O usu??rio informado n??o est?? participando da semanal de %s." % game)

            if entry.status == EntryStatus.DNF:
                raise FrompsBotException("%s n??o est?? mais participando da semanal de %s." % (entry.player.name, game))

            if parameter == 'time':
                converter = TimeConverter()
                try:
                    finish_time = await converter.convert(ctx, value)
                except Exception:
                    raise FrompsBotException(
                        "O tempo fornecido deve estar no formato '%s'." % converter.description_format
                    )

                if entry.status not in [EntryStatus.TIME_SUBMITTED, EntryStatus.DONE]:
                    raise FrompsBotException(
                        "%s ainda n??o enviou seu tempo para a semanal de %s." % (entry.player.name, game)
                    )

                self.db.update_time(session, entry, finish_time)

            elif parameter == 'vod':
                if entry.status is not EntryStatus.DONE:
                    raise FrompsBotException(
                        "%s ainda n??o enviou seu VOD para a semanal de %s." % (entry.player.name, game)
                    )

                self.db.update_vod(session, entry, value)

            else:
                raise FrompsBotException("Par??metro desconhecido: %s." % parametro)

            session.commit()
            await ctx.message.reply(
                "Entrada de %s para a semanal de %s alterada com sucesso!" % (entry.player.name, game)
            )

    @commands.group(
        name="leaderboard",
        aliases=['lb'],
        help="Mostra a leaderboard ativa.",
        brief="Mostra a leaderboard ativa.",
        invoke_without_command=True,
        ignore_extra=False,
    )
    async def leaderboard(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo

        with self.db.Session() as session:
            lb = self.db.get_open_leaderboard(session, game)
            if lb is None:
                await ctx.reply("N??o h?? uma leaderboard aberta para %s." % game)
            else:
                if lb.results_url is None:
                    await ctx.reply("Os resultados da leaderboard de %s ainda n??o foram publicados." % game)
                else:
                    await ctx.reply("Leaderboard de %s: <%s>" % (game, lb.results_url))

    @leaderboard.command(
        name="entrar",
        aliases=['enter', 'e'],
        help="Participar de uma leaderboard.\nIsso afeta apenas as seeds que solicitar ap??s entrar na leaderboard. Caso"
             " tenha solicitado uma seed antes de entrar, seu resultado n??o ser?? inserido na leaderboard.",
        brief="Participar de uma leaderboard.",
        ignore_extra=False,
        signup_only=True
    )
    async def leaderboard_enter(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo

        with self.db.Session() as session:
            player = self.db.get_or_create_player(session, ctx.author)
            if not self.db.excluded_from_leaderboard(session, player, game):
                raise FrompsBotException("Voc?? j?? est?? participando da leaderboard de '%s'." % game)
            self.db.include_on_leaderboard(session, player, game)
            session.commit()
            await ctx.reply("Voc?? entrou para a leaderboard de '%s'." % game)

    @leaderboard.command(
        name="sair",
        aliases=['quit', 'q'],
        help="Deixar de participar de uma leaderboard.\nVoc?? ainda pode pedir seeds e participar das races, mas seu"
             " resultado n??o ser?? considerado na leaderboard.\nIsso afeta apenas as seeds que solicitar ap??s sair da"
             " leaderboard. Caso tenha solicitado uma seed antes de sair, seu resultado ser?? inserido na leaderboard.",
        brief="Deixar de participar de uma leaderboard.",
        ignore_extra=False,
        signup_only=True
    )
    async def leaderboard_quit(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo

        with self.db.Session() as session:
            player = self.db.get_or_create_player(session, ctx.author)
            if self.db.excluded_from_leaderboard(session, player, game):
                raise FrompsBotException("Voc?? j?? saiu da leaderboard de '%s'." % game)
            self.db.exclude_from_leaderboard(session, player, game)
            session.commit()
            await ctx.reply("Voc?? n??o est?? mais participando da leaderboard de '%s'." % game)

    @leaderboard.command(
        name="open",
        aliases=['o'],
        help="Abrir uma nova leaderboard.\nVoc?? n??o poder?? abrir uma leaderboard se houver outra aberta para o mesmo jogo.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Abrir uma uma nova leaderboard.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    async def leaderboard_open(self, ctx, codigo_do_jogo: GameConverter(), url_dos_resultados=None):
        game = codigo_do_jogo
        results_url = url_dos_resultados
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            lb = self.db.get_open_leaderboard(session, game)
            if lb is not None:
                raise FrompsBotException(
                    "H?? uma leaderboard aberta para %s. Feche-a primeiro antes de criar uma nova." % game
                )

            open_weekly = self.db.get_open_weekly(session, game)
            if open_weekly is not None:
                raise FrompsBotException(
                    "N??o foi poss??vel abrir a leaderboard de '%s' pois h?? uma semanal aberta para este jogo." % game
                )

            self.db.create_leaderboard(session, game, results_url)
            session.commit()

            await ctx.message.reply("Leaderboard de %s aberta com sucesso!" % game)

    @leaderboard.command(
        name="close",
        aliases=['x'],
        help="Fechar a leaderboard aberta.\nVoc?? n??o poder?? fechar a leaderboard se houver uma semanal aberta.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Criar uma nova leaderboard.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    async def leaderboard_close(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            lb = self.db.get_open_leaderboard(session, game)
            if lb is None:
                raise FrompsBotException("A leaderboard de %s n??o est?? aberta." % game)

            weekly = self.db.get_open_weekly(session, game)
            if weekly is not None:
                raise FrompsBotException("N??o foi poss??vel fechar a leaderboard pois h?? uma semanal de %s aberta." % game)

            self.db.close_leaderboard(session, lb)
            session.commit()

            await ctx.message.reply("Leaderboard de %s fechada com sucesso!" % game)

    @leaderboard.command(
        name="update",
        aliases=['u'],
        help="Fechar a leaderboard aberta.\nVoc?? n??o poder?? fechar a leaderboard se houver uma semanal aberta.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Criar uma nova leaderboard.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    async def leaderboard_update(self, ctx, codigo_do_jogo: GameConverter()):
        game = codigo_do_jogo
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            lb = self.db.get_open_leaderboard(session, game)
            if lb is None:
                raise FrompsBotException("A leaderboard de %s n??o est?? aberta." % game)

            update_leaderboard(self.db, session, lb)
            session.commit()
            await ctx.reply("A leaderboard de %s foi atualizada!" % game)


    @leaderboard.command(
        name="add",
        aliases=['a'],
        help="Adiciona uma semanal ?? leaderboard atual. Caso n??o seja especificada uma semanal e houver uma aberta, esta ser?? adicionada ?? leaderboard.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Adiciona uma semanal ?? leaderboard atual.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    async def leaderboard_add(self, ctx, codigo_do_jogo: GameConverter(), weekly_id: int = None):
        raise FrompsBotException("N??o implementado.")

    @leaderboard.command(
        name="remove",
        aliases=['r'],
        help="Remove uma semanal da leaderboard atual. Caso n??o seja especificada uma semanal e houver uma aberta, esta ser?? removida da leaderboard.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Remove uma semanal da leaderboard atual.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    async def leaderboard_remove(self, ctx, codigo_do_jogo: GameConverter(), weekly_id: int = None):
        raise FrompsBotException("N??o implementado.")

    @leaderboard.command(
        name="url",
        help="Define ou altera a url para os resultados da leaderboard.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Define ou altera a url para os resultados da leaderboard.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    async def leaderboard_url(self, ctx, codigo_do_jogo: GameConverter(), url_dos_resultados):
        game = codigo_do_jogo
        results_url = url_dos_resultados
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            lb = self.db.get_open_leaderboard(session, game)
            if lb is None:
                raise FrompsBotException("A leaderboard de %s n??o est?? aberta." % game)

            lb.results_url = results_url
            session.commit()
            ctx.reply("URL para os resultados da leaderboard de %s alterada com sucesso." % game)

    @leaderboard.command(
        name="set",
        aliases=['s'],
        help="Altera um par??metro da leaderboard.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Altera um par??metro da leaderboard.",
        ignore_extra=False,
        hidden=True,
        dm_only=True
    )
    async def leaderboard_set(self, ctx, codigo_do_jogo: GameConverter(), parametro: str, valor: str = None):
        game = codigo_do_jogo
        parameter = parametro
        value = valor
        self._check_monitor(ctx.author, game)

        with self.db.Session() as session:
            lb = self.db.get_open_leaderboard(session, game)
            if lb is None:
                raise FrompsBotException("A leaderboard de %s n??o est?? aberta." % game)

            if value is None:
                if parameter in lb.leaderboard_data.keys():
                    del lb.leaderboard_data[parameter]
                    session.commit()
                    await ctx.reply("Par??metro '%s' removido com sucesso!" % parameter)
                else:
                    raise FrompsBotException("Par??metro '%s' n??o foi setado ainda." % parameter)
            else:
                lb.leaderboard_data[parameter] = value
                session.commit()
                await ctx.reply("Par??metro '%s' atualizado com sucesso!" % parameter)

    @commands.group(
        name="stat",
        help="Show some statistics.",
        brief="Show some statistics.",
        invoke_without_command=True,
        hidden=True,
        ignore_extra=False,
        dm_only=True
    )
    async def stat(self, ctx, sub):
        pass

    @stat.command(
        name="confronto_periodo",
        help="Mostra stats do confronto de dois jogadores.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Mostra stats do confronto de dois jogadores.",
        ignore_extra=False,
        dm_only=True
    )
    async def stat_headtohead_dated(
            self,
            ctx,
            codigo_do_jogo: GameConverter(),
            id_do_jogador1: int,
            id_do_jogador2: int,
            data_inicial: DateConverter(),
            data_final: DateConverter()
    ):
        await self.do_head_to_head(ctx, codigo_do_jogo, id_do_jogador1, id_do_jogador2, data_inicial, data_final)

    @stat.command(
        name="confronto",
        help="Mostra stats do confronto de dois jogadores.\nEste comando deve ser utilizado APENAS NO PRIVADO.",
        brief="*NO PRIVADO* Mostra stats do confronto de dois jogadores.",
        ignore_extra=False,
        dm_only=True
    )
    async def stat_headtohead(self, ctx, codigo_do_jogo: GameConverter(), id_do_jogador1: int, id_do_jogador2: int):
        await self.do_head_to_head(ctx, codigo_do_jogo, id_do_jogador1, id_do_jogador2)

    async def do_head_to_head(self, ctx, game, discord_id_1, discord_id_2, initial_date=None, final_date=None):
        self._check_admin(ctx.author)

        if discord_id_1 == discord_id_2:
            raise FrompsBotException("Os jogadores devem ser diferentes!")

        with self.db.Session() as session:
            player1 = self.db.get_player(session, discord_id_1)
            if player1 is None:
                raise FrompsBotException("N??o foi encontrado um jogador com id: %d" % discord_id_1)
            player2 = self.db.get_player(session, discord_id_2)
            if player2 is None:
                raise FrompsBotException("N??o foi encontrado um jogador com id: %d" % discord_id_2)

            values = self.db.get_head_to_head(
                session,
                game,
                player1.discord_id,
                player2.discord_id,
                initial_date,
                final_date
            )
            results = {
                "matches": len(values),
                "players": [player1, player2],
                "dnfs": [0, 0],
                "victories": [0, 0],
                "ties": 0,
                "victories_with_dnfs": [0, 0],
                "ties_with_dnfs": 0
            }

            for value in values.values():
                entry1 = value["entries"][0]
                entry2 = value["entries"][1]
                if entry1.finish_time is None or entry2.finish_time is None:
                    if entry1.finish_time is None:
                        results["dnfs"][0] += 1
                        if entry2.finish_time is None:
                            results["dnfs"][1] += 1
                            results["ties_with_dnfs"] += 1
                        else:
                            results["victories_with_dnfs"][1] += 1
                    else:
                        results["dnfs"][1] += 1
                        results["victories_with_dnfs"][0] += 1
                else:
                    if entry1.finish_time < entry2.finish_time:
                        results["victories"][0] += 1
                        results["victories_with_dnfs"][0] += 1
                    elif entry2.finish_time < entry1.finish_time:
                        results["victories"][1] += 1
                        results["victories_with_dnfs"][1] += 1
                    else:
                        results["ties"] += 1
                        results["ties_with_dnfs"] += 1

            msg = "Confrontos diretos entre **%s** e **%s** em **%s**\n\n" % (player1.name, player2.name, game)
            msg += "N??mero de partidas: **%d**\n" % results["matches"]
            msg += "DNFs: **%d x %d**\n" % (results["dnfs"][0], results["dnfs"][1])
            msg += "Resultado (excluindo DNFs): **%d x %d** (**%d** empates)\n" % \
                   (results["victories"][0], results["victories"][1], results["ties"])
            msg += "Resultado (incluindo DNFs): **%d x %d** (**%d** empates)\n" % \
                   (results["victories_with_dnfs"][0], results["victories_with_dnfs"][1], results["ties_with_dnfs"])

            await ctx.reply(msg)

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

    def _check_admin(self, user):
        if user.id not in self.admins:
            raise FrompsBotException("Este comando deve ser executado apenas por administradores.")

    def _check_monitor(self, user, game=None):
        if game is not None:
            if game in self.monitors.keys() and user.id in self.monitors[game]:
                return
            raise FrompsBotException("Voc?? n??o ?? monitor de %s." % game)

        for monitor_list in self.monitors.values():
            if user.id in monitor_list:
                return
        raise FrompsBotException("Este comando deve ser executado apenas por monitores.")
