import discord
import re


def setup(bot):
    filter_command = re.compile(r'^' + re.escape(bot.command_prefix) + r'(.*)$')
    filter_signup = re.compile(
        r'^' + re.escape(bot.command_prefix) + r'(ajuda|semanais|weeklies|semente|seed).*$')
    filter_dm = re.compile(
        r'^' + re.escape(bot.command_prefix) + r'(ajuda|semanais|weeklies|tempo|time|desistir|forfeit|video|gravacao|vod|entradas|inscricoes|entries|criarsemanal|weeklycreate|testarsemanal|weeklytest|encerrarsemanal|weeklyclose|alterarsemanal|weeklyupdate|alterarentrada|entryupdate|comentario|comment).*$'
    )

    signup_channel = getattr(bot, 'signup_channel', None)
    testing = getattr(bot, 'testing', False)

    @bot.event
    async def on_message(message):

        # ignore messages sent by this bot or that were not sent to this bot's DM channel or to the signup channel
        if message.author.id == bot.user.id or (
                not isinstance(message.channel, discord.DMChannel) and message.channel.id != signup_channel):
            return

        is_command = filter_command.match(message.content)
        signup_command = filter_signup.match(message.content)
        dm_command = filter_dm.match(message.content)

        # ignore any message that is not a command supposed to be sent in private
        if isinstance(message.channel, discord.DMChannel):
            if not is_command:
                return
            if not dm_command and signup_command:
                await message.reply(
                    "O comando '%s' deve ser usado no canal #%s." % (
                        signup_command.group(1), bot.get_channel(signup_channel).name))
                return

        # ignore any message that is not a command supposed to be sent on the signup channel
        elif message.channel.id == signup_channel:
            if not signup_command:
                # The message is deleted to maintain the channel clean and spoiler free. For testing purposes, only commands
                # that are supposed to be sent in private are deleted when testing mode is active
                if not testing or dm_command:
                    await message.delete()
                # inform the author if the command should be sent in private
                if dm_command:
                    await message.author.send(
                        "O comando '%s' deve ser usado neste canal privado." % dm_command.group(1))
                return

        async with message.channel.typing():
            await bot.process_commands(message)
