import discord
import re
from datetime import datetime
from datatypes import Games


def seed_embed(ctx, weekly, instructions):
    signup_channel = "semanais-seed" if isinstance(ctx.message.channel, discord.DMChannel) else ctx.message.channel.name
    game = weekly.game
    description = instructions['ALL'] + "\n" + instructions[game]

    #TODO: Set this with the game
    verification_text = "Código de Verificação"
    if game == Games.HKR:
        verification_text = "Item de Fury of the Fallen"

    description += "\n**Seed:** " + weekly.seed_url + "\n\n**"+ verification_text +":** "
    description = description.format(signup_channel=signup_channel)

    embed = discord.Embed(
        title="RBR Semanal - %s" % weekly.game,
        colour=discord.Colour(weekly.game.color),
        description=description
    )

    if re.match("https?://", weekly.seed_hash):
        embed.set_image(url=weekly.seed_hash)
    else:
        embed.description += weekly.seed_hash
    return embed


def list_embed(weeklies):
    weeklies = sorted(weeklies, key=lambda v: 2 if v.submission_end <= datetime.now() else 1)
    embed = discord.Embed(title="Semanais da Randomizer Brasil")
    if len(weeklies) > 0:
        codes = []
        games = []
        times = []
        for w in weeklies:
            codes.append(w.game.keys[0])
            games.append(str(w.game))

            if w.submission_end > datetime.now():
                time = int(w.submission_end.timestamp())
                times.append(f"<t:{time}>")
            else:
                times.append("ENCERRADO")

        embed.add_field(name="Código", value="\n".join(codes))
        embed.add_field(name="Jogo", value="\n".join(games))
        embed.add_field(name="Inscrições até (hora local)", value="\n".join(times))
    else:
        embed.description = "Nenhuma semanal aberta no momento."

    return embed
