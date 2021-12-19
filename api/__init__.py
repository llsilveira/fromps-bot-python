from .Api import Api


def create_api(db, config):
    return Api(db, config)
