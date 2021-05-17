import discord
import re
from datetime import datetime


def seed_embed(weekly):
    embed = discord.Embed(
        title="ZRBR Semanal - Majoras Mask Randomizer",
        colour=discord.Colour(weekly.game.color),
        description="""
        
        **INSTRUÇÕES**
                
        1) Faça o download da seed (link abaixo) e confira se o código de verificação está correto.
        
        2) Grave a sua gameplay localmente, ou faça uma stream não listada no youtube sem divulgá-la a ninguém. Sua gravação deve conter, a todo momento, o **timer**, a **imagem limpa** do jogo. **Apenas o áudio do jogo** deve aparecer durante a gameplay (sem voz, músicas, etc). Atente-se para começar o seu timer no momento correto, conforme as regras do jogo, e não pause-o durante a gameplay.
        
        3) Ao terminar  o jogo, faça um print contendo o timer e a tela do jogo. Envie o seu tempo final e o print imediatamente, utilizando o seguinte comando neste chat privado (anexe o print na mesma mensagem do comando):
        
        **!time H:MM:SS**
        
        4) Faça o upload da sua gravação para o lugar de sua preferência e envie o link utilizando o seguinte comando neste chat privado:
        
        **!vod %s <link_da_gravacao>**
        
        
        **OBSERVAÇÕES**
        
        - Você não poderá requisitar uma seed de outro jogo até que tenha enviado o seu tempo de conclusão. Se você não pretende terminar esta seed envie o comando **!forfeit** neste chat privado (você receberá instruções para confirmar esta ação).
        
        - Você deve enviar o seu tempo assim que terminar de jogar a seed, mas a sua gravação pode ser enviada a posteriori, desde que não ultrapasse o limite de envios para esta semanal, no dia **%s** às **%s** (horário de Brasília).
        
        
        **GLHF**
        
        ----
        """ % (weekly.game.keys[0], weekly.submission_end.strftime("%d/%m/%Y"), weekly.submission_end.strftime("%H:%M"))
    )

    embed.add_field(name="Seed", value=weekly.seed_url, inline=False)

    if re.match("https?://", weekly.seed_hash):
        embed.set_image(url=weekly.seed_hash)
    else:
        embed.add_field(name="Código de Verificação", value=weekly.seed_hash, inline=False)

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
