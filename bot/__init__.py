import discord
from discord.ext import commands

from .cogs import weekly_races


class ZRBRBot(commands.Bot):

    class ZRBRHelpCommand(commands.DefaultHelpCommand):
        def __init__(self):
            super().__init__(
                command_attrs={
                    "name": "ajuda",
                    "help": "Mostrar esta mensagem"
                },
                commands_heading="Comandos:",
                no_category="Sem categoria",
                dm_help=True
            )

        def get_ending_note(self):
            command_name = self.invoked_with
            return "Envie '{0}{1} comando' para mais informações sobre um comando.".format(self.clean_prefix,
                                                                                           command_name)

    def __init__(self, config):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix=config['command_prefix'],
            intents=intents,
            help_command=ZRBRBot.ZRBRHelpCommand()
        )

        self.ping_on_error = config['ping_on_error']
        self.signup_channel = config['signup_channel']
        self.testing = config['testing']


def create_bot(config, db, testing=False):
    config = dict(config)
    config['testing'] = testing

    bot = ZRBRBot(config)

    bot.load_extension('bot.extensions.reactions_feedback')
    bot.load_extension('bot.extensions.error_handling')
    bot.load_extension('bot.extensions.filter_messages')

    bot.add_cog(weekly_races.Weekly(bot, config, db))

    return bot
