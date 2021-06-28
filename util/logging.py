import os
import logging
import logging.handlers


class LogFilter(logging.Filter):
    def __init__(self, path):
        super(LogFilter, self).__init__()
        self.path = path

    def filter(self, record):
        return os.path.abspath(record.pathname).find(self.path) == 0


def setup_logging(config):
    numeric_level = getattr(logging, config.get('level', 'INFO').upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % config['level'])
    formatter = logging.Formatter(
        fmt=config.get('format', "%(asctime)s:%(name)s:%(levelname)s:%(message)s"),
        datefmt=config.get('datefmt', "%Y-%m-%d %H:%M:%S"))

    logfile = config.get('logfile', None)
    print(logfile)
    if logfile is None:
        handler = logging.StreamHandler()
    else:
        handler = logging.handlers.RotatingFileHandler(
            logfile, maxBytes=config.get('maxbytes', 1000000), backupCount=config.get('count', 5)
        )
        handler.addFilter(LogFilter(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    logger.addHandler(handler)
