import config
from database import Database
from bot import create_bot

import logging
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    cfg = config.load_conf()
    db = Database(**cfg['database'])
    bot = create_bot(cfg['bot'], db, cfg['general'].get('testing', False))

    @bot.event
    async def on_ready():
        print('Logged in as %s<%s>' % (bot.user.name, bot.user.id))
        print('------')
        logger.info("BOT IS READY!")

    bot.run(cfg['bot']['token'])
