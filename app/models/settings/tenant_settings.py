from pydantic import BaseModel, ConfigDict, Field

from models.settings.database_settings import DatabaseSettings


class TenantSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid", frozen=True)
    tenant_id: str = Field(..., alias="tenantId", min_length=1)
    database: DatabaseSettings
