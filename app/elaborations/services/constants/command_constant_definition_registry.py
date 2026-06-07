from dataclasses import dataclass, replace
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from _alembic.models.command_constant_definition_entity import (
    CommandConstantDefinitionEntity,
)
from _alembic.models.mock_server_entity import MockServerEntity
from _alembic.models.suite_item_entity import SuiteItemEntity
from elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
    CommandCode,
    ConstantContext,
    ConstantSourceType,
    DeleteConstantConfigurationCommandDto,
    HttpInputNode,
    HttpInputNodeKind,
    InitConstantConfigurationCommandDto,
    ReadApiConfigurationCommandDto,
    RunSuiteConfigurationCommandDto,
    WriteApiConfigurationCommandDto,
    convert_to_config_command_type,
)
from elaborations.models.dtos.test_suite_dto import CreateTestSuiteDto
from elaborations.services.alembic.command_constant_definition_service import (
    CommandConstantDefinitionService,
)
from elaborations.services.alembic.suite_item_command_service import (
    SuiteItemOperationService,
)
from elaborations.services.alembic.suite_item_service import SuiteItemService
from elaborations.services.operations.command_scope import (
    SCOPE_HOOK_AFTER_ALL,
    SCOPE_HOOK_AFTER_EACH,
    SCOPE_HOOK_BEFORE_ALL,
    SCOPE_HOOK_BEFORE_EACH,
    SCOPE_MOCK_POST_RESPONSE,
    SCOPE_MOCK_PRE_RESPONSE,
    SCOPE_TEST,
)
from elaborations.services.suite_source_registry import validate_suite_sources_graph
from mock_servers.models.dtos.mock_server_dto import CreateMockServerDto, UpdateMockServerDto
from mock_servers.services.alembic.mock_server_api_service import MockServerApiService
from mock_servers.services.alembic.mock_server_queue_service import MockServerQueueService
from mock_servers.services.alembic.ms_api_command_service import MsApiOperationService
from mock_servers.services.alembic.ms_queue_command_service import MsQueueOperationService


SUITE_SECTION_TEST = "test"
SUITE_SECTION_BEFORE_ALL = "beforeAll"
SUITE_SECTION_BEFORE_EACH = "beforeEach"
SUITE_SECTION_AFTER_EACH = "afterEach"
SUITE_SECTION_AFTER_ALL = "afterAll"
MOCK_SECTION_PRE_RESPONSE = "mock.preResponse"
MOCK_SECTION_POST_RESPONSE = "mock.postResponse"
MOCK_SECTION_QUEUE = "mock.queue"

OWNER_SUITE = "suite"
OWNER_MOCK_API_PRE = "mock_api_pre"
OWNER_MOCK_API_POST = "mock_api_post"
OWNER_MOCK_QUEUE = "mock_queue"

_TYPE_COMPATIBILITY: dict[str, set[str]] = {
    CommandCode.SEND_MESSAGE_QUEUE.value: {
        ConstantSourceType.RAW.value,
        ConstantSourceType.JSON.value,
        ConstantSourceType.JSON_ARRAY.value,
        ConstantSourceType.DATASET.value,
    },
    CommandCode.SAVE_TABLE.value: {
        ConstantSourceType.JSON.value,
        ConstantSourceType.JSON_ARRAY.value,
        ConstantSourceType.DATASET.value,
    },
    CommandCode.EXPORT_DATASET.value: {
        ConstantSourceType.JSON.value,
        ConstantSourceType.JSON_ARRAY.value,
        ConstantSourceType.DATASET.value,
    },
    CommandCode.JSON_EQUALS.value: {
        ConstantSourceType.JSON.value,
        ConstantSourceType.RAW.value,
    },
    CommandCode.JSON_EMPTY.value: {
        ConstantSourceType.JSON.value,
        ConstantSourceType.RAW.value,
    },
    CommandCode.JSON_NOT_EMPTY.value: {
        ConstantSourceType.JSON.value,
        ConstantSourceType.RAW.value,
    },
    CommandCode.JSON_CONTAINS.value: {
        ConstantSourceType.JSON.value,
        ConstantSourceType.RAW.value,
    },
    CommandCode.JSON_ARRAY_EQUALS.value: {
        ConstantSourceType.JSON_ARRAY.value,
    },
    CommandCode.JSON_ARRAY_EMPTY.value: {
        ConstantSourceType.JSON_ARRAY.value,
    },
    CommandCode.JSON_ARRAY_NOT_EMPTY.value: {
        ConstantSourceType.JSON_ARRAY.value,
    },
    CommandCode.JSON_ARRAY_CONTAINS.value: {
        ConstantSourceType.JSON_ARRAY.value,
    },
}

_READABLE_SCOPES: dict[str, set[str]] = {
    SUITE_SECTION_BEFORE_ALL: {ConstantContext.RUN_ENVELOPE.value, ConstantContext.RESULT.value},
    SUITE_SECTION_BEFORE_EACH: {
        ConstantContext.RUN_ENVELOPE.value,
        ConstantContext.GLOBAL.value,
        ConstantContext.RESULT.value,
    },
    SUITE_SECTION_TEST: {
        ConstantContext.RUN_ENVELOPE.value,
        ConstantContext.GLOBAL.value,
        ConstantContext.LOCAL.value,
        ConstantContext.RESULT.value,
    },
    SUITE_SECTION_AFTER_EACH: {
        ConstantContext.RUN_ENVELOPE.value,
        ConstantContext.GLOBAL.value,
        ConstantContext.LOCAL.value,
        ConstantContext.RESULT.value,
    },
    SUITE_SECTION_AFTER_ALL: {
        ConstantContext.RUN_ENVELOPE.value,
        ConstantContext.GLOBAL.value,
        ConstantContext.RESULT.value,
    },
    MOCK_SECTION_PRE_RESPONSE: {
        ConstantContext.RUN_ENVELOPE.value,
        ConstantContext.RESULT.value,
    },
    MOCK_SECTION_POST_RESPONSE: {
        ConstantContext.RUN_ENVELOPE.value,
        ConstantContext.RESULT.value,
    },
    MOCK_SECTION_QUEUE: {
        ConstantContext.RUN_ENVELOPE.value,
        ConstantContext.RESULT.value,
    },
}

_WRITABLE_SCOPES: dict[str, set[str]] = {
    SUITE_SECTION_BEFORE_ALL: {
        ConstantContext.GLOBAL.value,
        ConstantContext.RESULT.value,
    },
    SUITE_SECTION_BEFORE_EACH: {
        ConstantContext.LOCAL.value,
        ConstantContext.RESULT.value,
    },
    SUITE_SECTION_TEST: {
        ConstantContext.LOCAL.value,
        ConstantContext.RESULT.value,
    },
    SUITE_SECTION_AFTER_EACH: {
        ConstantContext.LOCAL.value,
        ConstantContext.RESULT.value,
    },
    SUITE_SECTION_AFTER_ALL: {
        ConstantContext.GLOBAL.value,
        ConstantContext.RESULT.value,
    },
    MOCK_SECTION_PRE_RESPONSE: {
        ConstantContext.RUN_ENVELOPE.value,
        ConstantContext.RESULT.value,
    },
    MOCK_SECTION_POST_RESPONSE: {
        ConstantContext.RESULT.value,
    },
    MOCK_SECTION_QUEUE: {
        ConstantContext.RESULT.value,
    },
}

_SECTION_SCOPE_TO_EXECUTION_SCOPE: dict[str, str] = {
    SUITE_SECTION_BEFORE_ALL: SCOPE_HOOK_BEFORE_ALL,
    SUITE_SECTION_BEFORE_EACH: SCOPE_HOOK_BEFORE_EACH,
    SUITE_SECTION_TEST: SCOPE_TEST,
    SUITE_SECTION_AFTER_EACH: SCOPE_HOOK_AFTER_EACH,
    SUITE_SECTION_AFTER_ALL: SCOPE_HOOK_AFTER_ALL,
    MOCK_SECTION_PRE_RESPONSE: SCOPE_MOCK_PRE_RESPONSE,
    MOCK_SECTION_POST_RESPONSE: SCOPE_MOCK_POST_RESPONSE,
}

_RESULT_TYPE_BY_COMMAND: dict[str, str] = {
    CommandCode.READ_API.value: ConstantSourceType.JSON.value,
    CommandCode.WRITE_API.value: ConstantSourceType.JSON.value,
    CommandCode.SEND_MESSAGE_QUEUE.value: ConstantSourceType.JSON.value,
    CommandCode.SAVE_TABLE.value: ConstantSourceType.JSON.value,
    CommandCode.EXPORT_DATASET.value: ConstantSourceType.JSON.value,
    CommandCode.RUN_SUITE.value: ConstantSourceType.JSON.value,
    CommandCode.SLEEP.value: ConstantSourceType.JSON.value,
    CommandCode.JSON_EQUALS.value: ConstantSourceType.JSON.value,
    CommandCode.JSON_EMPTY.value: ConstantSourceType.JSON.value,
    CommandCode.JSON_NOT_EMPTY.value: ConstantSourceType.JSON.value,
    CommandCode.JSON_CONTAINS.value: ConstantSourceType.JSON.value,
    CommandCode.JSON_ARRAY_EQUALS.value: ConstantSourceType.JSON.value,
    CommandCode.JSON_ARRAY_EMPTY.value: ConstantSourceType.JSON.value,
    CommandCode.JSON_ARRAY_NOT_EMPTY.value: ConstantSourceType.JSON.value,
    CommandCode.JSON_ARRAY_CONTAINS.value: ConstantSourceType.JSON.value,
}


@dataclass
class CommandInput:
    command_id: str
    command_order: int
    cfg: dict[str, Any]


@dataclass
class PlannedDefinition:
    definition_id: str
    command_id: str
    command_order: int
    section_type: str
    name: str
    context_scope: str
    value_type: str
    deleted_at_order: int | None = None


def _new_id() -> str:
    return str(uuid4())


def ensure_command_id(raw_command: dict[str, Any]) -> str:
    command_id = str(raw_command.get("id") or "").strip()
    if command_id:
        return command_id
    command_id = _new_id()
    raw_command["id"] = command_id
    return command_id


def _cfg_payload(raw_cfg: Any) -> dict[str, Any]:
    if hasattr(raw_cfg, "model_dump"):
        return raw_cfg.model_dump()
    return raw_cfg if isinstance(raw_cfg, dict) else {}


def _command_input(raw_command: dict[str, Any], default_order: int) -> CommandInput:
    cfg = _cfg_payload(raw_command.get("cfg") or raw_command.get("configuration_json"))
    return CommandInput(
        command_id=ensure_command_id(raw_command),
        command_order=int(raw_command.get("order") or default_order),
        cfg=cfg,
    )


def _clone_visible_map(source: dict[str, PlannedDefinition]) -> dict[str, PlannedDefinition]:
    return {key: replace(value) for key, value in source.items()}


def _carry_over_visible_map(source: dict[str, PlannedDefinition]) -> dict[str, PlannedDefinition]:
    carried: dict[str, PlannedDefinition] = {}
    for key, value in source.items():
        if value.deleted_at_order is not None:
            continue
        carried[key] = replace(value, command_order=0)
    return carried


def _active_definitions(
    definitions: dict[str, PlannedDefinition],
    *,
    readable_scopes: set[str],
    command_order: int,
) -> dict[str, PlannedDefinition]:
    result: dict[str, PlannedDefinition] = {}
    for definition_id, definition in definitions.items():
        if definition.context_scope not in readable_scopes:
            continue
        if int(definition.command_order) >= int(command_order):
            continue
        if definition.deleted_at_order is not None and int(definition.deleted_at_order) <= int(command_order):
            continue
        result[definition_id] = definition
    return result


def _validate_duplicate_name(
    active_definitions: dict[str, PlannedDefinition],
    *,
    name: str,
    context_scope: str,
):
    for definition in active_definitions.values():
        if definition.name == name and definition.context_scope == context_scope:
            raise ValueError(
                f"Constant '{name}' is already defined in scope '{context_scope}'."
            )


def _extract_http_input_node_refs(node: object, role: str) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if isinstance(node, HttpInputNode):
        if node.kind == HttpInputNodeKind.RUNTIME_VALUE.value and node.definitionId:
            refs.append((role, node.definitionId))
        return refs
    if isinstance(node, dict):
        for item in node.values():
            refs.extend(_extract_http_input_node_refs(item, role))
    elif isinstance(node, list):
        for item in node:
            refs.extend(_extract_http_input_node_refs(item, role))
    return refs


def _extract_http_auth_refs(authorization: dict | None) -> list[tuple[str, str]]:
    if not authorization or not isinstance(authorization, dict):
        return []
    refs: list[tuple[str, str]] = []
    for key, value in authorization.items():
        if key == "type":
            continue
        refs.extend(_extract_http_input_node_refs(value, "source"))
    return refs


def _definition_refs(cfg) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if isinstance(cfg, DeleteConstantConfigurationCommandDto):
        refs.append(("target", cfg.targetRuntimeValueRef.definitionId))
        return refs
    input_ref = getattr(cfg, "inputRef", None)
    if input_ref is not None and str(getattr(input_ref, "kind", "")) == "runtimeValue":
        refs.append(("source", input_ref.definitionId))
    actual_ref = getattr(cfg, "actualRef", None)
    if actual_ref is not None and str(getattr(actual_ref, "kind", "")) == "runtimeValue":
        refs.append(("actual", actual_ref.definitionId))
    expected_ref = getattr(cfg, "expectedRef", None)
    if expected_ref is not None and str(getattr(expected_ref, "kind", "")) == "runtimeValue":
        refs.append(("expected", expected_ref.definitionId))
    if isinstance(cfg, RunSuiteConfigurationCommandDto):
        refs.extend(("constant", item.definitionId) for item in cfg.runtimeValueRefs or [])
    if isinstance(cfg, (ReadApiConfigurationCommandDto, WriteApiConfigurationCommandDto)):
        for field_name in ("queryParams", "headers", "pathParams"):
            field_value = getattr(cfg, field_name, None)
            if isinstance(field_value, dict):
                for item in field_value.values():
                    refs.extend(_extract_http_input_node_refs(item, "source"))
        refs.extend(_extract_http_auth_refs(getattr(cfg, "authorization", None)))
        if isinstance(cfg, WriteApiConfigurationCommandDto) and cfg.body is not None:
            refs.extend(_extract_http_input_node_refs(cfg.body, "source"))
    return refs


def _validate_form_urlencoded_body_refs(
    cfg: WriteApiConfigurationCommandDto,
    *,
    active_definitions: dict[str, PlannedDefinition],
) -> None:
    if str(getattr(cfg, "bodyType", "") or "").strip() != "formUrlEncoded":
        return
    body = getattr(cfg, "body", None)
    if not isinstance(body, dict):
        return

    for field_name, node in body.items():
        if not isinstance(node, HttpInputNode):
            continue
        if node.kind == HttpInputNodeKind.SOURCE.value:
            raise ValueError(
                f"Datasource values are not supported for formUrlEncoded field '{field_name}'."
            )
        if node.kind != HttpInputNodeKind.RUNTIME_VALUE.value:
            continue
        definition = active_definitions.get(str(node.definitionId or "").strip())
        if definition is None:
            continue
        if definition.value_type in {
            ConstantSourceType.DATASET.value,
            ConstantSourceType.JSON_ARRAY.value,
        }:
            raise ValueError(
                f"Constant '{definition.name}' has incompatible type '{definition.value_type}' for formUrlEncoded field '{field_name}'."
            )


def _validate_ref_visibility(
    cfg,
    *,
    section_type: str,
    command_order: int,
    definitions: dict[str, PlannedDefinition],
):
    active_definitions = _active_definitions(
        definitions,
        readable_scopes=_READABLE_SCOPES.get(section_type, set()),
        command_order=command_order,
    )
    for ref_role, definition_id in _definition_refs(cfg):
        definition = active_definitions.get(definition_id)
        if definition is None:
            raise ValueError(
                f"Constant reference '{definition_id}' is not visible for command '{cfg.commandCode}'."
            )
        compatible_types = _TYPE_COMPATIBILITY.get(cfg.commandCode)
        if compatible_types and definition.value_type not in compatible_types:
            raise ValueError(
                f"Constant '{definition.name}' has incompatible type '{definition.value_type}' for command '{cfg.commandCode}'."
            )
        if ref_role == "target" and definition.context_scope not in _WRITABLE_SCOPES.get(section_type, set()):
            raise ValueError(
                f"Constant '{definition.name}' in scope '{definition.context_scope}' cannot be deleted in section '{section_type}'."
            )
    if isinstance(cfg, WriteApiConfigurationCommandDto):
        _validate_form_urlencoded_body_refs(cfg, active_definitions=active_definitions)


def _planned_declarations(cfg, *, command_id: str, command_order: int, section_type: str) -> list[PlannedDefinition]:
    declarations: list[PlannedDefinition] = []
    if isinstance(cfg, InitConstantConfigurationCommandDto):
        declarations.append(
            PlannedDefinition(
                definition_id=cfg.definitionId,
                command_id=command_id,
                command_order=command_order,
                section_type=section_type,
                name=cfg.name or "",
                context_scope=cfg.context or ConstantContext.LOCAL.value,
                value_type=cfg.valueType or ConstantSourceType.VALUE.value,
            )
        )
    result_constant = getattr(cfg, "resultConstant", None)
    if result_constant is not None:
        declarations.append(
            PlannedDefinition(
                definition_id=result_constant.definitionId,
                command_id=command_id,
                command_order=command_order,
                section_type=section_type,
                name=result_constant.name,
                context_scope=ConstantContext.RESULT.value,
                value_type=(
                    result_constant.valueType
                    or _RESULT_TYPE_BY_COMMAND.get(cfg.commandCode, ConstantSourceType.JSON.value)
                ),
            )
        )
    return declarations


def _validate_declarations(
    cfg,
    *,
    section_type: str,
    command_order: int,
    definitions: dict[str, PlannedDefinition],
    command_id: str,
) -> list[PlannedDefinition]:
    declarations = _planned_declarations(
        cfg,
        command_id=command_id,
        command_order=command_order,
        section_type=section_type,
    )
    active_definitions = _active_definitions(
        definitions,
        readable_scopes={
            ConstantContext.RUN_ENVELOPE.value,
            ConstantContext.GLOBAL.value,
            ConstantContext.LOCAL.value,
            ConstantContext.RESULT.value,
        },
        command_order=command_order + 1,
    )
    for declaration in declarations:
        if declaration.context_scope not in _WRITABLE_SCOPES.get(section_type, set()):
            raise ValueError(
                f"Scope '{declaration.context_scope}' is not writable in section '{section_type}'."
            )
        _validate_duplicate_name(
            active_definitions,
            name=declaration.name,
            context_scope=declaration.context_scope,
        )
        active_definitions[declaration.definition_id] = declaration
    return declarations


def plan_definitions_for_commands(
    raw_commands: list[dict[str, Any]],
    *,
    section_type: str,
    initial_visible: dict[str, PlannedDefinition] | None = None,
) -> tuple[list[PlannedDefinition], dict[str, PlannedDefinition]]:
    definitions = _carry_over_visible_map(initial_visible or {})
    planned_definitions: list[PlannedDefinition] = []
    commands = [
        _command_input(raw_command, default_order=index)
        for index, raw_command in enumerate(raw_commands or [], start=1)
    ]
    commands.sort(key=lambda item: (item.command_order, item.command_id))

    for command in commands:
        cfg = convert_to_config_command_type(command.cfg)
        _validate_ref_visibility(
            cfg,
            section_type=section_type,
            command_order=command.command_order,
            definitions=definitions,
        )
        if isinstance(cfg, DeleteConstantConfigurationCommandDto):
            target_id = cfg.targetRuntimeValueRef.definitionId
            existing = definitions.get(target_id)
            if existing is None:
                raise ValueError(
                    f"Constant reference '{target_id}' is not visible for deleteVariable."
                )
            definitions[target_id] = replace(existing, deleted_at_order=command.command_order)
            continue
        new_definitions = _validate_declarations(
            cfg,
            section_type=section_type,
            command_order=command.command_order,
            definitions=definitions,
            command_id=command.command_id,
        )
        for definition in new_definitions:
            definitions[definition.definition_id] = definition
            planned_definitions.append(definition)
    return planned_definitions, definitions


def _suite_item_commands(item) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for index, command in enumerate(item.commands or [], start=1):
        raw_cfg = _cfg_payload(getattr(command, "cfg", None))
        commands.append(
            {
                "id": raw_cfg.get("commandId") or command.order or _new_id(),
                "order": int(command.order or index),
                "cfg": raw_cfg,
            }
        )
    return commands


def validate_suite_constant_graph(dto: CreateTestSuiteDto) -> None:
    validate_suite_sources_graph(dto)
    hooks_by_phase = {
        str(item.hook_phase or "").strip(): item
        for item in dto.hooks or []
    }
    before_all_defs: dict[str, PlannedDefinition] = {}
    before_each_defs: dict[str, PlannedDefinition] = {}
    after_each_initial: dict[str, PlannedDefinition] = {}
    after_all_initial: dict[str, PlannedDefinition] = {}

    before_all = hooks_by_phase.get("before-all")
    if before_all is not None:
        _, before_all_defs = plan_definitions_for_commands(
            _suite_item_commands(before_all),
            section_type=SUITE_SECTION_BEFORE_ALL,
            initial_visible={},
        )
    before_each_defs = _clone_visible_map(before_all_defs)

    before_each = hooks_by_phase.get("before-each")
    if before_each is not None:
        _, before_each_defs = plan_definitions_for_commands(
            _suite_item_commands(before_each),
            section_type=SUITE_SECTION_BEFORE_EACH,
            initial_visible=before_all_defs,
        )

    after_each_initial = _clone_visible_map(before_each_defs)
    after_all_initial = _clone_visible_map(before_all_defs)

    for test_item in dto.tests or []:
        plan_definitions_for_commands(
            _suite_item_commands(test_item),
            section_type=SUITE_SECTION_TEST,
            initial_visible=before_each_defs,
        )

    after_each = hooks_by_phase.get("after-each")
    if after_each is not None:
        plan_definitions_for_commands(
            _suite_item_commands(after_each),
            section_type=SUITE_SECTION_AFTER_EACH,
            initial_visible=after_each_initial,
        )

    after_all = hooks_by_phase.get("after-all")
    if after_all is not None:
        plan_definitions_for_commands(
            _suite_item_commands(after_all),
            section_type=SUITE_SECTION_AFTER_ALL,
            initial_visible=after_all_initial,
        )


def validate_mock_server_constant_graph(dto: CreateMockServerDto | UpdateMockServerDto) -> None:
    for api_entry in dto.apis or []:
        api_cfg = _cfg_payload(api_entry.cfg)
        pre_commands = api_cfg.get("pre_response_commands") if isinstance(api_cfg.get("pre_response_commands"), list) else []
        plan_definitions_for_commands(
            [dict(item) for item in pre_commands if isinstance(item, dict)],
            section_type=MOCK_SECTION_PRE_RESPONSE,
            initial_visible={},
        )
        plan_definitions_for_commands(
            [
                {
                    "id": _new_id(),
                    "order": int(command.order or index),
                    "cfg": _cfg_payload(command.cfg),
                }
                for index, command in enumerate(api_entry.commands or [], start=1)
            ],
            section_type=MOCK_SECTION_POST_RESPONSE,
            initial_visible={},
        )

    for queue_entry in dto.queues or []:
        plan_definitions_for_commands(
            [
                {
                    "id": _new_id(),
                    "order": int(command.order or index),
                    "cfg": _cfg_payload(command.cfg),
                }
                for index, command in enumerate(queue_entry.commands or [], start=1)
            ],
            section_type=MOCK_SECTION_QUEUE,
            initial_visible={},
        )


def _definition_entity(
    definition: PlannedDefinition,
    *,
    owner_type: str,
    suite_id: str | None = None,
    suite_item_id: str | None = None,
    mock_server_api_id: str | None = None,
    mock_server_queue_id: str | None = None,
) -> CommandConstantDefinitionEntity:
    entity = CommandConstantDefinitionEntity()
    entity.id = definition.definition_id
    entity.owner_type = owner_type
    entity.suite_id = suite_id
    entity.suite_item_id = suite_item_id
    entity.mock_server_api_id = mock_server_api_id
    entity.mock_server_queue_id = mock_server_queue_id
    entity.command_id = definition.command_id
    entity.command_order = definition.command_order
    entity.section_type = definition.section_type
    entity.name = definition.name
    entity.context_scope = definition.context_scope
    entity.value_type = definition.value_type
    entity.declared_at_order = definition.command_order
    entity.deleted_at_order = definition.deleted_at_order
    return entity


def _persist_definition_entities(
    session: Session,
    entities: list[CommandConstantDefinitionEntity],
) -> None:
    if not entities:
        return
    CommandConstantDefinitionService().inserts(session, entities)


def rebuild_suite_constant_definitions(session: Session, suite_id: str) -> None:
    service = CommandConstantDefinitionService()
    service.delete_by_suite_id(session, suite_id)
    items = SuiteItemService().get_all_by_suite_id(session, suite_id)
    hooks_by_phase: dict[str, SuiteItemEntity] = {}
    tests: list[SuiteItemEntity] = []
    for item in items:
        hook_phase = str(item.hook_phase or "").strip()
        if hook_phase:
            hooks_by_phase[hook_phase] = item
        else:
            tests.append(item)

    persisted_entities: list[CommandConstantDefinitionEntity] = []
    visible_before_all: dict[str, PlannedDefinition] = {}
    visible_before_each: dict[str, PlannedDefinition] = {}

    def _commands_for_item(item: SuiteItemEntity) -> list[dict[str, Any]]:
        operations = SuiteItemOperationService().get_all_by_suite_item_id(session, item.id)
        return [
            {
                "id": str(operation.id or ""),
                "order": int(operation.order or index),
                "cfg": operation.configuration_json if isinstance(operation.configuration_json, dict) else {},
            }
            for index, operation in enumerate(operations, start=1)
        ]

    before_all = hooks_by_phase.get("before-all")
    if before_all is not None:
        definitions, visible_before_all = plan_definitions_for_commands(
            _commands_for_item(before_all),
            section_type=SUITE_SECTION_BEFORE_ALL,
            initial_visible={},
        )
        persisted_entities.extend(
            _definition_entity(
                definition,
                owner_type=OWNER_SUITE,
                suite_id=suite_id,
                suite_item_id=before_all.id,
            )
            for definition in definitions
        )
    visible_before_each = _clone_visible_map(visible_before_all)

    before_each = hooks_by_phase.get("before-each")
    if before_each is not None:
        definitions, visible_before_each = plan_definitions_for_commands(
            _commands_for_item(before_each),
            section_type=SUITE_SECTION_BEFORE_EACH,
            initial_visible=visible_before_all,
        )
        persisted_entities.extend(
            _definition_entity(
                definition,
                owner_type=OWNER_SUITE,
                suite_id=suite_id,
                suite_item_id=before_each.id,
            )
            for definition in definitions
        )

    for test_item in tests:
        definitions, _ = plan_definitions_for_commands(
            _commands_for_item(test_item),
            section_type=SUITE_SECTION_TEST,
            initial_visible=visible_before_each,
        )
        persisted_entities.extend(
            _definition_entity(
                definition,
                owner_type=OWNER_SUITE,
                suite_id=suite_id,
                suite_item_id=test_item.id,
            )
            for definition in definitions
        )

    after_each = hooks_by_phase.get("after-each")
    if after_each is not None:
        definitions, _ = plan_definitions_for_commands(
            _commands_for_item(after_each),
            section_type=SUITE_SECTION_AFTER_EACH,
            initial_visible=visible_before_each,
        )
        persisted_entities.extend(
            _definition_entity(
                definition,
                owner_type=OWNER_SUITE,
                suite_id=suite_id,
                suite_item_id=after_each.id,
            )
            for definition in definitions
        )

    after_all = hooks_by_phase.get("after-all")
    if after_all is not None:
        definitions, _ = plan_definitions_for_commands(
            _commands_for_item(after_all),
            section_type=SUITE_SECTION_AFTER_ALL,
            initial_visible=visible_before_all,
        )
        persisted_entities.extend(
            _definition_entity(
                definition,
                owner_type=OWNER_SUITE,
                suite_id=suite_id,
                suite_item_id=after_all.id,
            )
            for definition in definitions
        )

    _persist_definition_entities(session, persisted_entities)


def rebuild_mock_constant_definitions(session: Session, server_id: str) -> None:
    definition_service = CommandConstantDefinitionService()
    api_service = MockServerApiService()
    queue_service = MockServerQueueService()
    api_command_service = MsApiOperationService()
    queue_command_service = MsQueueOperationService()

    apis = api_service.get_all_by_server_id(session, server_id)
    queues = queue_service.get_all_by_server_id(session, server_id)
    persisted_entities: list[CommandConstantDefinitionEntity] = []

    for api in apis:
        definition_service.delete_by_mock_server_api_id(session, api.id)
        api_cfg = api.configuration_json if isinstance(api.configuration_json, dict) else {}
        pre_commands = api_cfg.get("pre_response_commands") if isinstance(api_cfg.get("pre_response_commands"), list) else []
        normalized_pre_commands: list[dict[str, Any]] = []
        for index, command in enumerate(pre_commands, start=1):
            if not isinstance(command, dict):
                continue
            command_id = ensure_command_id(command)
            normalized_pre_commands.append(
                {
                    "id": command_id,
                    "order": int(command.get("order") or index),
                    "cfg": _cfg_payload(command.get("cfg") or command.get("configuration_json") or command),
                }
            )
        api.configuration_json = api_cfg
        pre_definitions, _ = plan_definitions_for_commands(
            normalized_pre_commands,
            section_type=MOCK_SECTION_PRE_RESPONSE,
            initial_visible={},
        )
        persisted_entities.extend(
            _definition_entity(
                definition,
                owner_type=OWNER_MOCK_API_PRE,
                mock_server_api_id=api.id,
            )
            for definition in pre_definitions
        )

        post_commands = api_command_service.get_all_by_api_id(session, api.id)
        post_definitions, _ = plan_definitions_for_commands(
            [
                {
                    "id": str(command.id or ""),
                    "order": int(command.order or index),
                    "cfg": command.configuration_json if isinstance(command.configuration_json, dict) else {},
                }
                for index, command in enumerate(post_commands, start=1)
            ],
            section_type=MOCK_SECTION_POST_RESPONSE,
            initial_visible={},
        )
        persisted_entities.extend(
            _definition_entity(
                definition,
                owner_type=OWNER_MOCK_API_POST,
                mock_server_api_id=api.id,
            )
            for definition in post_definitions
        )

    for queue in queues:
        definition_service.delete_by_mock_server_queue_id(session, queue.id)
        queue_definitions, _ = plan_definitions_for_commands(
            [
                {
                    "id": str(command.id or ""),
                    "order": int(command.order or index),
                    "cfg": command.configuration_json if isinstance(command.configuration_json, dict) else {},
                }
                for index, command in enumerate(
                    queue_command_service.get_all_by_queue_binding_id(session, queue.id),
                    start=1,
                )
            ],
            section_type=MOCK_SECTION_QUEUE,
            initial_visible={},
        )
        persisted_entities.extend(
            _definition_entity(
                definition,
                owner_type=OWNER_MOCK_QUEUE,
                mock_server_queue_id=queue.id,
            )
            for definition in queue_definitions
        )

    _persist_definition_entities(session, persisted_entities)


def resolve_definition_path(session: Session, definition_id: str) -> tuple[CommandConstantDefinitionEntity, str]:
    definition = CommandConstantDefinitionService().get_by_id(session, definition_id)
    if definition is None:
        raise ValueError(f"Constant definition '{definition_id}' not found.")
    return definition, f"$.{definition.context_scope}.constants.{definition.name}"


def resolve_execution_scope_for_section(section_type: str) -> str | None:
    return _SECTION_SCOPE_TO_EXECUTION_SCOPE.get(section_type)
