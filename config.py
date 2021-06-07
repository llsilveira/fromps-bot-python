import os
import configparser
import ast
import dotenv
import logging
import logging.handlers

dotenv.load_dotenv()
INSTANCE_PATH = os.environ.get("INSTANCE_PATH", os.getcwd())
CONFIG_FILE = os.environ.get("CONFIG_FILE", os.path.join(INSTANCE_PATH, "config.ini"))


class AppConfigParser(configparser.ConfigParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self, section, option, raw=False, vars=None, fallback=None):
        return ast.literal_eval(super().get(section, option, raw=raw, vars=vars, fallback=fallback))


class LogFilter(logging.Filter):
    def __init__(self, path):
        super(LogFilter, self).__init__()
        self.path = path

    def filter(self, record):
        return os.path.abspath(record.pathname).find(self.path) == 0


def load_conf(config_file=CONFIG_FILE):
    parser = AppConfigParser(interpolation=configparser.ExtendedInterpolation())
    parser.read_dict({'env': {'instance_path': '"' + INSTANCE_PATH + '"'}})
    parser.read(config_file)

    # Logging setup
    cfg = parser['logging']

    numeric_level = getattr(logging, cfg['level'].upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % cfg['level'])
    formatter = logging.Formatter(fmt=cfg['format'], datefmt=cfg['datefmt'])

    if parser['general']['testing']:
        handler = logging.StreamHandler()
    else:
        handler = logging.handlers.RotatingFileHandler(
            cfg['logfile'], maxBytes=int(cfg['maxbytes']), backupCount=int(cfg['count'])
        )
        handler.addFilter(LogFilter(os.path.dirname(os.path.abspath(__file__))))
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    logger.addHandler(handler)

    return parser
