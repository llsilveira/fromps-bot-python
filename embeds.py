import discord
from datetime import datetime
from datatypes import Games

import logging
logger = logging.getLogger(__name__)


def seed_embed(weekly, instructions):
    game = weekly.game
    description = instructions['ALL'] + "\n" + instructions[game]
    description += "\n**Link:** " + weekly.seed_url + "\n\n**Código de Verificação:** "

    embed = discord.Embed(
        title="ZRBR Semanal - %s" % weekly.game,
        colour=discord.Colour(weekly.game.color),
        description=description
    )

    if game is Games.MMR:
        embed.set_image(url=weekly.seed_hash)
    else:
        embed.description += weekly.seed_hash
    return embed


def list_embed(weeklies):
    weeklies = sorted(weeklies, key=lambda v: 2 if v.submission_end <= datetime.now() else 1)
    embed = discord.Embed(title="Semanais da ZRBR")
    if len(weeklies) > 0:
        codes = []
        games = []
        times = []
        for w in weeklies:
            codes.append(w.game.keys[0])
            games.append(str(w.game))

            if w.submission_end > datetime.now():
                times.append(w.submission_end.strftime("%d/%m/%Y %H:%M"))
            else:
                times.append("ENCERRADO")

        embed.add_field(name="Código", value="\n".join(codes))
        embed.add_field(name="Jogo", value="\n".join(games))
        embed.add_field(name="Enviar até", value="\n".join(times))
    else:
        embed.description = "Nenhuma semanal aberta no momento."

    return embed
