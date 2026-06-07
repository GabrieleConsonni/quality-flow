from __future__ import annotations

from copy import deepcopy
from uuid import uuid4


SUITE_SECTION_TEST = "test"
SUITE_SECTION_BEFORE_ALL = "beforeAll"
SUITE_SECTION_BEFORE_EACH = "beforeEach"
SUITE_SECTION_AFTER_EACH = "afterEach"
SUITE_SECTION_AFTER_ALL = "afterAll"

_READABLE_SCOPES: dict[str, set[str]] = {
    SUITE_SECTION_BEFORE_ALL: {"runEnvelope", "result"},
    SUITE_SECTION_BEFORE_EACH: {"runEnvelope", "global", "result"},
    SUITE_SECTION_TEST: {"runEnvelope", "global", "local", "result"},
    SUITE_SECTION_AFTER_EACH: {"runEnvelope", "global", "local", "result"},
    SUITE_SECTION_AFTER_ALL: {"runEnvelope", "global", "result"},
}


def new_ui_key() -> str:
    return uuid4().hex[:10]


def _new_definition_id() -> str:
    return str(uuid4())


def _normalize_cfg(value: object) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _normalize_token(value: object) -> str:
    return str(value or "").strip()


def _command_code(cfg: dict) -> str:
    normalized = _normalize_token(cfg.get("commandCode") or cfg.get("command_code"))
    if normalized == "initConstant":
        return "setVariable"
    if normalized == "deleteConstant":
        return "deleteVariable"
    return normalized


def _definition_path(scope: str, name: str) -> str:
    return f"$.{scope}.constants.{name}"


def _stable_ui_key(*parts: object) -> str:
    raw = "_".join(_normalize_token(part) for part in parts if _normalize_token(part))
    sanitized = "".join(char if char.isalnum() else "_" for char in raw).strip("_")
    return sanitized or new_ui_key()


def _extract_scope_name(path_value: object) -> tuple[str | None, str | None]:
    raw = _normalize_token(path_value)
    if not raw:
        return None, None
    if raw.startswith("$."):
        raw = raw[2:]
    elif raw.startswith("$"):
        raw = raw[1:].lstrip(".")
    parts = [part for part in raw.split(".") if part]
    if len(parts) >= 3 and parts[1] == "constants":
        return parts[0], parts[-1]
    return None, None


def _constant_ref_id(value: object) -> str:
    if isinstance(value, dict):
        return _normalize_token(value.get("definitionId") or value.get("definition_id"))
    return ""


def _result_constant(value: object) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _definition_from_init(cfg: dict, command_order: int) -> dict | None:
    definition_id = _normalize_token(cfg.get("definitionId") or cfg.get("definition_id"))
    name = _normalize_token(cfg.get("name") or cfg.get("key"))
    context = _normalize_token(cfg.get("context") or cfg.get("scope"))
    if not definition_id or not name or not context:
        return None
    return {
        "definitionId": definition_id,
        "name": name,
        "context_scope": context,
        "value_type": _normalize_token(cfg.get("valueType") or cfg.get("value_type") or "value") or "value",
        "declared_at_order": int(command_order),
        "deleted_at_order": None,
    }


def _definition_from_result(cfg: dict, command_order: int) -> dict | None:
    result_constant = _result_constant(cfg.get("resultConstant") or cfg.get("result_constant"))
    definition_id = _normalize_token(result_constant.get("definitionId") or result_constant.get("definition_id"))
    name = _normalize_token(result_constant.get("name"))
    if not definition_id or not name:
        return None
    return {
        "definitionId": definition_id,
        "name": name,
        "context_scope": "result",
        "value_type": _normalize_token(result_constant.get("valueType") or result_constant.get("value_type") or "json")
        or "json",
        "declared_at_order": int(command_order),
        "deleted_at_order": None,
    }


def _clone_visible_definitions(definitions: dict[str, dict] | None) -> dict[str, dict]:
    return {definition_id: dict(definition) for definition_id, definition in (definitions or {}).items()}


def _carry_over_definitions(definitions: dict[str, dict] | None) -> dict[str, dict]:
    carried: dict[str, dict] = {}
    for definition_id, definition in (definitions or {}).items():
        if definition.get("deleted_at_order") is not None:
            continue
        carried[definition_id] = {
            **definition,
            "declared_at_order": 0,
        }
    return carried


def _visible_definitions(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
) -> list[dict]:
    result: list[dict] = []
    readable_scopes = _READABLE_SCOPES.get(section_type, set())
    for definition in definitions.values():
        if definition.get("context_scope") not in readable_scopes:
            continue
        if int(definition.get("declared_at_order") or 0) >= int(command_order):
            continue
        deleted_at_order = definition.get("deleted_at_order")
        if deleted_at_order is not None and int(deleted_at_order) <= int(command_order):
            continue
        result.append(definition)
    result.sort(key=lambda item: int(item.get("declared_at_order") or 0))
    return result


def _find_definition_by_scope_name(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
    scope: str | None,
    name: str | None,
) -> dict | None:
    normalized_scope = _normalize_token(scope)
    normalized_name = _normalize_token(name)
    if not normalized_scope or not normalized_name:
        return None
    matches = [
        definition
        for definition in _visible_definitions(
            definitions,
            section_type=section_type,
            command_order=command_order,
        )
        if definition.get("context_scope") == normalized_scope and definition.get("name") == normalized_name
    ]
    return matches[-1] if matches else None


def _find_definition_by_path(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
    path_value: object,
) -> dict | None:
    scope, name = _extract_scope_name(path_value)
    return _find_definition_by_scope_name(
        definitions,
        section_type=section_type,
        command_order=command_order,
        scope=scope,
        name=name,
    )


def _find_definition_by_id(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
    definition_id: str,
) -> dict | None:
    for definition in _visible_definitions(
        definitions,
        section_type=section_type,
        command_order=command_order,
    ):
        if definition.get("definitionId") == definition_id:
            return definition
    return None


def _find_definition_by_name(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
    name: str,
) -> dict | None:
    for scope in ("local", "global", "runEnvelope", "result"):
        definition = _find_definition_by_scope_name(
            definitions,
            section_type=section_type,
            command_order=command_order,
            scope=scope,
            name=name,
        )
        if definition is not None:
            return definition
    return None


def _serialize_result_constant(cfg: dict) -> dict | None:
    result_constant = _result_constant(cfg.get("resultConstant") or cfg.get("result_constant"))
    if result_constant:
        definition_id = _normalize_token(result_constant.get("definitionId") or result_constant.get("definition_id"))
        name = _normalize_token(result_constant.get("name"))
        value_type = _normalize_token(result_constant.get("valueType") or result_constant.get("value_type") or "json") or "json"
        if definition_id and name:
            return {
                "definitionId": definition_id,
                "name": name,
                "valueType": value_type,
            }

    scope, name = _extract_scope_name(cfg.get("result_target") or cfg.get("resultTarget"))
    if scope != "result" or not name:
        return None

    definition_path = _definition_path(scope, name)
    return {
        "definitionId": definition_path,
        "name": name,
        "valueType": "json",
    }


def _normalize_sources(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    normalized: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            normalized.append(deepcopy(item))
    return normalized


def _hydrate_dataset_parameter_bindings(
    bindings: object,
    definitions: dict[str, dict],
    section_type: str,
    command_order: int,
) -> dict | None:
    if not isinstance(bindings, dict):
        return None
    hydrated: dict[str, object] = {}
    for parameter_name, raw_binding in bindings.items():
        normalized_name = _normalize_token(parameter_name)
        if not normalized_name:
            continue
        if isinstance(raw_binding, dict) and _normalize_token(raw_binding.get("kind")).lower() == "constant_ref":
            definition = _find_definition_by_id(
                definitions,
                section_type=section_type,
                command_order=command_order,
                definition_id=_normalize_token(raw_binding.get("definitionId") or raw_binding.get("definition_id")),
            )
            if definition is not None:
                hydrated[normalized_name] = {
                    "kind": "constant_path",
                    "path": _definition_path(definition["context_scope"], definition["name"]),
                }
                continue
        hydrated[normalized_name] = deepcopy(raw_binding)
    return hydrated or None


def _serialize_dataset_parameter_bindings(
    bindings: object,
    definitions: dict[str, dict],
    section_type: str,
    command_order: int,
) -> dict | None:
    if not isinstance(bindings, dict):
        return None
    serialized: dict[str, object] = {}
    for parameter_name, raw_binding in bindings.items():
        normalized_name = _normalize_token(parameter_name)
        if not normalized_name:
            continue
        if isinstance(raw_binding, dict) and _normalize_token(raw_binding.get("kind")).lower() == "constant_path":
            definition = _find_definition_by_path(
                definitions,
                section_type=section_type,
                command_order=command_order,
                path_value=raw_binding.get("path"),
            )
            if definition is not None:
                serialized[normalized_name] = {
                    "kind": "constant_ref",
                    "definitionId": definition["definitionId"],
                }
                continue
        serialized[normalized_name] = deepcopy(raw_binding)
    return serialized or None


def _resolve_runtime_definition_id(
    definitions: dict[str, dict],
    *,
    section_type: str,
    command_order: int,
    value: object,
) -> str:
    normalized_value = _normalize_token(value)
    if not normalized_value:
        return ""
    definition = _find_definition_by_id(
        definitions,
        section_type=section_type,
        command_order=command_order,
        definition_id=normalized_value,
    )
    if definition is not None:
        return str(definition["definitionId"])
    definition = _find_definition_by_path(
        definitions,
        section_type=section_type,
        command_order=command_order,
        path_value=normalized_value,
    )
    if definition is not None:
        return str(definition["definitionId"])
    return normalized_value


def _serialize_http_runtime_refs(
    value: object,
    definitions: dict[str, dict],
    section_type: str,
    command_order: int,
) -> object:
    if isinstance(value, list):
        return [
            _serialize_http_runtime_refs(item, definitions, section_type, command_order)
            for item in value
        ]
    if not isinstance(value, dict):
        return deepcopy(value)

    serialized = deepcopy(value)
    if _normalize_token(serialized.get("kind")) == "runtimeValue":
        definition_id = _resolve_runtime_definition_id(
            definitions,
            section_type=section_type,
            command_order=command_order,
            value=serialized.get("definitionId") or serialized.get("definition_id"),
        )
        if definition_id:
            serialized["definitionId"] = definition_id
            serialized.pop("definition_id", None)
        return serialized

    for key, item in list(serialized.items()):
        serialized[key] = _serialize_http_runtime_refs(item, definitions, section_type, command_order)
    return serialized


def _hydrate_http_runtime_refs(
    value: object,
    definitions: dict[str, dict],
    section_type: str,
    command_order: int,
) -> object:
    if isinstance(value, list):
        return [
            _hydrate_http_runtime_refs(item, definitions, section_type, command_order)
            for item in value
        ]
    if not isinstance(value, dict):
        return deepcopy(value)

    hydrated = deepcopy(value)
    if _normalize_token(hydrated.get("kind")) == "runtimeValue":
        definition = _find_definition_by_id(
            definitions,
            section_type=section_type,
            command_order=command_order,
            definition_id=_normalize_token(hydrated.get("definitionId") or hydrated.get("definition_id")),
        )
        if definition is not None:
            hydrated["definitionId"] = _definition_path(definition["context_scope"], definition["name"])
            hydrated.pop("definition_id", None)
        return hydrated

    for key, item in list(hydrated.items()):
        hydrated[key] = _hydrate_http_runtime_refs(item, definitions, section_type, command_order)
    return hydrated


def _hydrate_operation_cfg(cfg: dict, definitions: dict[str, dict], section_type: str, command_order: int) -> dict:
    hydrated = deepcopy(cfg)
    command_code = _command_code(hydrated)
    if command_code:
        hydrated["commandCode"] = command_code

    if command_code == "deleteVariable":
        definition_id = _constant_ref_id(hydrated.get("targetRuntimeValueRef") or hydrated.get("target_runtime_value_ref"))
        definition = _find_definition_by_id(
            definitions,
            section_type=section_type,
            command_order=command_order,
            definition_id=definition_id,
        )
        if definition is not None:
            hydrated.setdefault("name", definition.get("name"))
            hydrated.setdefault("context", definition.get("context_scope"))
            hydrated.setdefault("scope", definition.get("context_scope"))

    input_ref = (
        hydrated.get("inputRef")
        or hydrated.get("input_ref")
        or hydrated.get("sourceConstantRef")
        or hydrated.get("source_constant_ref")
    )
    source_definition_id = ""
    input_ref_kind = _normalize_token(input_ref.get("kind")) if isinstance(input_ref, dict) else ""
    if isinstance(input_ref, dict) and (input_ref_kind == "runtimeValue" or not input_ref_kind):
        source_definition_id = _constant_ref_id(input_ref)
    if isinstance(input_ref, dict) and input_ref_kind == "source":
        hydrated["sourceCode"] = _normalize_token(input_ref.get("sourceCode") or input_ref.get("source_code"))
    if source_definition_id and not _normalize_token(hydrated.get("source")):
        definition = _find_definition_by_id(
            definitions,
            section_type=section_type,
            command_order=command_order,
            definition_id=source_definition_id,
        )
        if definition is not None:
            hydrated["source"] = _definition_path(definition["context_scope"], definition["name"])

    actual_ref = (
        hydrated.get("actualRef")
        or hydrated.get("actual_ref")
        or hydrated.get("actualConstantRef")
        or hydrated.get("actual_constant_ref")
    )
    actual_definition_id = ""
    actual_ref_kind = _normalize_token(actual_ref.get("kind")) if isinstance(actual_ref, dict) else ""
    if isinstance(actual_ref, dict) and (actual_ref_kind == "runtimeValue" or not actual_ref_kind):
        actual_definition_id = _constant_ref_id(actual_ref)
    if isinstance(actual_ref, dict) and actual_ref_kind == "source":
        hydrated["actualSourceCode"] = _normalize_token(actual_ref.get("sourceCode") or actual_ref.get("source_code"))
    if actual_definition_id and not hydrated.get("actual"):
        definition = _find_definition_by_id(
            definitions,
            section_type=section_type,
            command_order=command_order,
            definition_id=actual_definition_id,
        )
        if definition is not None:
            hydrated["actual"] = _definition_path(definition["context_scope"], definition["name"])

    expected_ref = hydrated.get("expectedRef") or hydrated.get("expected_ref")
    if isinstance(expected_ref, dict) and _normalize_token(expected_ref.get("kind")) == "source":
        hydrated["expectedSourceCode"] = _normalize_token(
            expected_ref.get("sourceCode") or expected_ref.get("source_code")
        )

    if command_code in {"readApi", "writeApi"}:
        for field_name in ("queryParams", "headers", "pathParams", "authorization", "body"):
            if field_name in hydrated:
                hydrated[field_name] = _hydrate_http_runtime_refs(
                    hydrated[field_name],
                    definitions,
                    section_type,
                    command_order,
                )

    constant_refs = hydrated.get("runtimeValueRefs") or hydrated.get("runtime_value_refs") or []
    if constant_refs and not hydrated.get("constants"):
        constant_names: list[str] = []
        for item in constant_refs:
            definition_id = _constant_ref_id(item)
            definition = _find_definition_by_id(
                definitions,
                section_type=section_type,
                command_order=command_order,
                definition_id=definition_id,
            )
            if definition is not None:
                constant_names.append(str(definition.get("name") or ""))
        if constant_names:
            hydrated["constants"] = constant_names

    result_constant = _serialize_result_constant(hydrated)
    if result_constant is not None and not _normalize_token(hydrated.get("result_target") or hydrated.get("resultTarget")):
        hydrated["result_target"] = _definition_path("result", result_constant["name"])
    if command_code == "setVariable":
        hydrated_bindings = _hydrate_dataset_parameter_bindings(
            hydrated.get("parameters"),
            definitions,
            section_type,
            command_order,
        )
        if hydrated_bindings is not None:
            hydrated["parameters"] = hydrated_bindings

    return hydrated


def _serialize_operation_cfg(cfg: dict, definitions: dict[str, dict], section_type: str, command_order: int) -> dict:
    serialized = deepcopy(cfg)
    command_code = _command_code(serialized)
    if command_code:
        serialized["commandCode"] = command_code

    if command_code == "setVariable":
        serialized["definitionId"] = _normalize_token(serialized.get("definitionId") or serialized.get("definition_id")) or _new_definition_id()
        serialized_bindings = _serialize_dataset_parameter_bindings(
            serialized.get("parameters"),
            definitions,
            section_type,
            command_order,
        )
        if serialized_bindings is not None:
            serialized["parameters"] = serialized_bindings

    if command_code == "deleteVariable":
        serialized.pop("targetRuntimeValueRef", None)
        serialized.pop("target_runtime_value_ref", None)
        definition = _find_definition_by_scope_name(
            definitions,
            section_type=section_type,
            command_order=command_order,
            scope=serialized.get("context") or serialized.get("scope"),
            name=serialized.get("name") or serialized.get("key"),
        )
        if definition is not None:
            serialized["targetRuntimeValueRef"] = {"definitionId": definition["definitionId"]}

    if command_code in {"sendMessageQueue", "saveTable", "exportDataset"}:
        serialized.pop("sourceConstantRef", None)
        serialized.pop("source_constant_ref", None)
        serialized.pop("inputRef", None)
        serialized.pop("input_ref", None)
        source_code = _normalize_token(serialized.get("sourceCode") or serialized.get("source_code"))
        if source_code:
            serialized["inputRef"] = {"kind": "source", "sourceCode": source_code}
        else:
            definition = _find_definition_by_path(
                definitions,
                section_type=section_type,
                command_order=command_order,
                path_value=serialized.get("source"),
            )
            if definition is not None:
                serialized["inputRef"] = {"kind": "runtimeValue", "definitionId": definition["definitionId"]}

    if command_code in {"readApi", "writeApi"}:
        for field_name in ("queryParams", "headers", "pathParams", "authorization", "body"):
            if field_name in serialized:
                serialized[field_name] = _serialize_http_runtime_refs(
                    serialized[field_name],
                    definitions,
                    section_type,
                    command_order,
                )

    if command_code in {
        "jsonEquals",
        "jsonEmpty",
        "jsonNotEmpty",
        "jsonContains",
        "jsonArrayEquals",
        "jsonArrayEmpty",
        "jsonArrayNotEmpty",
        "jsonArrayContains",
    }:
        serialized.pop("actualConstantRef", None)
        serialized.pop("actual_constant_ref", None)
        serialized.pop("actualRef", None)
        serialized.pop("actual_ref", None)
        actual_source_code = _normalize_token(serialized.get("actualSourceCode") or serialized.get("actual_source_code"))
        if actual_source_code:
            serialized["actualRef"] = {"kind": "source", "sourceCode": actual_source_code}
        else:
            definition = _find_definition_by_path(
                definitions,
                section_type=section_type,
                command_order=command_order,
                path_value=serialized.get("actual"),
            )
            if definition is not None:
                serialized["actualRef"] = {"kind": "runtimeValue", "definitionId": definition["definitionId"]}

        expected_source_code = _normalize_token(serialized.get("expectedSourceCode") or serialized.get("expected_source_code"))
        serialized.pop("expectedRef", None)
        serialized.pop("expected_ref", None)
        if expected_source_code:
            serialized["expectedRef"] = {"kind": "source", "sourceCode": expected_source_code}

    if command_code == "runSuite":
        serialized.pop("runtimeValueRefs", None)
        serialized.pop("runtime_value_refs", None)
        constant_refs: list[dict[str, str]] = []
        for constant_name in serialized.get("constants") or []:
            definition = _find_definition_by_name(
                definitions,
                section_type=section_type,
                command_order=command_order,
                name=str(constant_name or ""),
            )
            if definition is not None:
                constant_refs.append({"definitionId": definition["definitionId"]})
        if constant_refs:
            serialized["runtimeValueRefs"] = constant_refs

    result_constant = _serialize_result_constant(serialized)
    if result_constant is not None:
        serialized["resultConstant"] = result_constant

    return serialized


def _apply_post_command_definition_updates(cfg: dict, definitions: dict[str, dict], command_order: int) -> None:
    command_code = _command_code(cfg)
    if command_code == "deleteVariable":
        definition_id = _constant_ref_id(cfg.get("targetRuntimeValueRef") or cfg.get("target_runtime_value_ref"))
        if definition_id and definition_id in definitions:
            definitions[definition_id] = {
                **definitions[definition_id],
                "deleted_at_order": int(command_order),
            }
        return

    declared_constant = _definition_from_init(cfg, command_order)
    if declared_constant is not None:
        definitions[declared_constant["definitionId"]] = declared_constant

    result_constant = _definition_from_result(cfg, command_order)
    if result_constant is not None:
        definitions[result_constant["definitionId"]] = result_constant


def _normalize_operations_for_draft(
    operations_source: list[dict] | None,
    *,
    section_type: str,
    initial_definitions: dict[str, dict],
    ui_scope: str,
) -> tuple[list[dict], dict[str, dict]]:
    definitions = _carry_over_definitions(initial_definitions)
    normalized_operations: list[dict] = []
    for op_idx, operation in enumerate(operations_source or [], start=1):
        if not isinstance(operation, dict):
            continue
        cfg = _normalize_cfg(operation.get("configuration_json") or operation.get("cfg"))
        command_order = int(operation.get("order") or op_idx)
        hydrated_cfg = _hydrate_operation_cfg(cfg, definitions, section_type, command_order)
        normalized_operation = {
            **operation,
            "order": command_order,
            "configuration_json": hydrated_cfg,
            "_ui_key": str(
                operation.get("_ui_key")
                or _stable_ui_key("op", ui_scope, command_order, _command_code(hydrated_cfg))
            ),
        }
        normalized_operations.append(normalized_operation)
        _apply_post_command_definition_updates(hydrated_cfg, definitions, command_order)
    return normalized_operations, definitions


def _serialize_operations_for_payload(
    operations_source: list[dict] | None,
    *,
    section_type: str,
    initial_definitions: dict[str, dict],
) -> tuple[list[dict], dict[str, dict]]:
    definitions = _carry_over_definitions(initial_definitions)
    commands_payload: list[dict] = []
    for op_idx, operation in enumerate(operations_source or [], start=1):
        if not isinstance(operation, dict):
            continue
        cfg = _normalize_cfg(operation.get("configuration_json") or operation.get("cfg"))
        command_order = int(operation.get("order") or op_idx)
        serialized_cfg = _serialize_operation_cfg(cfg, definitions, section_type, command_order)
        commands_payload.append(
            {
                "order": command_order,
                "description": str(operation.get("description") or ""),
                "cfg": serialized_cfg,
            }
        )
        _apply_post_command_definition_updates(serialized_cfg, definitions, command_order)
    return commands_payload, definitions


def _section_type_for_phase(hook_phase: str) -> str:
    mapping = {
        "before-all": SUITE_SECTION_BEFORE_ALL,
        "before-each": SUITE_SECTION_BEFORE_EACH,
        "after-each": SUITE_SECTION_AFTER_EACH,
        "after-all": SUITE_SECTION_AFTER_ALL,
    }
    return mapping.get(str(hook_phase or "").strip(), SUITE_SECTION_TEST)


def build_test_suite_draft(payload: dict | None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    hooks_map: dict[str, dict] = {}

    raw_hooks = {
        str(hook.get("hook_phase") or "").strip(): hook
        for hook in source.get("hooks") or []
        if isinstance(hook, dict) and str(hook.get("hook_phase") or "").strip()
    }

    before_all_defs: dict[str, dict] = {}
    before_each_defs: dict[str, dict] = {}

    before_all_hook = raw_hooks.get("before-all")
    if isinstance(before_all_hook, dict):
        operations, before_all_defs = _normalize_operations_for_draft(
            list(before_all_hook.get("commands") or before_all_hook.get("operations") or []),
            section_type=SUITE_SECTION_BEFORE_ALL,
            initial_definitions={},
            ui_scope="hook_before_all",
        )
        hooks_map["before-all"] = {
            **before_all_hook,
            "sources": _normalize_sources(before_all_hook.get("sources")),
            "operations": operations,
            "_ui_key": str(before_all_hook.get("_ui_key") or "hook_before_all"),
        }
    before_each_defs = _clone_visible_definitions(before_all_defs)

    before_each_hook = raw_hooks.get("before-each")
    if isinstance(before_each_hook, dict):
        operations, before_each_defs = _normalize_operations_for_draft(
            list(before_each_hook.get("commands") or before_each_hook.get("operations") or []),
            section_type=SUITE_SECTION_BEFORE_EACH,
            initial_definitions=before_all_defs,
            ui_scope="hook_before_each",
        )
        hooks_map["before-each"] = {
            **before_each_hook,
            "sources": _normalize_sources(before_each_hook.get("sources")),
            "operations": operations,
            "_ui_key": str(before_each_hook.get("_ui_key") or "hook_before_each"),
        }

    tests = []
    for idx, test in enumerate(source.get("tests") or [], start=1):
        if not isinstance(test, dict):
            continue
        test_position = int(test.get("position") or idx)
        test_ui_scope = _stable_ui_key("test", test.get("id") or test_position)
        operations, _ = _normalize_operations_for_draft(
            list(test.get("commands") or test.get("operations") or []),
            section_type=SUITE_SECTION_TEST,
            initial_definitions=before_each_defs,
            ui_scope=test_ui_scope,
        )
        tests.append(
            {
                **test,
                "sources": _normalize_sources(test.get("sources")),
                "position": test_position,
                "operations": operations,
                "_ui_key": str(test.get("_ui_key") or test_ui_scope),
            }
        )

    after_each_hook = raw_hooks.get("after-each")
    if isinstance(after_each_hook, dict):
        operations, _ = _normalize_operations_for_draft(
            list(after_each_hook.get("commands") or after_each_hook.get("operations") or []),
            section_type=SUITE_SECTION_AFTER_EACH,
            initial_definitions=before_each_defs,
            ui_scope="hook_after_each",
        )
        hooks_map["after-each"] = {
            **after_each_hook,
            "sources": _normalize_sources(after_each_hook.get("sources")),
            "operations": operations,
            "_ui_key": str(after_each_hook.get("_ui_key") or "hook_after_each"),
        }

    after_all_hook = raw_hooks.get("after-all")
    if isinstance(after_all_hook, dict):
        operations, _ = _normalize_operations_for_draft(
            list(after_all_hook.get("commands") or after_all_hook.get("operations") or []),
            section_type=SUITE_SECTION_AFTER_ALL,
            initial_definitions=before_all_defs,
            ui_scope="hook_after_all",
        )
        hooks_map["after-all"] = {
            **after_all_hook,
            "sources": _normalize_sources(after_all_hook.get("sources")),
            "operations": operations,
            "_ui_key": str(after_all_hook.get("_ui_key") or "hook_after_all"),
        }

    return {
        "id": source.get("id"),
        "description": str(source.get("description") or ""),
        "hooks": hooks_map,
        "tests": tests,
    }


def draft_to_test_suite_payload(draft: dict) -> dict:
    def _serialize_item(item: dict, *, section_type: str, initial_definitions: dict[str, dict]) -> tuple[dict, dict[str, dict]]:
        commands, resulting_definitions = _serialize_operations_for_payload(
            list(item.get("operations") or []),
            section_type=section_type,
            initial_definitions=initial_definitions,
        )
        payload = {
            "kind": str(item.get("kind") or "test"),
            "description": str(item.get("description") or ""),
            "on_failure": str(item.get("on_failure") or "ABORT"),
            "sources": _normalize_sources(item.get("sources")),
            "commands": commands,
        }
        hook_phase = str(item.get("hook_phase") or "").strip()
        if hook_phase:
            payload["hook_phase"] = hook_phase
        return payload, resulting_definitions

    hooks_payload = []
    hooks = draft.get("hooks") or {}
    before_all_defs: dict[str, dict] = {}
    before_each_defs: dict[str, dict] = {}

    if isinstance(hooks, dict):
        before_all_item = hooks.get("before-all")
        if isinstance(before_all_item, dict):
            before_all_item["hook_phase"] = "before-all"
            before_all_item["kind"] = "hook"
            payload, before_all_defs = _serialize_item(
                before_all_item,
                section_type=SUITE_SECTION_BEFORE_ALL,
                initial_definitions={},
            )
            hooks_payload.append(payload)
        before_each_defs = _clone_visible_definitions(before_all_defs)

        before_each_item = hooks.get("before-each")
        if isinstance(before_each_item, dict):
            before_each_item["hook_phase"] = "before-each"
            before_each_item["kind"] = "hook"
            payload, before_each_defs = _serialize_item(
                before_each_item,
                section_type=SUITE_SECTION_BEFORE_EACH,
                initial_definitions=before_all_defs,
            )
            hooks_payload.append(payload)

    tests_payload = []
    for position, item in enumerate(draft.get("tests") or [], start=1):
        if not isinstance(item, dict):
            continue
        item["position"] = position
        item["kind"] = "test"
        payload, _ = _serialize_item(
            item,
            section_type=SUITE_SECTION_TEST,
            initial_definitions=before_each_defs,
        )
        tests_payload.append(payload)

    if isinstance(hooks, dict):
        after_each_item = hooks.get("after-each")
        if isinstance(after_each_item, dict):
            after_each_item["hook_phase"] = "after-each"
            after_each_item["kind"] = "hook"
            payload, _ = _serialize_item(
                after_each_item,
                section_type=SUITE_SECTION_AFTER_EACH,
                initial_definitions=before_each_defs,
            )
            hooks_payload.append(payload)

        after_all_item = hooks.get("after-all")
        if isinstance(after_all_item, dict):
            after_all_item["hook_phase"] = "after-all"
            after_all_item["kind"] = "hook"
            payload, _ = _serialize_item(
                after_all_item,
                section_type=SUITE_SECTION_AFTER_ALL,
                initial_definitions=before_all_defs,
            )
            hooks_payload.append(payload)

    return {
        "description": str(draft.get("description") or ""),
        "hooks": hooks_payload,
        "tests": tests_payload,
    }
