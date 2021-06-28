from util import load_conf, setup_logging
from database import Database
from bot import create_bot



def main():
    cfg = load_conf()
    setup_logging(cfg['logging'])

    import logging
    logger = logging.getLogger(__name__)

    db = Database(**cfg['database'])
    bot = create_bot(cfg['bot'], db)

    @bot.event
    async def on_ready():
        print('Logged in as %s<%s>' % (bot.user.name, bot.user.id))
        print('------')
        logger.info("BOT IS READY!")

    bot.run(cfg['bot']['token'])


if __name__ == '__main__':
    main()
