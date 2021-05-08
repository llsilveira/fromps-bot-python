import os
from dotenv import load_dotenv
load_dotenv()

DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
INSTANCE_PATH = os.environ['INSTANCE_PATH']
VERBOSE = os.environ.get("VERBOSE", "False").lower() in ['true', 't', 'yes', 'y', '1', 'on']

DATABASE_PATH = os.path.join(INSTANCE_PATH, 'db.sqlite')

ADMINS = [
    "491980801026555915", #Cesinha
    "119135787383128068", #Grafitte
    "237744469133361152", #Tso
    "343878980358635520" #llsilveira
]


class ConfigError(Exception):
    pass


def check_config():
    assert DISCORD_TOKEN is not None
    assert INSTANCE_PATH is not None

    if not os.path.exists(INSTANCE_PATH):
        os.makedirs(INSTANCE_PATH)
    if not os.path.isdir(INSTANCE_PATH) or not os.access(INSTANCE_PATH, os.W_OK):
        raise ConfigError("'INSTANCE_PATH' is not a writable directory")


check_config()
