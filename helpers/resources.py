import os


def get_resource(resource_name):
    resource_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../resources')
    return os.path.join(resource_path, resource_name)
