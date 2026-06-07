from fastapi import APIRouter

from _alembic.models.suite_item_entity import SuiteItemEntity
from _alembic.models.suite_item_command_entity import SuiteItemOperationEntity
from _alembic.models.test_suite_entity import TestSuiteEntity
from _alembic.services.session_context_manager import managed_session
from data_sources.services.dataset_parameter_resolver import DatasetParameterResolver
from data_sources.services.dataset_query_service import DatasetQueryService
from elaborations.models.dtos.send_message_template_preview_dto import (
    PreviewSendMessageTemplateRowsDto,
)
from elaborations.models.dtos.test_suite_dto import (
    CreateSuiteItemDto,
    CreateSuiteItemCommandDto,
    PreviewSuiteSourceDto,
    CreateTestSuiteDto,
    TemplatePreviewDto,
    UpdateTestSuiteDto,
)
from elaborations.models.enums.hook_phase import HookPhase
from elaborations.models.enums.on_failure import OnFailure
from elaborations.models.enums.suite_item_kind import SuiteItemKind
from elaborations.models.enums.suite_item_role import SuiteItemRole
from elaborations.models.enums.template_kind import TemplateKind
from templating import (
    InvalidTemplateConfigError,
    UnknownTemplateError,
    template_registry,
)
from elaborations.services.alembic.suite_item_command_service import (
    SuiteItemOperationService,
)
from elaborations.services.alembic.suite_item_service import SuiteItemService
from elaborations.services.alembic.test_suite_service import TestSuiteService
from elaborations.services.constants.command_constant_definition_registry import (
    rebuild_suite_constant_definitions,
    validate_suite_constant_graph,
)
from elaborations.services.operations.send_message_template_service import (
    preview_send_message_template_rows,
)
from elaborations.services.test_suites.test_suite_executor_service import (
    execute_test_by_id,
    execute_test_suite_by_id,
)
from exceptions.app_exception import QualityFlowAppException
from json_utils.services.alembic.json_files_service import JsonFilesService

router = APIRouter(prefix="/elaborations")


def _normalize_on_failure(value: str | None) -> str:
    normalized = str(value or OnFailure.ABORT.value).strip().upper()
    if normalized not in {OnFailure.ABORT.value, OnFailure.CONTINUE.value}:
        return OnFailure.ABORT.value
    return normalized


def _build_suite_item_command_entity(dto: CreateSuiteItemCommandDto) -> SuiteItemOperationEntity:
    entity = SuiteItemOperationEntity()
    entity.order = dto.order
    dto_cfg = dto.cfg.model_dump() if dto.cfg else None
    dto_type = str((dto.cfg.commandCode if dto.cfg else None) or "").strip()
    dto_family = str((dto.cfg.commandType if dto.cfg else None) or "").strip()
    entity.description = str(dto.description or "")
    entity.operation_type = dto_type
    if hasattr(entity, "command_code"):
        entity.command_code = dto_type
    if hasattr(entity, "command_type"):
        entity.command_type = dto_family
    entity.configuration_json = dto_cfg if isinstance(dto_cfg, dict) else {}

    if not dto_type:
        raise QualityFlowAppException("Command code is required.")
    return entity


def _build_suite_item_entity(test_suite_id: str, dto: CreateSuiteItemDto, position: int) -> SuiteItemEntity:
    entity = SuiteItemEntity()
    entity.test_suite_id = test_suite_id
    entity.kind = str(dto.kind or SuiteItemKind.TEST.value)
    entity.hook_phase = str(dto.hook_phase or "").strip() or None
    entity.description = str(dto.description or "")
    entity.sources_json = [
        source.model_dump()
        for source in (dto.sources or [])
        if hasattr(source, "model_dump")
    ]
    entity.position = position
    entity.on_failure = _normalize_on_failure(dto.on_failure)
    entity.role = str(dto.role or SuiteItemRole.TEST.value)
    entity.template_kind = str(dto.template_kind or TemplateKind.CUSTOM.value)
    entity.template_config = dto.template_config if isinstance(dto.template_config, dict) else None
    entity.data_driven = bool(dto.data_driven)
    entity.dataset_id = (str(dto.dataset_id).strip() or None) if dto.dataset_id else None
    return entity


def _insert_suite_item_operations(session, suite_item_id: str, commands: list[CreateSuiteItemCommandDto]):
    for operation in commands or []:
        entity = _build_suite_item_command_entity(operation)
        entity.suite_item_id = suite_item_id
        SuiteItemOperationService().insert(session, entity)


def _resolve_template_commands(dto: CreateSuiteItemDto) -> list[CreateSuiteItemCommandDto]:
    """Return the commands list to persist for `dto`.

    When `template_kind` is one supported by the template engine, the
    user-supplied `commands` are ignored and the engine output is used
    instead. When `template_kind == 'custom'` (or anything not registered
    in the engine, e.g. legacy values), the user-supplied `commands` are
    kept verbatim.
    """
    template_kind = str(dto.template_kind or TemplateKind.CUSTOM.value)
    if template_kind == TemplateKind.CUSTOM.value or not template_registry.is_supported(
        template_kind
    ):
        return list(dto.commands or [])

    try:
        return template_registry.generate_commands(template_kind, dto.template_config)
    except UnknownTemplateError as exc:
        raise QualityFlowAppException(str(exc)) from exc
    except InvalidTemplateConfigError as exc:
        raise QualityFlowAppException(str(exc)) from exc


def _insert_suite_items(
    session,
    test_suite_id: str,
    *,
    hooks: list[CreateSuiteItemDto],
    tests: list[CreateSuiteItemDto],
):
    seen_hook_phases: set[str] = set()
    for phase in HookPhase:
        hook = next(
            (
                item
                for item in hooks or []
                if str(item.hook_phase or "").strip().lower() == phase.value
            ),
            None,
        )
        if hook is None:
            continue
        if phase.value in seen_hook_phases:
            raise QualityFlowAppException(f"Duplicate hook for phase '{phase.value}'.")
        seen_hook_phases.add(phase.value)
        suite_item_entity = _build_suite_item_entity(test_suite_id, hook, position=0)
        suite_item_id = SuiteItemService().insert(session, suite_item_entity)
        _insert_suite_item_operations(session, suite_item_id, hook.commands or [])

    for position, test in enumerate(tests or [], start=1):
        suite_item_entity = _build_suite_item_entity(test_suite_id, test, position=position)
        suite_item_id = SuiteItemService().insert(session, suite_item_entity)
        _insert_suite_item_operations(session, suite_item_id, test.commands or [])


def _serialize_operation(operation: SuiteItemOperationEntity) -> dict:
    return {
        "id": operation.id,
        "suite_item_id": operation.suite_item_id,
        "description": operation.description,
        "command_code": getattr(operation, "command_code", None) or operation.operation_type,
        "command_type": getattr(operation, "command_type", None),
        "configuration_json": operation.configuration_json,
        "order": int(operation.order),
    }


def _serialize_item(session, item: SuiteItemEntity) -> dict:
    operations = SuiteItemOperationService().get_all_by_suite_item_id(session, item.id)
    return {
        "id": item.id,
        "test_suite_id": item.test_suite_id,
        "kind": item.kind,
        "hook_phase": item.hook_phase,
        "description": item.description,
        "sources": item.sources_json if isinstance(item.sources_json, list) else [],
        "position": int(item.position),
        "on_failure": item.on_failure,
        "role": getattr(item, "role", None) or SuiteItemRole.TEST.value,
        "template_kind": getattr(item, "template_kind", None) or TemplateKind.CUSTOM.value,
        "template_config": getattr(item, "template_config", None),
        "data_driven": bool(getattr(item, "data_driven", False)),
        "dataset_id": getattr(item, "dataset_id", None),
        "commands": [_serialize_operation(operation) for operation in operations],
    }


def _resolve_preview_dataset_parameter_bindings(bindings: dict | None) -> tuple[dict | None, str | None]:
    normalized_bindings = bindings if isinstance(bindings, dict) else {}
    resolved: dict[str, object] = {}
    for parameter_name, raw_binding in normalized_bindings.items():
        if isinstance(raw_binding, dict):
            binding_kind = str(raw_binding.get("kind") or "").strip().lower()
            if binding_kind == "built_in":
                resolved[parameter_name] = DatasetParameterResolver.resolve_builtin(
                    str(raw_binding.get("resolver") or "").strip()
                )
                continue
            if binding_kind in {"constant_ref", "constant_path"}:
                return (
                    None,
                    f"Preview non disponibile per il parametro dataset '{parameter_name}' con binding runtime.",
                )
        resolved[parameter_name] = raw_binding
    return resolved or None, None


@router.post("/test-suite")
async def insert_test_suite_api(dto: CreateTestSuiteDto):
    with managed_session() as session:
        validate_suite_constant_graph(dto)
        entity = TestSuiteEntity()
        entity.description = dto.description
        test_suite_id = TestSuiteService().insert(session, entity)
        _insert_suite_items(session, test_suite_id, hooks=dto.hooks or [], tests=dto.tests or [])
        rebuild_suite_constant_definitions(session, test_suite_id)
    return {"id": test_suite_id, "message": "Test suite added"}


@router.put("/test-suite")
async def update_test_suite_api(dto: UpdateTestSuiteDto):
    with managed_session() as session:
        validate_suite_constant_graph(dto)
        entity = TestSuiteService().update(session, dto.id, description=dto.description)
        if not entity:
            raise QualityFlowAppException(f"No test suite found with id [ {dto.id} ]")
        SuiteItemService().delete_by_suite_id(session, dto.id)
        _insert_suite_items(session, dto.id, hooks=dto.hooks or [], tests=dto.tests or [])
        rebuild_suite_constant_definitions(session, dto.id)
    return {"id": dto.id, "message": "Test suite updated"}


@router.get("/test-suite")
async def find_all_test_suites_api():
    with managed_session() as session:
        return [
            {"id": suite.id, "description": suite.description}
            for suite in TestSuiteService().get_all(session)
        ]


@router.get("/test-suite/{_id}")
async def find_test_suite_api(_id: str):
    with managed_session() as session:
        suite = TestSuiteService().get_by_id(session, _id)
        if not suite:
            raise QualityFlowAppException(f"No test suite found with id [ {_id} ]")
        items = SuiteItemService().get_all_by_suite_id(session, _id)
        hooks = []
        tests = []
        for item in items:
            serialized = _serialize_item(session, item)
            if str(item.kind or "") == SuiteItemKind.HOOK.value:
                hooks.append(serialized)
            else:
                tests.append(serialized)
        return {
            "id": suite.id,
            "description": suite.description,
            "hooks": hooks,
            "tests": tests,
        }


@router.delete("/test-suite/{_id}")
async def delete_test_suite_api(_id: str):
    with managed_session() as session:
        result = TestSuiteService().delete_by_id(session, _id)
        if result == 0:
            raise QualityFlowAppException(f"No test suite found with id [ {_id} ]")
        return {"message": f"{result} test suite(s) deleted"}


@router.get("/test-suite/{_id}/execute")
async def execute_test_suite_api(_id: str):
    execution_id = execute_test_suite_by_id(_id)
    return {"message": "Test suite started", "execution_id": execution_id}


@router.post("/test-suite/send-message-template/preview")
async def preview_send_message_template_rows_api(dto: PreviewSendMessageTemplateRowsDto):
    return preview_send_message_template_rows(
        dto.input_data,
        source_type=dto.source_type,
        for_each=dto.for_each,
    )


@router.post("/test-suite/source/preview")
async def preview_suite_source_api(dto: PreviewSuiteSourceDto, limit: int = 100):
    source = dto.source
    with managed_session() as session:
        if source.sourceType == "jsonArray":
            json_array_entity = JsonFilesService().get_by_id(session, source.jsonArrayId)
            if not json_array_entity:
                raise QualityFlowAppException(f"Json array '{source.jsonArrayId}' not found")
            payload = json_array_entity.payload
            return {
                "source_type": "jsonArray",
                "payload": payload if isinstance(payload, list) else ([payload] if payload is not None else []),
            }

        if source.sourceType == "dataset":
            dataset = DatasetQueryService.get_dataset_or_raise(session, source.datasetId)
            payload = dataset.configuration_json if isinstance(dataset.configuration_json, dict) else {}
            parameter_values, bindings_error = _resolve_preview_dataset_parameter_bindings(source.parameterBindings)
            if bindings_error:
                return {
                    "source_type": "dataset",
                    "rows": [],
                    "error": bindings_error,
                }
            try:
                preview = DatasetQueryService.execute_dataset_query(
                    payload,
                    source.perimeter,
                    limit=limit,
                    parameter_values=parameter_values,
                    dataset_id=str(dataset.id or "").strip() or source.datasetId,
                    session=session,
                )
            except Exception as exc:
                return {
                    "source_type": "dataset",
                    "rows": [],
                    "error": str(exc),
                }
            return {
                "source_type": "dataset",
                **(preview if isinstance(preview, dict) else {"rows": []}),
            }

    raise QualityFlowAppException(f"Unsupported sourceType '{source.sourceType}'")


@router.post("/test-suite/{test_suite_id}/test/{suite_item_id}/execute")
async def execute_test_api(test_suite_id: str, suite_item_id: str):
    execution_id = execute_test_by_id(
        test_suite_id=test_suite_id,
        suite_item_id=suite_item_id,
    )
    return {"message": "Test started", "execution_id": execution_id}


def _build_suite_item_update_payload(dto: CreateSuiteItemDto) -> dict:
    return {
        "kind": str(dto.kind or SuiteItemKind.TEST.value),
        "hook_phase": str(dto.hook_phase or "").strip() or None,
        "description": str(dto.description or ""),
        "sources_json": [
            source.model_dump()
            for source in (dto.sources or [])
            if hasattr(source, "model_dump")
        ],
        "on_failure": _normalize_on_failure(dto.on_failure),
        "role": str(dto.role or SuiteItemRole.TEST.value),
        "template_kind": str(dto.template_kind or TemplateKind.CUSTOM.value),
        "template_config": dto.template_config if isinstance(dto.template_config, dict) else None,
        "data_driven": bool(dto.data_driven),
        "dataset_id": (str(dto.dataset_id).strip() or None) if dto.dataset_id else None,
    }


@router.post("/test-suite/{test_suite_id}/test")
async def add_test_to_suite_api(test_suite_id: str, dto: CreateSuiteItemDto):
    """Append a single test to an existing suite.

    * `template_kind=custom` (default) → persist `dto.commands` verbatim.
    * `template_kind=send_verify|mock_assert` → run the template engine on
      `dto.template_config` and persist the generated commands; any
      `dto.commands` from the payload is ignored on purpose.
    """
    commands_to_persist = _resolve_template_commands(dto)
    with managed_session() as session:
        suite = TestSuiteService().get_by_id(session, test_suite_id)
        if not suite:
            raise QualityFlowAppException(f"No test suite found with id [ {test_suite_id} ]")

        existing_tests = SuiteItemService().get_all_tests_by_suite_id(session, test_suite_id)
        next_position = max((int(item.position) for item in existing_tests), default=0) + 1

        entity = _build_suite_item_entity(test_suite_id, dto, position=next_position)
        suite_item_id = SuiteItemService().insert(session, entity)
        _insert_suite_item_operations(session, suite_item_id, commands_to_persist)
        rebuild_suite_constant_definitions(session, test_suite_id)

        inserted = SuiteItemService().get_by_id(session, suite_item_id)
        return _serialize_item(session, inserted)


@router.put("/test-suite/{test_suite_id}/test/{suite_item_id}")
async def update_test_in_suite_api(
    test_suite_id: str,
    suite_item_id: str,
    dto: CreateSuiteItemDto,
):
    """Update a single test.

    * Custom: the `commands` list is fully replaced by the payload.
    * Template (`send_verify` / `mock_assert`): the template engine
      regenerates the commands snapshot from `dto.template_config`; any
      `dto.commands` from the payload is ignored.
    """
    commands_to_persist = _resolve_template_commands(dto)
    with managed_session() as session:
        existing = SuiteItemService().get_by_id(session, suite_item_id)
        if not existing or existing.test_suite_id != test_suite_id:
            raise QualityFlowAppException(
                f"No suite_item [ {suite_item_id} ] found in test suite [ {test_suite_id} ]."
            )

        SuiteItemService().update(
            session,
            suite_item_id,
            **_build_suite_item_update_payload(dto),
        )
        SuiteItemOperationService().delete_by_suite_item_id(session, suite_item_id)
        _insert_suite_item_operations(session, suite_item_id, commands_to_persist)
        rebuild_suite_constant_definitions(session, test_suite_id)

        updated = SuiteItemService().get_by_id(session, suite_item_id)
        return _serialize_item(session, updated)


@router.post("/test-suite/{test_suite_id}/test/{suite_item_id}/convert-to-custom")
async def convert_test_to_custom_api(test_suite_id: str, suite_item_id: str):
    """Idempotent conversion to `template_kind=custom`.

    * If the item is already custom (or its template_kind is not handled by
      the engine) → no-op, the current state is echoed back.
    * Otherwise → snapshot the template-generated commands as the editable
      starting point, then clear `template_config` and set
      `template_kind=custom`. The conversion is one-way: the original
      `template_config` is lost on purpose (mockup 10 confirm dialog covers
      the UX guard).
    """
    with managed_session() as session:
        existing = SuiteItemService().get_by_id(session, suite_item_id)
        if not existing or existing.test_suite_id != test_suite_id:
            raise QualityFlowAppException(
                f"No suite_item [ {suite_item_id} ] found in test suite [ {test_suite_id} ]."
            )

        current_template_kind = str(
            getattr(existing, "template_kind", None) or TemplateKind.CUSTOM.value
        )
        if current_template_kind != TemplateKind.CUSTOM.value and template_registry.is_supported(
            current_template_kind
        ):
            try:
                snapshot_commands = template_registry.generate_commands(
                    current_template_kind,
                    getattr(existing, "template_config", None),
                )
            except UnknownTemplateError as exc:
                raise QualityFlowAppException(str(exc)) from exc
            except InvalidTemplateConfigError as exc:
                raise QualityFlowAppException(str(exc)) from exc

            SuiteItemOperationService().delete_by_suite_item_id(session, suite_item_id)
            _insert_suite_item_operations(session, suite_item_id, snapshot_commands)
            SuiteItemService().update(
                session,
                suite_item_id,
                template_kind=TemplateKind.CUSTOM.value,
                template_config=None,
            )
            rebuild_suite_constant_definitions(session, test_suite_id)

        refreshed = SuiteItemService().get_by_id(session, suite_item_id)
        return _serialize_item(session, refreshed)


@router.get("/templates")
async def list_templates_api():
    """Static metadata of the templates the engine knows about. Used by the
    FE to render the New Test dialog dynamically."""
    return [
        {
            "kind": meta.kind,
            "name": meta.name,
            "description": meta.description,
            "config_schema_summary": meta.config_schema_summary,
        }
        for meta in template_registry.list_templates()
    ]


@router.post("/templates/preview")
async def preview_template_api(dto: TemplatePreviewDto):
    """Run the engine on `template_config` without persisting. Used by the
    Test Editor template-mode timeline (Mockup 4 right pane) to render the
    generated steps live as the user edits the form."""
    if dto.template_kind == TemplateKind.CUSTOM.value:
        return {
            "template_kind": dto.template_kind,
            "commands": [],
            "note": "Custom template_kind has no generated commands.",
        }
    try:
        commands = template_registry.generate_commands(
            dto.template_kind, dto.template_config
        )
    except UnknownTemplateError as exc:
        raise QualityFlowAppException(str(exc)) from exc
    except InvalidTemplateConfigError as exc:
        raise QualityFlowAppException(str(exc)) from exc

    serialized = [
        {
            "order": cmd.order,
            "description": cmd.description,
            "cfg": cmd.cfg.model_dump() if cmd.cfg is not None else None,
        }
        for cmd in commands
    ]
    return {"template_kind": dto.template_kind, "commands": serialized}

