import discord
from discord.ext import commands
from datetime import datetime

from datatypes import EntryStatus
from helpers import get_discord_name, GameConverter
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

    @commands.command(
        name='seed',
        help="Solicitar seed da semanal"
    )
    async def seed(self, ctx, *args):
        with self.db.Session() as session:
            message = ctx.message

            if message.channel.id != self.config['channels']['signup']:
                raise SeedBotException(
                    "Este comando deve ser enviado no canal #%s." %
                    self.bot.get_channel(self.config['channels']['signup']).name
                )

            if len(args) != 1:
                raise SeedBotException("O formato correto deste comando é: %s%s <jogo>" % (ctx.prefix, ctx.invoked_with) )

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

    @commands.command(
        name="time",
        help="Enviar o tempo final da seed jogada"
    )
    async def time(self, ctx, *args):
        with self.db.Session() as session:
            if not isinstance(ctx.message.channel, discord.DMChannel):
                raise SeedBotException(
                    "O comando '%s' deve ser utilizado apenas neste canal privado." % ctx.invoked_with,
                    delete_origin=True,
                    reply_on_private=True
                )

            if len(args) != 1:
                raise SeedBotException("O formato correto deste comando é: %s%s H:MM:SS" % (ctx.prefix, ctx.invoked_with))

            try:
                time = datetime.strptime(args[0], "%H:%M:%S").time()
            except:
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

    @commands.command(
        name="forfeit",
        help="Desistir da participação na semanal atual"
    )
    async def forfeit(self, ctx, *args):
        with self.db.Session() as session:
            if not isinstance(ctx.message.channel, discord.DMChannel):
                raise SeedBotException(
                    "O comando '%s' deve ser utilizado apenas neste canal privado." % ctx.invoked_with,
                    delete_origin=True,
                    reply_on_private=True
                )

            author_id = ctx.author.id
            entry = self.db.get_registered_entry(session, author_id)
            if entry is None:
                raise SeedBotException("Você já registrou seu tempo ou não está participando de uma semanal.")

            if len(args) < 1 or len(args) > 1 or str.lower(args[0]) != "ok":
                raise SeedBotException(
                    "Confirme sua desistência da semanal de %s ação enviando o comando '%sforfeit ok' aqui." %  (entry.weekly.game, ctx.prefix)
                )

            self.db.forfeit_player(session, entry.weekly, author_id)
            await ctx.message.reply("Você não está mais participando da semanal de %s." % entry.weekly.game)

    @commands.command(
        name="vod",
        help="Enviar o vod da seed jogada"
    )
    async def vod(self, ctx, *args):
        with self.db.Session() as session:
            if not isinstance(ctx.message.channel, discord.DMChannel):
                raise SeedBotException(
                    "O comando '%s' deve ser utilizado apenas neste canal privado." % ctx.invoked_with,
                    delete_origin=True,
                    reply_on_private=True
                )

            if len(args) != 2:
                raise SeedBotException("O formato correto deste comando é: %s%s <jogo> <vod_url>" % (ctx.prefix, ctx.invoked_with) )

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

    @commands.command(
        name="entries",
        checks=[privileged],
        hidden=True
    )
    async def entries(self, ctx, *args):
        with self.db.Session() as session:
            if not isinstance(ctx.message.channel, discord.DMChannel):
                raise SeedBotException(
                    "O comando '%s' deve ser utilizado apenas neste canal privado." % ctx.invoked_with,
                    delete_origin=True,
                    reply_on_private=True
                )

            if len(args) != 1:
                raise SeedBotException("O formato correto deste comando é: %s%s <jogo>" % (ctx.prefix, ctx.invoked_with))

            game = GameConverter.convert(args[0])
            if game is None:
                raise SeedBotException("Jogo desconhecido.")

            weekly = self.db.get_open_weekly(session, game)
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

    @commands.command(checks=[privileged], enabled=False)
    async def create(self, ctx, game: GameConverter, seed_url: str, seed_hash: str,
                     submission_end):
        with self.db.Session() as session:
            print(game, seed_url, seed_hash, submission_end)
