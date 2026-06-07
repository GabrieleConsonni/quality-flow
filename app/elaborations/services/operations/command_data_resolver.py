from __future__ import annotations

from data_sources.services.dataset_parameter_resolver import DatasetParameterResolver
from data_sources.services.dataset_query_service import DatasetQueryService
from elaborations.models.dtos.configuration_command_dto import InputRefDto, InputRefKind
from elaborations.services.constants.command_constant_definition_registry import (
    resolve_definition_path,
)
from elaborations.services.suite_runs.run_context import (
    build_run_context_scope,
    get_run_context,
    write_context_path,
)
from elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value
from json_utils.services.alembic.json_files_service import JsonFilesService


def resolve_command_input_data(source: str | None, data):
    if not source:
        return data
    resolved = resolve_dynamic_value(source, build_run_context_scope())
    return resolved


def _resolve_dataset_parameter_bindings(session, bindings: dict | None) -> dict:
    normalized_parameters = bindings if isinstance(bindings, dict) else {}
    resolved: dict[str, object] = {}
    for parameter_name, raw_binding in normalized_parameters.items():
        if isinstance(raw_binding, dict):
            binding_kind = str(raw_binding.get("kind") or "").strip().lower()
            if binding_kind == "constant_ref":
                _definition, path = resolve_definition_path(
                    session,
                    str(raw_binding.get("definitionId") or "").strip(),
                )
                resolved_value = resolve_dynamic_value(path, build_run_context_scope())
                if resolved_value == path:
                    raise ValueError(
                        f"Dataset parameter '{parameter_name}' constant reference is not resolved."
                    )
                resolved[parameter_name] = resolved_value
                continue
            if binding_kind == "built_in":
                resolved[parameter_name] = DatasetParameterResolver.resolve_builtin(
                    str(raw_binding.get("resolver") or "").strip()
                )
                continue
        resolved[parameter_name] = raw_binding
    return resolved


def _resolve_source_payload(session, source_code: str) -> tuple[object, str]:
    context = get_run_context()
    visible_sources = context.visible_sources if context is not None and isinstance(context.visible_sources, dict) else {}
    source = visible_sources.get(str(source_code or "").strip())
    if not isinstance(source, dict):
        raise ValueError(f"Source '{source_code}' is not visible in the current execution context.")

    source_type = str(source.get("sourceType") or "").strip()
    if source_type == "jsonArray":
        json_array_id = str(source.get("jsonArrayId") or "").strip()
        json_payload_entity = JsonFilesService().get_by_id(session, json_array_id)
        if not json_payload_entity:
            raise ValueError(f"Json array '{json_array_id}' not found")
        payload = json_payload_entity.payload
        return (payload if isinstance(payload, list) else [payload]), source_type

    if source_type == "dataset":
        dataset_id = str(source.get("datasetId") or "").strip()
        dataset = DatasetQueryService.get_dataset_or_raise_for_runtime(session, dataset_id)
        perimeter = DatasetQueryService.normalize_perimeter(source.get("perimeter")) or {}
        parameter_values = _resolve_dataset_parameter_bindings(session, source.get("parameterBindings"))
        preview = DatasetQueryService.execute_dataset_query(
            dataset.configuration_json if isinstance(dataset.configuration_json, dict) else {},
            perimeter,
            parameter_values=parameter_values,
            dataset_id=dataset_id,
            session=session,
        )
        return preview.get("rows") or [], source_type

    raise ValueError(f"Unsupported sourceType '{source_type}'.")


def resolve_input_reference(session, input_ref: InputRefDto | None, data):
    if input_ref is None:
        return data, "json"
    if input_ref.kind == InputRefKind.RUNTIME_VALUE.value:
        resolved = resolve_definition_input_data(session, input_ref.definitionId, data)
        definition, _path = resolve_definition_path(session, input_ref.definitionId)
        return resolved, str(getattr(definition, "value_type", "") or "json")
    resolved, source_type = _resolve_source_payload(session, input_ref.sourceCode)
    return resolved, source_type


def resolve_definition_input_data(session, definition_id: str | None, data):
    if not definition_id:
        return data
    definition, path = resolve_definition_path(session, definition_id)
    resolved = resolve_dynamic_value(path, build_run_context_scope())
    if resolved == path:
        return None
    return resolved


def write_result_constant(session, result_constant, value):
    if result_constant is None:
        return
    _definition, path = resolve_definition_path(session, result_constant.definitionId)
    write_context_path(path, value)


def coerce_rows(value) -> list[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []
