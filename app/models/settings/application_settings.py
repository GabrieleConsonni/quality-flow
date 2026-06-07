from pydantic import BaseModel, ConfigDict

from models.settings.quality_flow_settings import QualityFlowSettings


class ApplicationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    akeron: QualityFlowSettings
