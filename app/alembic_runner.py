import os

from alembic.config import Config
from alembic import command
from pathlib import Path

from exceptions.app_exception import QualityFlowAppException


def run_alembic_migrations():
    project_dir = Path(__file__).parent.parent
    alembic_ini_path = os.path.join(project_dir, "alembic.ini")

    if not os.path.isfile(alembic_ini_path):
        raise QualityFlowAppException("Alembic configuration file not found!")

    alembic_cfg: Config = Config(alembic_ini_path)
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        raise QualityFlowAppException(f"Errore Alembic: {str(e)}")
