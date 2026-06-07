from __future__ import annotations

import os
from typing import Optional

from models.settings.application_settings import ApplicationSettings
from omegaconf import OmegaConf
from path_utils.path_service import get_project_root_path

_settings: Optional[ApplicationSettings] = None


def load_config() -> ApplicationSettings:
    global _settings
    base_config_path = os.path.join(get_project_root_path(), "application.yaml")

    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    env_config_path = os.path.join(get_project_root_path(), f"application-{app_env}.yaml")

    base_config = OmegaConf.load(base_config_path)
    env_config = OmegaConf.load(env_config_path)
    merged_config = OmegaConf.merge(base_config, env_config)

    config_dict = OmegaConf.to_container(merged_config, resolve=True)
    _settings = ApplicationSettings.model_validate(config_dict)

    return _settings


def get_settings() -> ApplicationSettings:
    if _settings is None:
        raise RuntimeError("Settings have not been loaded. Call load_config() first.")
    return _settings
