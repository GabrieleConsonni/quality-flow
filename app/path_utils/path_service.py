import os

def get_app_path() -> str:
    return os.path.join(os.getcwd(), "app")


def get_project_root_path() -> str:
    return os.getcwd()
