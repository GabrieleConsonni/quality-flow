from pydantic import BaseModel, Field, model_validator

from elaborations.models.dtos.configuration_command_dto import ConfigurationOperationTypes


def _normalize_endpoint(endpoint: str) -> str:
    value = str(endpoint or "").strip().strip("/")
    if not value:
        raise ValueError("endpoint is required.")
    return value.lower()


def _normalize_path(path: str) -> str:
    raw = str(path or "").strip()
    if not raw:
        return "/"
    if not raw.startswith("/"):
        raw = f"/{raw}"
    if len(raw) > 1:
        raw = raw.rstrip("/")
    return raw


class MockServerConfigurationDto(BaseModel):
    endpoint: str
    authorization: dict | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        self.endpoint = _normalize_endpoint(self.endpoint)
        return self


class MockServerOperationDto(BaseModel):
    order: int = 0
    description: str = ""
    cfg: ConfigurationOperationTypes


class MockServerApiConfigurationDto(BaseModel):
    method: str
    path: str
    params: dict | None = None
    authMode: str | None = "inherit"
    authorization: dict | None = None
    headers: dict | None = None
    body: dict | list | str | int | float | bool | None = None
    body_match: str | None = "contains"
    response: dict | None = None
    response_status: int = 200
    response_headers: dict | None = None
    response_body: dict | list | str | int | float | bool | None = None
    pre_response_commands: list[dict] | None = None
    post_response_commands: list[dict] | None = None
    priority: int = 0

    @model_validator(mode="after")
    def validate_configuration(self):
        method = str(self.method or "").strip().upper()
        if method not in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}:
            raise ValueError(f"Unsupported method '{method}'.")
        self.method = method
        self.path = _normalize_path(self.path)
        auth_mode = str(self.authMode or "inherit").strip()
        if auth_mode not in {"inherit", "none", "custom"}:
            raise ValueError("authMode must be 'inherit', 'none' or 'custom'.")
        self.authMode = auth_mode
        body_match = str(self.body_match or "contains").strip().lower()
        if body_match not in {"contains", "equals"}:
            raise ValueError("body_match must be 'contains' or 'equals'.")
        self.body_match = body_match

        response_cfg = self.response if isinstance(self.response, dict) else {}
        status_value = response_cfg.get("status", self.response_status)
        if isinstance(status_value, dict):
            self.response_status = 200
        else:
            self.response_status = max(int(status_value or 200), 100)

        return self


class MockServerApiDto(BaseModel):
    id: str | None = None
    order: int = 0
    description: str = ""
    cfg: MockServerApiConfigurationDto
    commands: list[MockServerOperationDto] = Field(default_factory=list)


class MockServerQueueConfigurationDto(BaseModel):
    polling_interval_seconds: int = 1
    max_messages: int = 10

    @model_validator(mode="after")
    def validate_configuration(self):
        self.polling_interval_seconds = max(int(self.polling_interval_seconds or 1), 1)
        self.max_messages = max(min(int(self.max_messages or 10), 10), 1)
        return self


class MockServerQueueDto(BaseModel):
    id: str | None = None
    order: int = 0
    description: str = ""
    queue_id: str
    cfg: MockServerQueueConfigurationDto = Field(
        default_factory=MockServerQueueConfigurationDto
    )
    commands: list[MockServerOperationDto] = Field(default_factory=list)


class CreateMockServerDto(BaseModel):
    description: str = ""
    cfg: MockServerConfigurationDto
    apis: list[MockServerApiDto] = Field(default_factory=list)
    queues: list[MockServerQueueDto] = Field(default_factory=list)
    is_active: bool = False


class UpdateMockServerDto(CreateMockServerDto):
    id: str

