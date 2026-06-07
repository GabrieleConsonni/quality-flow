from pydantic import BaseModel, ConfigDict

from models.settings.multitenant_settings import MultitenantSettings


class QualityFlowSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    multitenant: MultitenantSettings
