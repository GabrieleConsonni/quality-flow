from pydantic import BaseModel, ConfigDict, Field

from models.settings.tenant_settings import TenantSettings


class MultitenantSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tenants: list[TenantSettings] = Field(default_factory=list)
