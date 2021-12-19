from util import load_conf, setup_logging
from database import Database
from bot import create_bot
from api import create_api

import asyncio


def main():
    cfg = load_conf()
    setup_logging(cfg['logging'])

    import logging
    logger = logging.getLogger(__name__)

    db = Database(**cfg['database'])
    bot = create_bot(db, cfg)
    api = create_api(db, cfg['api'])

    @bot.listen()
    async def on_ready():
        print('Logged in as %s<%s>' % (bot.user.name, bot.user.id))
        print('------')
        logger.info("BOT IS READY!")

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start())
    loop.create_task(api.run(use_reloader=False, loop=loop))
    loop.run_forever()


if __name__ == '__main__':
    main()
