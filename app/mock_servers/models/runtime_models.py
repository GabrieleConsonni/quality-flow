from dataclasses import dataclass, field
from typing import Any


@dataclass
class MockCommandSnapshot:
    id: str
    description: str
    command_code: str
    command_type: str
    configuration_json: dict[str, Any]
    order: int
    code: str = ""
    operation_type: str = ""

    def __post_init__(self):
        if not self.command_code:
            self.command_code = str(self.operation_type or self.code or "").strip()
        if not self.code:
            self.code = self.command_code
        if not self.operation_type:
            self.operation_type = self.command_code


@dataclass
class MockApiRoute:
    id: str
    description: str
    order: int
    method: str
    path: str
    params: dict[str, Any]
    headers: dict[str, Any]
    body: Any
    body_match: str
    priority: int
    response_status: Any
    response_headers: dict[str, Any]
    response_body: Any
    code: str = ""
    commands: list[MockCommandSnapshot] = field(default_factory=list)
    pre_response_commands: list[MockCommandSnapshot] = field(default_factory=list)
    post_response_commands: list[MockCommandSnapshot] = field(default_factory=list)
    operations: list[MockCommandSnapshot] = field(default_factory=list)
    response_operations: list[MockCommandSnapshot] = field(default_factory=list)


@dataclass
class MockQueueBinding:
    id: str
    description: str
    order: int
    queue_id: str
    polling_interval_seconds: int
    max_messages: int
    code: str = ""
    commands: list[MockCommandSnapshot] = field(default_factory=list)


@dataclass
class MockRuntimeServer:
    id: str
    description: str
    endpoint: str
    is_active: bool
    code: str = ""
    apis: list[MockApiRoute] = field(default_factory=list)
    queues: list[MockQueueBinding] = field(default_factory=list)


# Backward aliases during the refactor.
MockOperationSnapshot = MockCommandSnapshot
