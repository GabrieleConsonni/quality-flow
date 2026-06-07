"""`mock_assert` template generator.

Produces the canonical "Mock & Assert" chain of suite_item_commands:

    sleep(wait_ms)
    for each assert:
        receiveQueue(target.queue_id)  OR  queryDatabase(target.connection_id, target.database_query)
        assertX(actualRef = last receive/query, expected or expectedRef)

This template assumes the trigger that caused the side effects is fired
externally to the suite (typically by a mock server). `trigger_hint` is
info-only metadata to help operators understand what to do.

Phase 2 scope constraints mirror `send_verify`:
* `operator` only supports `equals` and `exists`.
* `target` ∈ {`queue`, `database`} — at least one assert is required.
"""

from __future__ import annotations

from typing import Any

from elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
    CommandCode,
    CommandType,
    InputRefDto,
    InputRefKind,
    QueryDatabaseConfigurationCommandDto,
    ReceiveQueueConfigurationCommandDto,
    ResultConstantDto,
    SleepConfigurationCommandDto,
)
from elaborations.models.dtos.test_suite_dto import CreateSuiteItemCommandDto
from elaborations.models.enums.template_kind import TemplateKind
from templating.base import InvalidTemplateConfigError, TemplateMeta
from templating.template_registry import template_registry


_SUPPORTED_TARGETS = {"queue", "database"}
_SUPPORTED_OPERATORS = {"equals", "exists"}

_OPERATOR_TO_COMMAND_CODE = {
    "equals": CommandCode.JSON_EQUALS.value,
    "exists": CommandCode.JSON_NOT_EMPTY.value,
}


class MockAssertTemplate:
    meta = TemplateMeta(
        kind=TemplateKind.MOCK_ASSERT.value,
        name="Mock & Assert",
        description=(
            "Verify the side effects on a queue or a database after an "
            "external system has triggered the mock."
        ),
        config_schema_summary={
            "fields": [
                {
                    "name": "trigger_hint",
                    "type": "string",
                    "required": False,
                    "description": "Info-only helper for the operator; not used at runtime.",
                },
                {"name": "wait_ms", "type": "integer", "required": False, "default": 1000},
                {
                    "name": "asserts",
                    "type": "array<object>",
                    "required": True,
                    "minItems": 1,
                    "shape": {
                        "target": "queue | database",
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
        wait_ms = _coerce_wait_ms(config.get("wait_ms"), default=1000)
        asserts = _coerce_assert_list(config.get("asserts"))
        if not asserts:
            raise InvalidTemplateConfigError(
                "mock_assert requires at least one assert."
            )

        order = 0
        commands: list[CreateSuiteItemCommandDto] = []

        # 1. sleep before checking the side effects.
        if wait_ms > 0:
            commands.append(
                _wrap(
                    order,
                    description=f"Wait {wait_ms}ms for the external trigger to land",
                    cfg=SleepConfigurationCommandDto(duration=wait_ms),
                )
            )
            order += 1

        # 2. per assert: read source + assert
        for assert_index, assert_spec in enumerate(asserts):
            target = _normalize_token(assert_spec.get("target"))
            if target not in _SUPPORTED_TARGETS:
                raise InvalidTemplateConfigError(
                    f"assert[{assert_index}].target must be one of "
                    f"{sorted(_SUPPORTED_TARGETS)}; got '{target}'."
                )

            operator = _normalize_token(assert_spec.get("operator"))
            if operator not in _SUPPORTED_OPERATORS:
                raise InvalidTemplateConfigError(
                    f"assert[{assert_index}].operator must be one of "
                    f"{sorted(_SUPPORTED_OPERATORS)}; got '{operator}'."
                )

            actual_definition_id = f"tpl_ma_actual_{assert_index}"
            actual_name = f"actual_{assert_index}"

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
# Helpers (kept local to the module — mirror the ones in send_verify.py)
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


template_registry._templates.pop(TemplateKind.MOCK_ASSERT.value, None)  # noqa: SLF001
template_registry.register(MockAssertTemplate())
