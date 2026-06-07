"""`send_verify` template generator.

Produces the canonical "Send & Verify" chain of suite_item_commands:

    [setVariable payload]?              (only when payload.kind == 'json_inline')
    sendMessageQueue(queue_id, payload)
    sleep(wait_ms)
    [for each assert with target != 'none':
        receiveQueue(target.queue_id)  OR  queryDatabase(target.connection_id, target.database_query)
        assertX(actualRef = last receive/query, expected or expectedRef)
    ]

Phase 2 scope decisions (kept conservative):
* `payload.kind` only supports `json_inline`. `json_array_ref` and
  `dataset_ref` are deferred to Phase 4 (data-driven).
* `operator` only supports `equals` and `exists` (mapped to JSON_EQUALS /
  JSON_NOT_EMPTY). `contains` and `matches_schema` need explicit
  `compare_keys` / json_schema handling — deferred.
* `target` ∈ {`queue`, `database`, `none`}. `none` skips the verify step.

The generator is pure: it builds and returns `CreateSuiteItemCommandDto`
snapshots without any DB I/O.
"""

from __future__ import annotations

from typing import Any

from elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
    CommandCode,
    CommandType,
    ConstantContext,
    ConstantSourceType,
    InputRefDto,
    InputRefKind,
    QueryDatabaseConfigurationCommandDto,
    ReceiveQueueConfigurationCommandDto,
    ResultConstantDto,
    SendMessageQueueConfigurationCommandDto,
    SetVariableConfigurationCommandDto,
    SleepConfigurationCommandDto,
)
from elaborations.models.dtos.test_suite_dto import CreateSuiteItemCommandDto
from elaborations.models.enums.template_kind import TemplateKind
from templating.base import InvalidTemplateConfigError, TemplateMeta
from templating.template_registry import template_registry


_SUPPORTED_PAYLOAD_KINDS = {"json_inline"}
_SUPPORTED_TARGETS = {"queue", "database", "none"}
_SUPPORTED_OPERATORS = {"equals", "exists"}

_OPERATOR_TO_COMMAND_CODE = {
    "equals": CommandCode.JSON_EQUALS.value,
    "exists": CommandCode.JSON_NOT_EMPTY.value,
}


class SendVerifyTemplate:
    meta = TemplateMeta(
        kind=TemplateKind.SEND_VERIFY.value,
        name="Send & Verify",
        description=(
            "Send a message to a queue and verify the side effects on a "
            "queue or a database."
        ),
        config_schema_summary={
            "fields": [
                {"name": "queue_id", "type": "uuid", "required": True},
                {
                    "name": "payload",
                    "type": "object",
                    "required": True,
                    "shape": {
                        "kind": "json_inline",
                        "value": "object",
                    },
                    "phase2_supported_kinds": ["json_inline"],
                    "phase4_planned_kinds": ["json_array_ref", "dataset_ref"],
                },
                {"name": "wait_ms", "type": "integer", "required": False, "default": 500},
                {
                    "name": "asserts",
                    "type": "array<object>",
                    "required": False,
                    "shape": {
                        "target": "queue | database | none",
                        "queue_id": "uuid? (when target=queue)",
                        "connection_id": "uuid? (when target=database)",
                        "database_query": "string? (when target=database)",
                        "operator": "equals | exists",
                        "expected": "object? (when operator=equals)",
                    },
                },
            ],
            "phase2_supported_operators": sorted(_SUPPORTED_OPERATORS),
        },
    )

    def generate_commands(
        self, template_config: dict
    ) -> list[CreateSuiteItemCommandDto]:
        config = template_config or {}
        queue_id = _require_str(config.get("queue_id"), "queue_id is required for send_verify.")
        payload = _require_dict(config.get("payload"), "payload is required for send_verify.")
        wait_ms = _coerce_wait_ms(config.get("wait_ms"), default=500)
        asserts = _coerce_assert_list(config.get("asserts"))

        order = 0
        commands: list[CreateSuiteItemCommandDto] = []

        payload_kind = _normalize_token(payload.get("kind"))
        if payload_kind not in _SUPPORTED_PAYLOAD_KINDS:
            raise InvalidTemplateConfigError(
                f"payload.kind must be one of {sorted(_SUPPORTED_PAYLOAD_KINDS)}; "
                f"got '{payload_kind}'."
            )

        payload_value = payload.get("value")
        payload_definition_id = "tpl_sv_payload"

        # 1. setVariable that materialises the inline JSON payload.
        commands.append(
            _wrap(
                order,
                description="Materialize inline JSON payload",
                cfg=SetVariableConfigurationCommandDto(
                    commandCode=CommandCode.SET_VARIABLE.value,
                    commandType=CommandType.CONTEXT.value,
                    definitionId=payload_definition_id,
                    name="payload",
                    context=ConstantContext.LOCAL.value,
                    valueType=ConstantSourceType.JSON.value,
                    value=payload_value,
                ),
            )
        )
        order += 1

        # 2. sendMessageQueue referencing the payload constant.
        commands.append(
            _wrap(
                order,
                description=f"Send message to queue '{queue_id}'",
                cfg=SendMessageQueueConfigurationCommandDto(
                    queue_id=queue_id,
                    inputRef=InputRefDto(
                        kind=InputRefKind.RUNTIME_VALUE.value,
                        definitionId=payload_definition_id,
                    ),
                ),
            )
        )
        order += 1

        # 3. sleep for `wait_ms` before verifying.
        if wait_ms > 0:
            commands.append(
                _wrap(
                    order,
                    description=f"Wait {wait_ms}ms for side effects",
                    cfg=SleepConfigurationCommandDto(duration=wait_ms),
                )
            )
            order += 1

        # 4. For each assert: produce read-source + assert pair.
        for assert_index, assert_spec in enumerate(asserts):
            target = _normalize_token(assert_spec.get("target"))
            if target not in _SUPPORTED_TARGETS:
                raise InvalidTemplateConfigError(
                    f"assert[{assert_index}].target must be one of {sorted(_SUPPORTED_TARGETS)};"
                    f" got '{target}'."
                )
            if target == "none":
                continue

            operator = _normalize_token(assert_spec.get("operator"))
            if operator not in _SUPPORTED_OPERATORS:
                raise InvalidTemplateConfigError(
                    f"assert[{assert_index}].operator must be one of "
                    f"{sorted(_SUPPORTED_OPERATORS)}; got '{operator}'."
                )

            actual_definition_id = f"tpl_sv_actual_{assert_index}"
            actual_name = f"actual_{assert_index}"

            # Read step (receive / query).
            if target == "queue":
                read_queue_id = _require_str(
                    assert_spec.get("queue_id"),
                    f"assert[{assert_index}].queue_id is required when target=queue.",
                )
                commands.append(
                    _wrap(
                        order,
                        description=f"Receive messages from queue '{read_queue_id}' for assert {assert_index}",
                        cfg=ReceiveQueueConfigurationCommandDto(
                            queue_id=read_queue_id,
                            max_messages=1,
                            retry=3,
                            wait_time_seconds=1,
                            target=f"$.local.constants.{actual_name}",
                            resultConstant=ResultConstantDto(
                                definitionId=actual_definition_id,
                                name=actual_name,
                            ),
                        ),
                    )
                )
            else:  # target == "database"
                connection_id = _require_str(
                    assert_spec.get("connection_id"),
                    f"assert[{assert_index}].connection_id is required when target=database.",
                )
                database_query = _require_str(
                    assert_spec.get("database_query"),
                    f"assert[{assert_index}].database_query is required when target=database.",
                )
                commands.append(
                    _wrap(
                        order,
                        description=f"Query database '{connection_id}' for assert {assert_index}",
                        cfg=QueryDatabaseConfigurationCommandDto(
                            connection_id=connection_id,
                            query=database_query,
                            target=f"$.local.constants.{actual_name}",
                            resultConstant=ResultConstantDto(
                                definitionId=actual_definition_id,
                                name=actual_name,
                            ),
                        ),
                    )
                )
            order += 1

            # Assert step.
            command_code = _OPERATOR_TO_COMMAND_CODE[operator]
            assert_cfg_kwargs: dict[str, Any] = {
                "commandCode": command_code,
                "commandType": CommandType.ASSERT.value,
                "actualRef": InputRefDto(
                    kind=InputRefKind.RUNTIME_VALUE.value,
                    definitionId=actual_definition_id,
                ),
            }
            if operator == "equals":
                if "expected" not in assert_spec:
                    raise InvalidTemplateConfigError(
                        f"assert[{assert_index}].expected is required when operator=equals."
                    )
                assert_cfg_kwargs["expected"] = assert_spec.get("expected")

            commands.append(
                _wrap(
                    order,
                    description=f"Assert {operator} on {target} for assert {assert_index}",
                    cfg=AssertConfigurationCommandDto(**assert_cfg_kwargs),
                )
            )
            order += 1

        return commands


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wrap(order: int, *, description: str, cfg) -> CreateSuiteItemCommandDto:
    return CreateSuiteItemCommandDto(order=order, description=description, cfg=cfg)


def _normalize_token(value) -> str:
    return str(value or "").strip().lower()


def _require_str(value, message: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise InvalidTemplateConfigError(message)
    return normalized


def _require_dict(value, message: str) -> dict:
    if not isinstance(value, dict):
        raise InvalidTemplateConfigError(message)
    return value


def _coerce_wait_ms(value, *, default: int) -> int:
    if value is None:
        return default
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidTemplateConfigError("wait_ms must be an integer.") from exc
    if result < 0:
        raise InvalidTemplateConfigError("wait_ms must be greater than or equal to zero.")
    return result


def _coerce_assert_list(value) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InvalidTemplateConfigError("asserts must be a list.")
    out: list[dict] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise InvalidTemplateConfigError(f"asserts[{index}] must be an object.")
        out.append(item)
    return out


# Re-register the real implementation (the skeleton registered at module
# import time was the placeholder; the registry forbids double registration,
# so we replace it explicitly).
template_registry._templates.pop(TemplateKind.SEND_VERIFY.value, None)  # noqa: SLF001
template_registry.register(SendVerifyTemplate())
