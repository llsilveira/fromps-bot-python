import os
import configparser
import ast
import dotenv

dotenv.load_dotenv()
INSTANCE_PATH = os.environ.get("INSTANCE_PATH", os.getcwd())
CONFIG_FILE = os.environ.get("CONFIG_FILE", os.path.join(INSTANCE_PATH, "config.ini"))


class AppConfigParser(configparser.ConfigParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self, section, option, raw=False, vars=None, fallback=None):
        return ast.literal_eval(super().get(section, option, raw=raw, vars=vars, fallback=fallback))


def load_conf(config_file=CONFIG_FILE):
    parser = AppConfigParser(interpolation=configparser.ExtendedInterpolation())
    parser.read_dict({'env': {'instance_path': '"' + INSTANCE_PATH + '"'}})
    parser.read(config_file)
    return parser
