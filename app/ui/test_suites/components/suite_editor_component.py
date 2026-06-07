import json
from copy import deepcopy

import streamlit as st

from datetime import datetime

from database_connections.services.data_loader_service import (
    DATABASE_CONNECTIONS_KEY,
    load_database_connections,
)
from database_datasources.services.state_service import open_test_source_perimeter_editor
from database_datasources.services.perimeter_service import (
    build_connection_label,
    build_dataset_summary,
    build_filter_text,
    build_sort_text,
)
from elaborations_shared.components.auth_editor import (
    collect_auth_editor_value,
    initialize_auth_editor_state,
    render_auth_editor,
)
from elaborations_shared.components.guided_kv_editor import (
    collect_guided_kv_rows,
    ensure_guided_kv_state,
    render_guided_kv_rows_container,
)
from elaborations_shared.components.guided_value_control import (
    VALUE_MODE_BUILT_IN,
    VALUE_MODE_LITERAL,
    VALUE_MODE_RUNTIME_VALUE,
)
from elaborations_shared.components.kv_editor import (
    ensure_kv_editor_state,
    render_kv_rows_container,
    rows_to_dict,
)
from elaborations_shared.components.test_command_component import (
    find_draft_test_by_ui_key,
)
from elaborations_shared.services.data_loader_service import (
    load_test_editor_context,
    load_test_editor_queues_for_broker,
)
from elaborations_shared.services.state_keys import (
    ADD_TEST_OPERATION_DIALOG_NONCE_KEY,
    ADD_TEST_OPERATION_DIALOG_OPEN_KEY,
    ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY,
    SUITE_FEEDBACK_KEY,
    TEST_EDITOR_BROKERS_KEY,
    TEST_EDITOR_DATABASE_DATASOURCES_KEY,
    TEST_EDITOR_JSON_ARRAYS_KEY,
)
from test_suites.services.api_service import (
    get_all_test_suites,
    get_test_suite_by_id,
    get_test_suite_executions,
    preview_send_message_template_rows_via_api,
    preview_suite_source_via_api,
    update_test_suite,
)
from test_suites.services.draft_mapper import (
    build_test_suite_draft,
    draft_to_test_suite_payload,
    new_ui_key,
)
from test_suites.services.state_keys import (
    ADVANCED_SUITE_EDITOR_PAGE_PATH,
    SELECTED_TEST_POSITION_KEY,
    SELECTED_TEST_SUITE_ID_KEY,
    TEST_EDITOR_PAGE_PATH,
    TEST_SUITE_DRAFT_KEY,
    TEST_SUITE_EXECUTIONS_KEY,
    TEST_SUITE_FEEDBACK_KEY,
    TEST_SUITE_LAST_EXECUTION_ID_KEY,
    TEST_SUITES_KEY,
)

SELECTED_TEST_SUITE_EXECUTION_ID_KEY = "selected_test_suite_execution_id"
PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY = "pending_test_suite_execution_selection"
ADD_TEST_DIALOG_OPEN_KEY = "test_suite_add_test_dialog_open"
ADD_TEST_DIALOG_NONCE_KEY = "test_suite_add_test_dialog_nonce"
HOOK_ADD_COMMAND_DIALOG_OPEN_KEY = "suite_editor_hook_add_command_dialog_open"
HOOK_ADD_COMMAND_DIALOG_NONCE_KEY = "suite_editor_hook_add_command_dialog_nonce"
HOOK_ADD_COMMAND_DIALOG_TARGET_UI_KEY = "suite_editor_hook_add_command_dialog_target_ui_key"
HOOK_ADD_COMMAND_DIALOG_GROUP_KEY = "suite_editor_hook_add_command_dialog_group"
TEST_ADD_COMMAND_DIALOG_OPEN_KEY = "suite_editor_test_add_command_dialog_open"
TEST_ADD_COMMAND_DIALOG_NONCE_KEY = "suite_editor_test_add_command_dialog_nonce"
TEST_ADD_COMMAND_DIALOG_TARGET_UI_KEY = "suite_editor_test_add_command_dialog_target_ui_key"
TEST_ADD_COMMAND_DIALOG_GROUP_KEY = "suite_editor_test_add_command_dialog_group"
SOURCE_ADD_DIALOG_OPEN_KEY = "suite_editor_source_add_dialog_open"
SOURCE_ADD_DIALOG_NONCE_KEY = "suite_editor_source_add_dialog_nonce"
SOURCE_ADD_DIALOG_TARGET_UI_KEY = "suite_editor_source_add_dialog_target_ui_key"
SOURCE_DIALOG_MODE_KEY = "suite_editor_source_dialog_mode"
SOURCE_DIALOG_SOURCE_CODE_KEY = "suite_editor_source_dialog_source_code"
SOURCE_PREVIEW_CACHE_KEY = "suite_editor_source_preview_cache"
TEST_EDITOR_INLINE_COMMAND_UI_KEY = "test_editor_inline_command_ui_key"
TEST_EDITOR_INLINE_COMMAND_NONCE_KEY = "test_editor_inline_command_nonce"
COMMAND_EDIT_DIALOG_OPEN_KEY = "suite_editor_command_edit_dialog_open"
COMMAND_EDIT_DIALOG_NONCE_KEY = "suite_editor_command_edit_dialog_nonce"
COMMAND_EDIT_DIALOG_TARGET_ITEM_UI_KEY = "suite_editor_command_edit_dialog_target_item_ui_key"
COMMAND_EDIT_DIALOG_TARGET_COMMAND_UI_KEY = "suite_editor_command_edit_dialog_target_command_ui_key"
COMMAND_EDIT_DIALOG_OWNER_KIND_KEY = "suite_editor_command_edit_dialog_owner_kind"
COMMAND_EDIT_DIALOG_GROUP_KEY = "suite_editor_command_edit_dialog_group"
COMMAND_REORDER_DIALOG_OPEN_KEY = "suite_editor_command_reorder_dialog_open"
COMMAND_REORDER_DIALOG_NONCE_KEY = "suite_editor_command_reorder_dialog_nonce"
COMMAND_REORDER_DIALOG_TARGET_ITEM_UI_KEY = "suite_editor_command_reorder_dialog_target_item_ui_key"
COMMAND_REORDER_DIALOG_OPERATIONS_KEY = "suite_editor_command_reorder_dialog_operations"
INLINE_API_REOPEN_COMMAND_UI_KEY = "suite_editor_inline_api_reopen_command_ui_key"
HOOK_CONTEXT_COMMAND_CODES = ["initConstant", "deleteConstant"]
HOOK_ACTION_COMMAND_CODES = [
    "readApi",
    "writeApi",
    "saveTable",
    "dropTable",
    "cleanTable",
    "exportDataset",
    "dropDataset",
    "cleanDataset",
]
TEST_CONSTANT_COMMAND_CODES = ["initConstant"]
TEST_ASSERT_COMMAND_CODES = [
    "jsonEquals",
    "jsonEmpty",
    "jsonNotEmpty",
    "jsonContains",
    "jsonArrayEquals",
    "jsonArrayEmpty",
    "jsonArrayNotEmpty",
    "jsonArrayContains",
]
TEST_ACTION_COMMAND_OPTIONS = [
    ("readApi", "readApi"),
    ("writeApi", "writeApi"),
    ("sendMessageQueue", "sendMessageQueue"),
    ("saveTable", "saveTable"),
    ("dropTable", "dropTable"),
    ("cleanTable", "cleanTable"),
    ("exportDataset", "exportDataset"),
    ("dropDataset", "dropDataset"),
    ("cleanDataset", "cleanDataset"),
]
TEST_ACTION_COMMAND_MAPPING = {
    "readApi": "readApi",
    "writeApi": "writeApi",
    "sendMessageQueue": "sendMessageQueue",
    "saveTable": "saveTable",
    "dropTable": "dropTable",
    "cleanTable": "cleanTable",
    "exportDataset": "exportDataset",
    "dropDataset": "dropDataset",
    "cleanDataset": "cleanDataset",
}
HOOK_COMMAND_LABELS = {
    "initConstant": "Set runtime value",
    "deleteConstant": "Delete runtime value",
    "readApi": "Read API",
    "writeApi": "Write API",
    "saveTable": "Save table",
    "dropTable": "Drop table",
    "cleanTable": "Clean table",
    "exportDataset": "Export dataset",
    "dropDataset": "Drop dataset",
    "cleanDataset": "Clean dataset",
}
CONSTANT_CONTEXT_OPTIONS = ["runEnvelope", "global", "local", "result"]
TEST_CONSTANT_CONTEXT_OPTIONS = ["local", "result", "global", "runEnvelope"]
CONSTANT_SOURCE_OPTIONS = ["value", "json", "function"]
DECLARATIVE_SOURCE_OPTIONS = ["dataset", "jsonArray"]
EXPORT_DATASET_MODE_OPTIONS = ["append", "drop-create", "insert-update"]
HTTP_WRITE_METHOD_OPTIONS = ["POST", "PUT", "PATCH", "DELETE"]
HTTP_BODY_TYPE_OPTIONS = ["json", "text", "formUrlEncoded"]
FORM_URLENCODED_ALLOWED_MODES = [
    VALUE_MODE_LITERAL,
    VALUE_MODE_RUNTIME_VALUE,
    VALUE_MODE_BUILT_IN,
]
ADVANCED_HOOK_SECTION_TAB_KEY_PREFIX = "advanced_suite_editor_hook_section"
ADVANCED_HOOK_SELECTED_COMMAND_KEY_PREFIX = "advanced_suite_editor_hook_selected_command"
ADVANCED_HOOK_API_TAB_KEY_PREFIX = "advanced_suite_editor_hook_api_tab"
ADVANCED_HOOK_SECTION_COMMANDS_TAB = ":material/deployed_code: Commands"
ADVANCED_HOOK_SECTION_DATASOURCES_TAB = ":material/data_array: Datasources"
ADVANCED_HOOK_DESCRIPTION_BY_PHASE = {
    "before-all": "Runs once before the suite starts.",
    "before-each": "Runs before each test execution.",
    "after-each": "Runs after each test execution.",
    "after-all": "Runs once after the suite ends.",
}
SOURCE_COMPATIBILITY_BY_COMMAND = {
    "sendMessageQueue": {"value", "json", "dataset", "jsonArray"},
    "saveTable": {"json", "dataset", "jsonArray"},
    "exportDataset": {"json", "dataset", "jsonArray"},
}
ASSERT_ACTUAL_COMPATIBILITY_BY_COMMAND = {
    "jsonEquals": {"json"},
    "jsonEmpty": {"json"},
    "jsonNotEmpty": {"json"},
    "jsonContains": {"json"},
    "jsonArrayEquals": {"jsonArray"},
    "jsonArrayEmpty": {"jsonArray"},
    "jsonArrayNotEmpty": {"jsonArray"},
    "jsonArrayContains": {"jsonArray"},
}
ASSERT_EXPECTED_COMPATIBILITY_BY_COMMAND = {
    "jsonEquals": {"json"},
    "jsonContains": {"json"},
}
ASSERT_EXPECTED_MODE_OPTIONS = ["manual", "variable"]
ASSERT_EXPECTED_MODE_LABELS = {
    "manual": "Manual value",
    "variable": "Variable",
}
READABLE_SCOPES_BY_SECTION = {
    "beforeAll": {"runEnvelope", "result"},
    "beforeEach": {"runEnvelope", "global", "result"},
    "test": {"runEnvelope", "global", "local", "result"},
    "afterEach": {"runEnvelope", "global", "local", "result"},
    "afterAll": {"runEnvelope", "global", "result"},
}
COMMAND_ICON_DEFAULT = ":material/terminal:"
COMMAND_ICON_BY_CODE = {
    "deleteConstant": ":material/cleaning_services:",
    "sleep": ":material/schedule:",
    "readApi": ":material/cloud_download:",
    "writeApi": ":material/cloud_upload:",
    "sendMessageQueue": ":material/send:",
    "saveTable": ":material/database_upload:",
    "dropTable": ":material/database_off:",
    "cleanTable": ":material/mop:",
    "exportDataset": ":material/tab_move:",
    "dropDataset": ":material/tab_close_inactive:",
    "cleanDataset": ":material/dishwasher:",
    "runSuite": ":material/rocket_launch:",
}
CONSTANT_SOURCE_ICON_BY_TYPE = {
    "value": ":material/raw_on:",
    "json": ":material/file_json:",
    "function": ":material/functions:",
}
ASSERT_PHRASE_BY_CODE = {
    "jsonEquals": "json equals",
    "jsonEmpty": "json is empty",
    "jsonNotEmpty": "json is not empty",
    "jsonContains": "json contains",
    "jsonArrayEquals": "jsonArray equals",
    "jsonArrayEmpty": "jsonArray is empty",
    "jsonArrayNotEmpty": "jsonArray is not empty",
    "jsonArrayContains": "jsonArray contains",
}
COMMAND_UI_LABELS = {
    "initConstant": "Runtime value",
    "deleteConstant": "Runtime value cleanup",
    "sleep": "Sleep",
    "readApi": "Read API",
    "writeApi": "Write API",
    "sendMessageQueue": "Send message queue",
    "saveTable": "Save table",
    "dropTable": "Drop table",
    "cleanTable": "Clean table",
    "exportDataset": "Export dataset",
    "dropDataset": "Drop dataset",
    "cleanDataset": "Clean dataset",
    "runSuite": "Run suite",
}
VARIABLE_UI_LABELS_BY_SOURCE_TYPE = {
    "value": "Value runtime variable",
    "json": "Json variable",
    "function": "Function runtime variable",
    "dataset": "Dataset source",
    "jsonArray": "Json array source",
}
VARIABLE_TYPE_LABELS_BY_SOURCE_TYPE = {
    "value": "value",
    "json": "json",
    "function": "function",
    "dataset": "dataset",
    "jsonArray": "json array",
}
COMMAND_GROUP_LABELS = {
    "context": "variable",
    "constant": "variable",
    "action": "action",
    "assert": "assert",
}
DATASET_PERIMETER_EDITOR_PAGE_PATH = "pages/DatasetPerimeterEditor.py"


def _safe_list(value: object) -> list[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    raw = str(value or "").strip()
    if not raw:
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def _normalize_context_path(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("$."):
        return raw
    if raw.startswith("$"):
        return f"$.{raw[1:].lstrip('.')}"
    return f"$.{raw.lstrip('.')}"


def _api_result_target_label(result_target: object) -> str:
    if isinstance(result_target, dict):
        configuration_json = _safe_dict(result_target)
        explicit_target = (
            configuration_json.get("result_target")
            or configuration_json.get("resultTarget")
        )
        if not explicit_target:
            result_constant = _safe_dict(
                configuration_json.get("resultConstant")
                or configuration_json.get("result_constant")
            )
            result_name = str(result_constant.get("name") or "").strip()
            if result_name:
                explicit_target = f"$.result.constants.{result_name}"
        result_target = explicit_target

    normalized_target = _normalize_context_path(result_target)
    if not normalized_target:
        return ""
    return str(normalized_target.rsplit(".", 1)[-1] or normalized_target).strip()


def _normalize_api_result_target_input(value: object) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    if raw_value.startswith("$"):
        return _normalize_context_path(raw_value)
    if "." in raw_value:
        return _normalize_context_path(raw_value)
    return f"$.result.constants.{raw_value}"


def _source_selection_value(path_value: object = None, source_code: object = None) -> str:
    normalized_source_code = str(source_code or "").strip()
    if normalized_source_code:
        return f"source:{normalized_source_code}"
    return _normalize_context_path(path_value)


def _apply_reference_selection(
    cfg: dict[str, object],
    *,
    selection: object,
    path_key: str,
    source_code_key: str,
) -> bool:
    raw = str(selection or "").strip()
    if not raw:
        return False
    if raw.startswith("source:"):
        source_code = raw.split(":", 1)[1].strip()
        if not source_code:
            return False
        cfg[source_code_key] = source_code
        return True
    normalized_path = _normalize_context_path(raw)
    if not normalized_path:
        return False
    cfg[path_key] = normalized_path
    return True


def _parse_json_input(value: object) -> tuple[object | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, (dict, list, int, float, bool)):
        return value, None
    raw = str(value or "").strip()
    if not raw:
        return None, None
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"JSON non valido: {str(exc)}"


def _parse_optional_json_object_input(value: object, field_label: str) -> tuple[dict | None, str | None]:
    raw = str(value or "").strip()
    if not raw:
        return None, None
    parsed_value, parse_error = _parse_json_input(raw)
    if parse_error:
        return None, parse_error.replace("JSON", field_label)
    if not isinstance(parsed_value, dict):
        return None, f"Il campo {field_label} deve essere un oggetto JSON."
    return parsed_value, None


def _parse_json_or_ref_input(value: object) -> tuple[object | None, str | None]:
    raw = str(value or "").strip()
    if not raw:
        return None, None
    if raw == "$" or raw.startswith("$."):
        return raw, None
    return _parse_json_input(raw)


def _parse_csv_tokens(value: object) -> list[str]:
    raw = str(value or "").replace(";", ",").replace("\n", ",")
    return [item.strip() for item in raw.split(",") if item and item.strip()]


def _normalize_compare_keys_input(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return _parse_csv_tokens(value)


def _format_lookup_label(item: dict, fallback_key: str = "id") -> str:
    return str(item.get("description") or item.get("code") or item.get(fallback_key) or "-")


def _source_type_label(source_type: str) -> str:
    return {
        "dataset": "Dataset",
        "jsonArray": "JSON Array",
    }.get(str(source_type or "").strip(), str(source_type or "-"))


def _normalized_value_type(configuration_json: dict) -> str:
    value_type = str(
        configuration_json.get("valueType")
        or configuration_json.get("value_type")
        or configuration_json.get("sourceType")
        or configuration_json.get("source_type")
        or ""
    ).strip()
    return "value" if value_type == "raw" else value_type


def _format_source_variable_option(item: dict) -> str:
    name = str(item.get("name") or item.get("code") or item.get("id") or "-").strip() or "-"
    value_type = str(item.get("value_type") or "").strip()
    variable_type = VARIABLE_TYPE_LABELS_BY_SOURCE_TYPE.get(value_type, value_type or "generic")
    return f"{name}:{variable_type}"


def _map_by_id(items: list[dict]) -> dict[str, dict]:
    return {
        str(item.get("id") or "").strip(): item
        for item in items
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }


def _safe_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _dataset_parameter_definitions(dataset_id: object) -> list[dict]:
    normalized_dataset_id = str(dataset_id or "").strip()
    if not normalized_dataset_id:
        return []
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    datasource_item = next(
        (
            item
            for item in datasources
            if str(item.get("id") or "").strip() == normalized_dataset_id
        ),
        None,
    )
    perimeter = datasource_item.get("perimeter") if isinstance(datasource_item, dict) else {}
    parameters = perimeter.get("parameters") if isinstance(perimeter, dict) else []
    return [item for item in parameters if isinstance(item, dict) and str(item.get("name") or "").strip()]


def _dataset_parameter_state_suffix(parameter_name: object) -> str:
    raw = str(parameter_name or "").strip()
    return "".join(char if char.isalnum() else "_" for char in raw) or "parameter"


def _dataset_parameter_form_key(prefix: str, dialog_nonce: int, parameter_name: str, field: str) -> str:
    return _command_form_key(
        prefix,
        dialog_nonce,
        f"init_constant_dataset_param_{field}_{_dataset_parameter_state_suffix(parameter_name)}",
    )


def _ensure_dataset_parameter_binding_state(
    key_prefix: str,
    dialog_nonce: int,
    dataset_id: object,
    existing_bindings: object | None = None,
):
    parameter_definitions = _dataset_parameter_definitions(dataset_id)
    bindings = existing_bindings if isinstance(existing_bindings, dict) else {}
    for parameter_definition in parameter_definitions:
        parameter_name = str(parameter_definition.get("name") or "").strip()
        if not parameter_name:
            continue
        mode_key = _dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "mode")
        literal_key = _dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "literal")
        source_key = _dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "source")
        built_in_key = _dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "built_in")
        if mode_key in st.session_state:
            continue
        binding = bindings.get(parameter_name)
        if isinstance(binding, dict):
            binding_kind = str(binding.get("kind") or "").strip().lower()
            if binding_kind == "constant_path":
                st.session_state[mode_key] = "constant"
                st.session_state[source_key] = str(binding.get("path") or "").strip()
                st.session_state[literal_key] = ""
                st.session_state[built_in_key] = "$now"
                continue
            if binding_kind == "built_in":
                st.session_state[mode_key] = "built_in"
                st.session_state[built_in_key] = str(binding.get("resolver") or "$now").strip() or "$now"
                st.session_state[literal_key] = ""
                st.session_state[source_key] = ""
                continue
        if binding is not None:
            st.session_state[mode_key] = "literal"
            st.session_state[literal_key] = _stringify_form_value(binding)
            st.session_state[source_key] = ""
            st.session_state[built_in_key] = "$now"
            continue
        st.session_state[mode_key] = "default"
        st.session_state[literal_key] = ""
        st.session_state[source_key] = ""
        st.session_state[built_in_key] = "$now"


def _build_dataset_parameter_bindings_from_state(
    key_prefix: str,
    dialog_nonce: int,
    dataset_id: object,
) -> tuple[dict | None, str | None]:
    parameter_definitions = _dataset_parameter_definitions(dataset_id)
    if not parameter_definitions:
        return None, None
    bindings: dict[str, object] = {}
    for parameter_definition in parameter_definitions:
        parameter_name = str(parameter_definition.get("name") or "").strip()
        if not parameter_name:
            continue
        mode = str(
            st.session_state.get(_dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "mode"))
            or "default"
        ).strip().lower()
        if mode == "default":
            continue
        if mode == "literal":
            literal_value, parse_error = _parse_json_input(
                st.session_state.get(_dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "literal"))
            )
            if parse_error:
                return None, f"Parameter '{parameter_name}': {parse_error}"
            bindings[parameter_name] = literal_value
            continue
        if mode == "constant":
            source_path = _normalize_context_path(
                st.session_state.get(_dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "source"))
            )
            if not source_path:
                return None, f"Parameter '{parameter_name}': source variable is required."
            bindings[parameter_name] = {
                "kind": "constant_path",
                "path": source_path,
            }
            continue
        if mode == "built_in":
            resolver = str(
                st.session_state.get(_dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "built_in"))
                or "$now"
            ).strip() or "$now"
            bindings[parameter_name] = {
                "kind": "built_in",
                "resolver": resolver,
            }
            continue
    return bindings or None, None


def _render_dataset_parameter_bindings_section(
    key_prefix: str,
    dialog_nonce: int,
    draft: dict,
    item: dict,
    dataset_id: object,
    stop_before_index: int | None,
):
    parameter_definitions = _dataset_parameter_definitions(dataset_id)
    if not parameter_definitions:
        st.info("The selected dataset does not expose parameters.")
        return
    constant_options = [
        definition
        for definition in _resolve_available_source_constants(
            draft,
            item,
            command_code="saveTable",
            stop_before_index=stop_before_index,
        )
        if str(definition.get("value_type") or "").strip() not in {"dataset", "jsonArray"}
    ]
    st.caption("Parameter bindings")
    for parameter_definition in parameter_definitions:
        parameter_name = str(parameter_definition.get("name") or "").strip()
        if not parameter_name:
            continue
        parameter_type = str(parameter_definition.get("type") or "").strip()
        with st.container(border=True):
            st.markdown(f"**{parameter_name}** `{parameter_type}`")
            mode_key = _dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "mode")
            literal_key = _dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "literal")
            source_key = _dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "source")
            built_in_key = _dataset_parameter_form_key(key_prefix, dialog_nonce, parameter_name, "built_in")
            mode = st.selectbox(
                "Binding mode",
                options=["default", "literal", "constant", "built_in"],
                key=mode_key,
                format_func=lambda value: {
                    "default": "Dataset default",
                    "literal": "Literal",
                    "constant": "Visible constant",
                    "built_in": "Built-in",
                }.get(str(value), str(value)),
            )
            if mode == "literal":
                st.text_area(
                    "Literal value",
                    key=literal_key,
                    height=100,
                    help="Use JSON for structured values; plain text is stored as string.",
                )
            elif mode == "constant":
                _render_source_constant_select(
                    label="Visible constant",
                    key=source_key,
                    options=constant_options,
                    help_text="Visible and compatible variables at this point.",
                )
            elif mode == "built_in":
                st.selectbox(
                    "Built-in",
                    options=["$now", "$today"],
                    key=built_in_key,
                )


def _command_form_key(prefix: str, dialog_nonce: int, field: str) -> str:
    return f"{prefix}_{field}_{dialog_nonce}"


def _normalize_command_code(configuration_json: dict | None) -> str:
    cfg = _safe_dict(configuration_json)
    raw = str(cfg.get("commandCode") or cfg.get("command_code") or "").strip()
    if raw == "setVariable":
        return "initConstant"
    if raw == "deleteVariable":
        return "deleteConstant"
    return raw


def _normalize_command_type(configuration_json: dict | None) -> str:
    cfg = _safe_dict(configuration_json)
    return str(cfg.get("commandType") or cfg.get("command_type") or "").strip().lower()


def _stringify_form_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, indent=2)


def _csv_from_value(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _assert_expected_mode_label(mode: str) -> str:
    normalized = str(mode or "").strip().lower()
    return ASSERT_EXPECTED_MODE_LABELS.get(normalized, normalized or "Expected source")


def _extract_expected_ref_path(value: object) -> str:
    if isinstance(value, dict):
        ref = str(value.get("$ref") or "").strip()
        if ref == "$" or ref.startswith("$."):
            return ref
        return ""
    raw = str(value or "").strip()
    if raw == "$" or raw.startswith("$."):
        return raw
    return ""


def _normalize_json_path_input(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw == "$":
        return raw
    if raw.startswith("$."):
        return raw
    if raw.startswith("$"):
        return f"$.{raw[1:].lstrip('.')}"
    return f"$.{raw.lstrip('.')}"


def _json_object_keys(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    return [str(key).strip() for key in value.keys() if str(key).strip()]


def _resolve_expected_json_array_payload(
    json_arrays: list[dict],
    expected_json_array_id: object,
) -> tuple[object | None, str | None]:
    normalized_id = str(expected_json_array_id or "").strip()
    if not normalized_id:
        return None, "Il campo Expected json-array e' obbligatorio."
    json_array_item = next(
        (item for item in json_arrays if str(item.get("id") or "").strip() == normalized_id),
        None,
    )
    if not isinstance(json_array_item, dict):
        return None, "Expected json-array non trovato."
    return json_array_item.get("payload"), None


def _resolve_expected_json_array_compare_keys(
    json_arrays: list[dict],
    expected_json_array_id: object,
) -> tuple[list[str], str | None]:
    payload, error = _resolve_expected_json_array_payload(json_arrays, expected_json_array_id)
    if error:
        return [], error
    if isinstance(payload, dict):
        keys = _json_object_keys(payload)
        if not keys:
            return [], "Expected json-array deve contenere un oggetto JSON con campi selezionabili."
        return keys, None
    if not isinstance(payload, list) or not payload:
        return [], "Expected json-array deve contenere almeno un elemento."
    first_item = payload[0]
    keys = _json_object_keys(first_item)
    if not keys:
        return [], "Il primo elemento di Expected json-array deve essere un oggetto JSON."
    return keys, None


def _find_broker_id_for_queue_id(queue_id: str, brokers: list[dict]) -> str:
    normalized_queue_id = str(queue_id or "").strip()
    if not normalized_queue_id:
        return ""
    for broker in brokers:
        broker_id = str(broker.get("id") or "").strip()
        if not broker_id:
            continue
        queues = load_test_editor_queues_for_broker(broker_id, force=False)
        if any(str(queue.get("id") or "").strip() == normalized_queue_id for queue in queues):
            return broker_id
    return ""


def _section_type_for_item(item: dict | None) -> str:
    if not isinstance(item, dict):
        return "test"
    if str(item.get("kind") or "").strip().lower() != "hook":
        return "test"
    mapping = {
        "before-all": "beforeAll",
        "before-each": "beforeEach",
        "after-each": "afterEach",
        "after-all": "afterAll",
    }
    return mapping.get(str(item.get("hook_phase") or "").strip().lower(), "test")


def _find_hook_by_phase(draft: dict, hook_phase: str) -> dict | None:
    hooks = draft.get("hooks") or {}
    if not isinstance(hooks, dict):
        return None
    hook = hooks.get(hook_phase)
    return hook if isinstance(hook, dict) else None


def _operation_list(item: dict | None) -> list[dict]:
    operations = item.get("operations") if isinstance(item, dict) else []
    return [operation for operation in operations if isinstance(operation, dict)] if isinstance(operations, list) else []


def _command_result_constant(configuration_json: dict) -> tuple[str, str] | None:
    result_constant = _safe_dict(
        configuration_json.get("resultConstant") or configuration_json.get("result_constant")
    )
    result_name = str(result_constant.get("name") or "").strip()
    result_type = str(
        result_constant.get("valueType") or result_constant.get("value_type") or "json"
    ).strip() or "json"
    if result_name:
        return result_name, result_type

    result_target = _normalize_context_path(
        configuration_json.get("result_target") or configuration_json.get("resultTarget")
    )
    if result_target.startswith("$.result.constants."):
        return result_target.split(".")[-1], "json"
    return None


def _apply_visible_constant_effect(active_definitions: list[dict], operation: dict):
    configuration_json = _safe_dict(operation.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json)

    if command_code == "deleteConstant":
        target_definition_id = str(
            configuration_json.get("definitionId") or configuration_json.get("definition_id") or ""
        ).strip()
        target_name = str(configuration_json.get("name") or "").strip()
        target_context = str(
            configuration_json.get("context") or configuration_json.get("scope") or ""
        ).strip()
        if target_name and target_context:
            for index in range(len(active_definitions) - 1, -1, -1):
                definition = active_definitions[index]
                if target_definition_id and str(definition.get("definitionId") or "").strip() == target_definition_id:
                    active_definitions.pop(index)
                    break
                if (
                    str(definition.get("name") or "").strip() == target_name
                    and str(definition.get("context") or "").strip() == target_context
                ):
                    active_definitions.pop(index)
                    break
        return

    if command_code == "initConstant":
        name = str(configuration_json.get("name") or "").strip()
        context = str(
            configuration_json.get("context") or configuration_json.get("scope") or ""
        ).strip()
        source_type = _normalized_value_type(configuration_json)
        if name and context and source_type:
            preview_value = configuration_json.get("value") if source_type in {"json", "raw", "value"} else None
            active_definitions.append(
                {
                    "definitionId": str(
                        configuration_json.get("definitionId") or configuration_json.get("definition_id") or ""
                    ).strip() or f"$.{context}.constants.{name}",
                    "name": name,
                    "context": context,
                    "value_type": source_type,
                    "path": f"$.{context}.constants.{name}",
                    "preview_value": deepcopy(preview_value),
                    "source_reference_id": str(
                        configuration_json.get("json_array_id")
                        or configuration_json.get("jsonArrayId")
                        or configuration_json.get("dataset_id")
                        or configuration_json.get("datasetId")
                        or ""
                    ).strip(),
                }
            )

    result_constant = _command_result_constant(configuration_json)
    if result_constant is not None:
        result_name, result_type = result_constant
        explicit_result_constant = _safe_dict(
            configuration_json.get("resultConstant") or configuration_json.get("result_constant")
        )
        active_definitions.append(
            {
                "definitionId": str(
                    explicit_result_constant.get("definitionId")
                    or explicit_result_constant.get("definition_id")
                    or ""
                ).strip() or f"$.result.constants.{result_name}",
                "name": result_name,
                "context": "result",
                "value_type": result_type,
                "path": f"$.result.constants.{result_name}",
                "preview_value": None,
                "source_reference_id": "",
            }
        )


def _collect_visible_constants_from_operations(
    active_definitions: list[dict],
    item: dict | None,
    *,
    stop_before_index: int | None = None,
):
    operations = _operation_list(item)
    for op_index, operation in enumerate(operations):
        if stop_before_index is not None and op_index >= stop_before_index:
            break
        _apply_visible_constant_effect(active_definitions, operation)


def _source_list(item: dict | None) -> list[dict]:
    if not isinstance(item, dict):
        return []
    return [source for source in _safe_list(item.get("sources")) if str(source.get("sourceCode") or "").strip()]


def _find_source_index_by_code(item: dict | None, source_code: object) -> tuple[int, dict | None]:
    normalized_source_code = str(source_code or "").strip()
    if not normalized_source_code:
        return -1, None
    for index, source in enumerate(_source_list(item)):
        if str(source.get("sourceCode") or "").strip() == normalized_source_code:
            return index, source
    return -1, None


def _append_source_to_item(item: dict, source_item: dict):
    if not isinstance(item, dict) or not isinstance(source_item, dict):
        return
    sources = item.get("sources")
    if not isinstance(sources, list):
        sources = []
        item["sources"] = sources
    sources.append(deepcopy(source_item))


def _update_source_in_item(item: dict, source_index: int, updated_source: dict):
    if not isinstance(item, dict) or not isinstance(updated_source, dict):
        return
    sources = item.get("sources")
    if not isinstance(sources, list) or not (0 <= source_index < len(sources)):
        return
    sources[source_index] = deepcopy(updated_source)


def _delete_source_by_code(item: dict | None, source_code: object) -> bool:
    if not isinstance(item, dict):
        return False
    source_index, _source = _find_source_index_by_code(item, source_code)
    sources = item.get("sources")
    if not isinstance(sources, list) or not (0 <= source_index < len(sources)):
        return False
    sources.pop(source_index)
    return True


def append_operation_to_test(item: dict, operation_item: dict):
    if not isinstance(item, dict) or not isinstance(operation_item, dict):
        return
    operations = item.get("operations")
    if not isinstance(operations, list):
        operations = []
        item["operations"] = operations
    operations.append(
        {
            **deepcopy(operation_item),
            "_ui_key": str(operation_item.get("_ui_key") or new_ui_key()),
        }
    )
    item["operations"] = _resequence_operations(operations)


def _validate_source_code_for_item(
    item: dict | None,
    source_code: object,
    *,
    ignore_source_code: object = None,
) -> str | None:
    normalized_source_code = str(source_code or "").strip()
    if not normalized_source_code:
        return "Il campo Source code e' obbligatorio."
    ignored_source_code = str(ignore_source_code or "").strip()
    existing_codes = {
        str(source.get("sourceCode") or "").strip()
        for source in _source_list(item)
        if str(source.get("sourceCode") or "").strip()
        and str(source.get("sourceCode") or "").strip() != ignored_source_code
    }
    if normalized_source_code in existing_codes:
        return f"Source code '{normalized_source_code}' gia' presente in questa sezione."
    return None


def _build_source_option(source: dict) -> dict:
    source_code = str(source.get("sourceCode") or "").strip()
    source_type = str(source.get("sourceType") or "").strip()
    reference_id = str(
        source.get("jsonArrayId")
        or source.get("datasetId")
        or source.get("json_array_id")
        or source.get("dataset_id")
        or ""
    ).strip()
    preview_value = None
    if source_type == "jsonArray":
        json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
        json_array = _map_by_id(json_arrays).get(reference_id, {})
        preview_value = deepcopy(json_array.get("payload")) if isinstance(json_array, dict) else None
    return {
        "name": source_code,
        "code": source_code,
        "context": "source",
        "value_type": source_type,
        "path": f"source:{source_code}",
        "preview_value": preview_value,
        "source_reference_id": reference_id,
        "source_code": source_code,
        "is_source": True,
    }


def _source_state_suffix(*parts: object) -> str:
    raw = "_".join(str(part or "").strip() for part in parts if str(part or "").strip())
    sanitized = "".join(char if char.isalnum() else "_" for char in raw)
    return sanitized or "source"


def _source_preview_toggle_key(item: dict | None, source: dict | None) -> str:
    item_ui_key = str((item or {}).get("_ui_key") or "").strip()
    source_code = str((source or {}).get("sourceCode") or "").strip()
    return f"suite_editor_source_preview_visible_{_source_state_suffix(item_ui_key, source_code)}"


def _is_source_preview_visible(item: dict | None, source: dict | None) -> bool:
    return bool(st.session_state.get(_source_preview_toggle_key(item, source), False))


def _toggle_source_preview(item: dict | None, source: dict | None) -> bool:
    key = _source_preview_toggle_key(item, source)
    next_value = not bool(st.session_state.get(key, False))
    st.session_state[key] = next_value
    return next_value


def _source_preview_cache_bucket() -> dict:
    cache = st.session_state.get(SOURCE_PREVIEW_CACHE_KEY)
    if isinstance(cache, dict):
        return cache
    cache = {}
    st.session_state[SOURCE_PREVIEW_CACHE_KEY] = cache
    return cache


def _source_preview_cache_key(source: dict) -> str:
    return json.dumps(source, ensure_ascii=True, sort_keys=True)


def _load_source_preview(source: dict, *, force: bool = False) -> dict:
    cache = _source_preview_cache_bucket()
    cache_key = _source_preview_cache_key(source)
    if force or cache_key not in cache:
        try:
            cache[cache_key] = preview_suite_source_via_api(source=source)
        except Exception as exc:
            cache[cache_key] = {"error": str(exc)}
    payload = cache.get(cache_key)
    return payload if isinstance(payload, dict) else {}


def _connection_labels_by_id() -> dict[str, str]:
    load_database_connections(force=False)
    connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))
    return {
        str(item.get("id") or "").strip(): build_connection_label(item)
        for item in connections
        if str(item.get("id") or "").strip()
    }


def _resolve_dataset_source_details(source: dict) -> dict:
    normalized_dataset_id = str(source.get("datasetId") or "").strip()
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    datasource_item = _map_by_id(datasources).get(normalized_dataset_id, {})
    if not datasource_item:
        return {
            "description": normalized_dataset_id or "-",
            "connection_label": "-",
            "schema": "-",
            "object_label": "-",
        }
    return build_dataset_summary(datasource_item, _connection_labels_by_id())


def _resolve_json_array_source_details(source: dict) -> dict:
    normalized_json_array_id = str(source.get("jsonArrayId") or "").strip()
    json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    json_array_item = _map_by_id(json_arrays).get(normalized_json_array_id, {})
    payload = json_array_item.get("payload") if isinstance(json_array_item, dict) else None
    items_count = len(payload) if isinstance(payload, list) else (1 if payload is not None else 0)
    return {
        "description": _format_lookup_label(json_array_item, fallback_key="code")
        if json_array_item
        else (normalized_json_array_id or "-"),
        "code": str(json_array_item.get("code") or "").strip() if json_array_item else "",
        "items_count": items_count,
    }


def _render_dataset_source_preview(source: dict, *, force: bool = False):
    perimeter = source.get("perimeter") if isinstance(source.get("perimeter"), dict) else None
    filter_text = build_filter_text(perimeter)
    sort_text = build_sort_text(perimeter)
    if filter_text:
        st.caption(f"Filters: {filter_text}")
    if sort_text:
        st.caption(f"Sort: {sort_text}")
    selected_columns = [
        str(column).strip()
        for column in (perimeter or {}).get("selected_columns", [])
        if str(column).strip()
    ]
    if selected_columns:
        st.caption(f"Columns: {', '.join(selected_columns)}")

    preview_payload = _load_source_preview(source, force=force)
    if str(preview_payload.get("error") or "").strip():
        st.error(str(preview_payload.get("error") or "").strip())
        return
    rows = preview_payload.get("rows") if isinstance(preview_payload.get("rows"), list) else []
    if rows:
        st.dataframe(rows, use_container_width=True, height=320)
        return
    st.info("Nessun dato disponibile per la preview.")


def _render_json_array_source_preview(source: dict, *, force: bool = False):
    preview_payload = _load_source_preview(source, force=force)
    if str(preview_payload.get("error") or "").strip():
        st.error(str(preview_payload.get("error") or "").strip())
        return
    payload = preview_payload.get("payload")
    st.json(payload if payload is not None else [], expanded=False)


def _render_source_preview_content(source: dict, *, force: bool = False):
    source_type = str(source.get("sourceType") or "").strip()
    if source_type == "dataset":
        _render_dataset_source_preview(source, force=force)
        return
    if source_type == "jsonArray":
        _render_json_array_source_preview(source, force=force)
        return
    st.info("Preview non disponibile per questo source type.")

def _collect_visible_source_options(
    draft: dict,
    item: dict,
) -> list[dict]:
    section_type = _section_type_for_item(item)
    visible_sources: list[dict] = []
    before_all_hook = _find_hook_by_phase(draft, "before-all")
    before_each_hook = _find_hook_by_phase(draft, "before-each")

    if section_type in {"beforeAll", "beforeEach", "test", "afterAll"}:
        visible_sources.extend(_build_source_option(source) for source in _source_list(before_all_hook))
    if section_type in {"beforeEach", "test", "afterEach"}:
        visible_sources.extend(_build_source_option(source) for source in _source_list(before_each_hook))
    visible_sources.extend(_build_source_option(source) for source in _source_list(item))

    deduped_by_code: dict[str, dict] = {}
    for source in visible_sources:
        source_code = str(source.get("source_code") or "").strip()
        if source_code:
            deduped_by_code[source_code] = source
    return list(deduped_by_code.values())


def _resolve_available_source_constants(
    draft: dict,
    item: dict,
    *,
    command_code: str,
    stop_before_index: int | None = None,
) -> list[dict]:
    active_definitions: list[dict] = []
    section_type = _section_type_for_item(item)

    before_all_hook = _find_hook_by_phase(draft, "before-all")
    before_each_hook = _find_hook_by_phase(draft, "before-each")

    if section_type in {"beforeEach", "test", "afterEach", "afterAll"}:
        _collect_visible_constants_from_operations(active_definitions, before_all_hook)

    if section_type in {"beforeEach", "test", "afterEach"}:
        _collect_visible_constants_from_operations(active_definitions, before_each_hook)

    if section_type in {"beforeAll", "beforeEach", "afterEach", "afterAll", "test"}:
        _collect_visible_constants_from_operations(
            active_definitions,
            item,
            stop_before_index=stop_before_index,
        )

    filtered_definitions = [
        definition
        for definition in active_definitions
        if str(definition.get("context") or "").strip()
        in READABLE_SCOPES_BY_SECTION.get(section_type, set())
    ]

    deduped_by_path: dict[str, dict] = {}
    for definition in filtered_definitions:
        path = str(definition.get("path") or "").strip()
        if path:
            deduped_by_path[path] = definition

    options = list(deduped_by_path.values())
    options.extend(_collect_visible_source_options(draft, item))
    options.sort(
        key=lambda item: (
            str(item.get("context") or ""),
            str(item.get("name") or ""),
            str(item.get("value_type") or ""),
        )
    )
    compatible_types = SOURCE_COMPATIBILITY_BY_COMMAND.get(str(command_code or "").strip(), set())
    if not compatible_types:
        return []
    return [
        definition
        for definition in options
        if str(definition.get("value_type") or "").strip() in compatible_types
    ]


def _resolve_available_http_form_runtime_constants(
    draft: dict,
    item: dict,
    *,
    stop_before_index: int | None = None,
) -> list[dict]:
    options = _resolve_available_source_constants(
        draft,
        item,
        command_code="sendMessageQueue",
        stop_before_index=stop_before_index,
    )
    return [
        definition
        for definition in options
        if str(definition.get("context") or "").strip() != "source"
        and str(definition.get("value_type") or "").strip() not in {"dataset", "jsonArray"}
    ]


def _resolve_available_assert_constants(
    draft: dict,
    item: dict,
    *,
    command_code: str,
    stop_before_index: int | None = None,
    role: str = "actual",
) -> list[dict]:
    compatible_by_command = (
        ASSERT_EXPECTED_COMPATIBILITY_BY_COMMAND
        if str(role or "").strip().lower() == "expected"
        else ASSERT_ACTUAL_COMPATIBILITY_BY_COMMAND
    )
    compatible_types = compatible_by_command.get(str(command_code or "").strip(), set())
    if not compatible_types:
        return []

    visible_constants = _resolve_available_source_constants(
        draft,
        item,
        command_code="sendMessageQueue",
        stop_before_index=stop_before_index,
    )
    filtered = [
        definition
        for definition in visible_constants
        if str(definition.get("value_type") or "").strip() in compatible_types
    ]
    if str(role or "").strip().lower() == "expected" and str(command_code or "").strip() == "jsonContains":
        filtered = [
            definition
            for definition in filtered
            if isinstance(definition.get("preview_value"), dict)
    ]
    return filtered


def _render_add_source_form(
    dialog_nonce: int,
    datasources: list[dict],
    json_arrays: list[dict],
    *,
    key_prefix: str,
):
    st.text_input(
        "Source code",
        key=_command_form_key(key_prefix, dialog_nonce, "source_code"),
        placeholder="ordersSource",
    )
    source_type_key = _command_form_key(key_prefix, dialog_nonce, "source_type")
    current_source_type = str(st.session_state.get(source_type_key) or "").strip()
    if current_source_type not in DECLARATIVE_SOURCE_OPTIONS:
        st.session_state[source_type_key] = DECLARATIVE_SOURCE_OPTIONS[0]
    source_type = st.selectbox(
        "Source type",
        options=DECLARATIVE_SOURCE_OPTIONS,
        key=source_type_key,
        format_func=_source_type_label,
    )

    if source_type == "dataset":
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Dataset",
            options=dataset_ids or [""],
            format_func=lambda item_id: _format_lookup_label(
                next((item for item in datasources if str(item.get("id")) == str(item_id)), {})
            ) if item_id else "Nessun dataset disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "dataset_id"),
            disabled=not bool(dataset_ids),
        )
    else:
        json_array_ids = [str(item.get("id")) for item in json_arrays if item.get("id")]
        st.selectbox(
            "JSON Array",
            options=json_array_ids or [""],
            format_func=lambda item_id: _format_lookup_label(
                next((item for item in json_arrays if str(item.get("id")) == str(item_id)), {})
            ) if item_id else "Nessun JSON Array disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "json_array_id"),
            disabled=not bool(json_array_ids),
        )


def _build_preview_source_draft_with_prefix(
    dialog_nonce: int,
    datasources: list[dict],
    json_arrays: list[dict],
    *,
    key_prefix: str,
) -> tuple[dict | None, str | None]:
    source_type = str(
        st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "source_type")) or "dataset"
    ).strip()
    if source_type == "dataset":
        dataset_id = str(
            st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "dataset_id")) or ""
        ).strip()
        if not dataset_id:
            return None, "Seleziona un dataset per vedere la preview."
        datasource_item = _map_by_id(datasources).get(dataset_id)
        if not isinstance(datasource_item, dict):
            return None, "Il dataset selezionato non e' disponibile."
        perimeter = datasource_item.get("perimeter")
        return {
            "sourceCode": "__preview__",
            "sourceType": "dataset",
            "datasetId": dataset_id,
            "perimeter": deepcopy(perimeter) if isinstance(perimeter, dict) else {},
        }, None
    if source_type == "jsonArray":
        json_array_id = str(
            st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "json_array_id")) or ""
        ).strip()
        if not json_array_id:
            return None, "Seleziona un JSON Array per vedere la preview."
        json_array_item = _map_by_id(json_arrays).get(json_array_id)
        if not isinstance(json_array_item, dict):
            return None, "Il JSON Array selezionato non e' disponibile."
        return {
            "sourceCode": "__preview__",
            "sourceType": "jsonArray",
            "jsonArrayId": json_array_id,
        }, None
    return None, "Source type non supportato."


def _render_add_source_preview(
    dialog_nonce: int,
    datasources: list[dict],
    json_arrays: list[dict],
    *,
    key_prefix: str,
):
    st.caption("Selected source preview")
    preview_source, preview_error = _build_preview_source_draft_with_prefix(
        dialog_nonce,
        datasources,
        json_arrays,
        key_prefix=key_prefix,
    )
    if preview_error:
        st.info(preview_error)
        return
    with st.container(border=True):
        _render_source_preview_content(preview_source or {})


def _build_source_draft_with_prefix(
    dialog_nonce: int,
    datasources: list[dict],
    json_arrays: list[dict],
    *,
    key_prefix: str,
) -> tuple[dict | None, str | None]:
    source_code = str(
        st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "source_code")) or ""
    ).strip()
    source_code_error = _validate_source_code_for_item(None, source_code)
    if source_code_error:
        return None, source_code_error

    source_type = str(
        st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "source_type")) or "dataset"
    ).strip()
    if source_type == "dataset":
        dataset_id = str(
            st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "dataset_id")) or ""
        ).strip()
        if not dataset_id:
            return None, "Il campo Dataset e' obbligatorio."
        datasource_item = _map_by_id(datasources).get(dataset_id)
        if not isinstance(datasource_item, dict):
            return None, "Il dataset selezionato non e' disponibile."
        perimeter = datasource_item.get("perimeter")
        return {
            "sourceCode": source_code,
            "sourceType": "dataset",
            "datasetId": dataset_id,
            "perimeter": deepcopy(perimeter) if isinstance(perimeter, dict) else {},
        }, None
    if source_type == "jsonArray":
        json_array_id = str(
            st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "json_array_id")) or ""
        ).strip()
        if not json_array_id:
            return None, "Il campo JSON Array e' obbligatorio."
        json_array_item = _map_by_id(json_arrays).get(json_array_id)
        if not isinstance(json_array_item, dict):
            return None, "Il JSON Array selezionato non e' disponibile."
        return {
            "sourceCode": source_code,
            "sourceType": "jsonArray",
            "jsonArrayId": json_array_id,
        }, None
    return None, "Source type non supportato."


def _dataset_mapping_key_options(datasource_item: dict) -> list[str]:
    perimeter = datasource_item.get("perimeter")
    if isinstance(perimeter, dict):
        selected_columns = perimeter.get("selected_columns")
        if isinstance(selected_columns, list):
            return [str(column).strip() for column in selected_columns if str(column).strip()]
    return []


def _resolve_export_dataset_mapping_key_options(
    draft: dict,
    item: dict,
    *,
    source_path: object,
    stop_before_index: int | None,
    json_arrays: list[dict],
    datasources: list[dict],
) -> tuple[list[str], str | None]:
    normalized_source = str(source_path or "").strip()
    if not normalized_source:
        return [], None

    visible_constants = _resolve_available_source_constants(
        draft,
        item,
        command_code="exportDataset",
        stop_before_index=stop_before_index,
    )
    source_definition = next(
        (
            definition
            for definition in visible_constants
            if str(definition.get("path") or "").strip() == normalized_source
        ),
        None,
    )
    if not isinstance(source_definition, dict):
        return [], None

    source_type = str(source_definition.get("value_type") or "").strip()
    if source_type == "json":
        keys = _json_object_keys(source_definition.get("preview_value"))
        return keys, None if keys else "La variabile json selezionata non espone campi selezionabili."

    source_reference_id = str(source_definition.get("source_reference_id") or "").strip()
    if source_type == "jsonArray":
        keys, error = _resolve_expected_json_array_compare_keys(json_arrays, source_reference_id)
        if error == "Il campo Expected json-array e' obbligatorio.":
            return [], "La variabile json array selezionata non e' collegata a un json-array."
        return keys, error

    if source_type == "dataset":
        datasource_item = next(
            (candidate for candidate in datasources if str(candidate.get("id") or "").strip() == source_reference_id),
            None,
        )
        if not isinstance(datasource_item, dict):
            return [], "Il dataset selezionato non e' disponibile."
        keys = _dataset_mapping_key_options(datasource_item)
        return keys, None if keys else "Il dataset selezionato non espone colonne nel perimeter."

    return [], None


def _resolve_send_message_source_definition(
    source_options: list[dict],
    source_path: object,
) -> dict | None:
    normalized_source_path = str(source_path or "").strip()
    if not normalized_source_path:
        return None
    return next(
        (
            item
            for item in source_options
            if str(item.get("path") or "").strip() == normalized_source_path
        ),
        None,
    )


def _parse_message_template_constants(value: object) -> tuple[list[dict], str | None]:
    if value is None:
        return [], None
    if not isinstance(value, list):
        return [], "Message template constants must be a table of rows."

    parsed_constants: list[dict] = []
    for raw_item in value:
        if not isinstance(raw_item, dict):
            return [], "Each message template constant row must be an object."
        field_name = str(raw_item.get("field") or raw_item.get("name") or "").strip()
        field_type = str(raw_item.get("type") or raw_item.get("kind") or "").strip().lower()
        field_value = raw_item.get("value")
        if not field_name and not field_type and (field_value is None or str(field_value).strip() == ""):
            continue
        if field_type == "booleano":
            field_type = "boolean"
        if not field_name:
            return [], "Template constant field is required."
        if field_type not in {"string", "number", "date", "datetime", "boolean"}:
            return [], "Template constant type is not supported."
        parsed_constants.append(
            {
                "name": field_name,
                "kind": field_type,
                "value": field_value,
            }
        )
    return parsed_constants, None


def _resolve_send_message_template_preview_rows(
    source_definition: dict | None,
    *,
    for_each: object,
    json_arrays: list[dict],
    datasources: list[dict],
) -> tuple[list[dict], list[str], str | None]:
    if not isinstance(source_definition, dict):
        return [], [], None

    source_type = str(source_definition.get("value_type") or "").strip()
    source_reference_id = str(source_definition.get("source_reference_id") or "").strip()
    if source_type == "dataset":
        datasource_item = next(
            (
                item
                for item in datasources
                if str(item.get("id") or "").strip() == source_reference_id
            ),
            None,
        )
        if not isinstance(datasource_item, dict):
            return [], [], "Selected dataset is not available."
        field_options = _dataset_mapping_key_options(datasource_item)
        preview_rows = [{field_name: f"<{field_name}>" for field_name in field_options[:10]}] if field_options else []
        return preview_rows, field_options, None if field_options else "Selected dataset does not expose perimeter columns."

    preview_source = source_definition.get("preview_value")
    if source_type == "jsonArray":
        preview_source, error = _resolve_expected_json_array_payload(json_arrays, source_reference_id)
        if error:
            return [], [], error
    if source_type not in {"json", "jsonArray"}:
        return [], [], "Message template preview is available only for json, jsonArray and dataset sources."

    try:
        preview_rows = preview_send_message_template_rows_via_api(
            input_data=preview_source,
            source_type=source_type,
            for_each=for_each,
        )
    except Exception as exc:
        return [], [], f"Unable to load message template preview: {str(exc)}"
    field_options = sorted(
        {
            str(field_name).strip()
            for row in preview_rows
            for field_name in row.keys()
            if str(field_name).strip()
        }
    )
    if not preview_rows:
        return [], [], "No preview rows available for the selected forEach path."
    return preview_rows, field_options, None


def _resolve_send_message_preview_payload(
    *,
    key_prefix: str,
    dialog_nonce: int,
    source_definition: dict | None,
    json_arrays: list[dict],
    datasources: list[dict],
) -> tuple[object | None, str | None]:
    if not isinstance(source_definition, dict):
        return None, None

    template_enabled = bool(
        st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "send_message_template_enabled"))
    )
    if template_enabled:
        preview_rows, _field_options, preview_error = _resolve_send_message_template_preview_rows(
            source_definition,
            for_each=st.session_state.get(
                _command_form_key(key_prefix, dialog_nonce, "send_message_template_for_each")
            ),
            json_arrays=json_arrays,
            datasources=datasources,
        )
        if preview_error:
            return None, preview_error

        preview_constants, constants_error = _parse_message_template_constants(
            st.session_state.get(
                _command_form_key(key_prefix, dialog_nonce, "send_message_template_constants_rows")
            )
        )
        if constants_error:
            return None, constants_error

        preview_payload = {
            field_name: preview_rows[0].get(field_name)
            for field_name in _normalize_compare_keys_input(
                st.session_state.get(
                    _command_form_key(key_prefix, dialog_nonce, "send_message_template_fields")
                )
            )
            if preview_rows and field_name in preview_rows[0]
        }
        for constant in preview_constants:
            constant_name = str(constant.get("name") or "").strip()
            if constant_name:
                preview_payload[constant_name] = constant.get("value")
        if preview_payload:
            return preview_payload, None
        return None, "No message preview available for the configured template."

    source_type = str(source_definition.get("value_type") or "").strip()
    source_reference_id = str(source_definition.get("source_reference_id") or "").strip()
    if source_type == "jsonArray":
        preview_payload, error = _resolve_expected_json_array_payload(json_arrays, source_reference_id)
        if error:
            return None, error
        return preview_payload, None if preview_payload is not None else "Selected json array does not expose a preview."
    if source_type == "dataset":
        preview_rows, _field_options, preview_error = _resolve_send_message_template_preview_rows(
            source_definition,
            for_each=None,
            json_arrays=json_arrays,
            datasources=datasources,
        )
        if preview_error:
            return None, preview_error
        return preview_rows[0], None if preview_rows else "Selected dataset does not expose a preview."

    preview_payload = source_definition.get("preview_value")
    if preview_payload is not None:
        return preview_payload, None
    return None, "Selected source variable does not expose a preview."


def _render_send_message_preview(
    *,
    key_prefix: str,
    dialog_nonce: int,
    source_options: list[dict],
    json_arrays: list[dict],
    datasources: list[dict],
):
    source_definition = _resolve_send_message_source_definition(
        source_options,
        st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "send_message_source")),
    )
    preview_payload, preview_error = _resolve_send_message_preview_payload(
        key_prefix=key_prefix,
        dialog_nonce=dialog_nonce,
        source_definition=source_definition,
        json_arrays=json_arrays,
        datasources=datasources,
    )
    st.caption("Message send preview")
    if preview_payload is not None:
        st.json(preview_payload, expanded=True)
    elif preview_error:
        st.info(preview_error)


def _send_message_template_constant_rows(value: object) -> list[dict]:
    constants = value if isinstance(value, list) else []
    if not constants and hasattr(value, "to_dict"):
        try:
            constants = value.to_dict(orient="records")
        except TypeError:
            try:
                constants = value.to_dict("records")
            except TypeError:
                constants = []
    rows: list[dict] = []
    for constant in constants:
        if not isinstance(constant, dict):
            continue
        raw_kind = str(constant.get("kind") or constant.get("type") or "").strip().lower()
        normalized_kind = "boolean" if raw_kind in {"booleano", "boolean"} else raw_kind
        rows.append(
            {
                "field": str(constant.get("name") or constant.get("field") or "").strip(),
                "type": normalized_kind or "string",
                "value": constant.get("value"),
            }
        )
    return rows


def _render_send_message_template_section(
    *,
    key_prefix: str,
    dialog_nonce: int,
    source_options: list[dict],
    json_arrays: list[dict],
    datasources: list[dict],
):
    enabled_key = _command_form_key(key_prefix, dialog_nonce, "send_message_template_enabled")
    for_each_key = _command_form_key(key_prefix, dialog_nonce, "send_message_template_for_each")
    fields_key = _command_form_key(key_prefix, dialog_nonce, "send_message_template_fields")
    constants_key = _command_form_key(key_prefix, dialog_nonce, "send_message_template_constants_rows")
    constants_editor_key = _command_form_key(key_prefix, dialog_nonce, "send_message_template_constants_editor")
    source_key = _command_form_key(key_prefix, dialog_nonce, "send_message_source")

    source_definition = _resolve_send_message_source_definition(
        source_options,
        st.session_state.get(source_key),
    )
    source_type = str((source_definition or {}).get("value_type") or "").strip()
    template_supported = source_type in {"json", "jsonArray", "dataset"}

    st.checkbox("Enable message template", key=enabled_key)
    if not bool(st.session_state.get(enabled_key)):
        return

    if not template_supported:
        st.info("Message template is available only for json, jsonArray and dataset sources.")
        return

    current_for_each = str(st.session_state.get(for_each_key) or "").strip()
    if source_type != "dataset" and not current_for_each:
        st.session_state[for_each_key] = "$"

    preview_rows, field_options, preview_error = _resolve_send_message_template_preview_rows(
        source_definition,
        for_each=st.session_state.get(for_each_key),
        json_arrays=json_arrays,
        datasources=datasources,
    )
    current_fields = _normalize_compare_keys_input(st.session_state.get(fields_key))
    st.session_state[fields_key] = [
        field_name for field_name in current_fields if field_name in field_options
    ]

    if source_type == "dataset":
        st.text_input("forEach", key=for_each_key, disabled=True, help="Not used for dataset sources.")
    else:
        st.text_input(
            "forEach",
            key=for_each_key,
            placeholder="payload items",
            help="JSON path root used to split or extract source records.",
        )

    st.multiselect(
        "Template fields",
        options=field_options,
        key=fields_key,
        disabled=not bool(field_options),
    )
    field_action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with field_action_cols[0]:
        if st.button(
            "Add all fields",
            key=f"{fields_key}_add_all",
            use_container_width=True,
            disabled=not bool(field_options),
        ):
            st.session_state[fields_key] = list(field_options)
            st.rerun()
    with field_action_cols[1]:
        if st.button(
            "Remove all fields",
            key=f"{fields_key}_remove_all",
            use_container_width=True,
            disabled=not bool(st.session_state.get(fields_key)),
        ):
            st.session_state[fields_key] = []
            st.rerun()

    st.caption("Template constants")
    edited_constant_rows = st.data_editor(
        _send_message_template_constant_rows(st.session_state.get(constants_key)),
        key=constants_editor_key,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "field": st.column_config.TextColumn("Field", required=True),
            "type": st.column_config.SelectboxColumn(
                "Type",
                options=["string", "number", "date", "datetime", "boolean"],
                required=True,
            ),
            "value": st.column_config.TextColumn("Value"),
        },
    )
    st.session_state[constants_key] = _send_message_template_constant_rows(edited_constant_rows)

    if preview_rows:
        st.caption("Template source preview")
        st.json(preview_rows[:3], expanded=True)
    elif preview_error:
        st.info(preview_error)


def _render_send_message_template_management(
    *,
    key_prefix: str,
    dialog_nonce: int,
    source_options: list[dict],
    json_arrays: list[dict],
    datasources: list[dict],
):
    panel_open_key = _command_form_key(key_prefix, dialog_nonce, "send_message_template_panel_open")
    template_enabled_key = _command_form_key(key_prefix, dialog_nonce, "send_message_template_enabled")
    if st.button(
        "Manage template",
        key=_command_form_key(key_prefix, dialog_nonce, "send_message_template_manage"),
        use_container_width=True,
    ):
        st.session_state[panel_open_key] = not bool(st.session_state.get(panel_open_key))

    template_status = "enabled" if bool(st.session_state.get(template_enabled_key)) else "disabled"
    st.caption(f"Message template: {template_status}")
    if not bool(st.session_state.get(panel_open_key)):
        return

    with st.container(border=True):
        st.caption("Template management")
        _render_send_message_template_section(
            key_prefix=key_prefix,
            dialog_nonce=dialog_nonce,
            source_options=source_options,
            json_arrays=json_arrays,
            datasources=datasources,
        )


def _render_source_constant_select(
    *,
    label: str,
    key: str,
    options: list[dict],
    help_text: str | None = None,
):
    option_values = [str(item.get("path") or "").strip() for item in options if str(item.get("path") or "").strip()]
    current_value = str(st.session_state.get(key) or "").strip()
    if current_value not in option_values:
        st.session_state[key] = option_values[0] if option_values else ""

    st.selectbox(
        label,
        options=option_values or [""],
        format_func=lambda path: (
            next(
                (
                    _format_source_variable_option(item)
                    for item in options
                    if str(item.get("path") or "").strip() == str(path or "").strip()
                ),
                "No variable available",
            )
        ),
        key=key,
        disabled=not bool(option_values),
        help=help_text,
    )
    if not option_values:
        st.info("No compatible variable available at this point.")


def _command_description_text(command_item: dict) -> str:
    return str(command_item.get("description") or "").strip()


def _extract_variable_name(value: object) -> str:
    if isinstance(value, str):
        raw = str(value).strip()
        if raw.startswith("source:"):
            return raw.split(":", 1)[1] or raw
        if ".constants." in raw:
            return raw.split(".")[-1] or raw
        return raw or "-"
    if value is None:
        return "-"
    return _stringify_form_value(value).strip() or "-"


def _italicize_entity(value: object) -> str:
    text = str(value or "").strip() or "-"
    if text == "-":
        return text
    return f"*{text}*"


def _bold_entity(value: object) -> str:
    text = str(value or "").strip() or "-"
    if text == "-":
        return text
    return f"**{text}**"


def _assert_data_label(command_code: str) -> str:
    normalized = str(command_code or "").strip()
    return "JsonArray" if normalized.startswith("jsonArray") else "Json"


def _command_ui_label(command_item: dict) -> str:
    configuration_json = _safe_dict(command_item.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json)
    if command_code == "initConstant":
        source_type = _normalized_value_type(configuration_json)
        return VARIABLE_UI_LABELS_BY_SOURCE_TYPE.get(source_type, "Variable")
    if command_code in TEST_ASSERT_COMMAND_CODES:
        return "Assert"
    return COMMAND_UI_LABELS.get(command_code, command_code or "Command")


def _command_action_label(command_item: dict) -> str:
    return _command_ui_label(command_item).strip().lower() or "command"


def _hook_command_type_label(command_code: str) -> str:
    return HOOK_COMMAND_LABELS.get(str(command_code or "").strip(), str(command_code or "").strip())


def _resolve_connection_label(connection_id: object) -> str:
    normalized_connection_id = str(connection_id or "").strip()
    if not normalized_connection_id:
        return "-"
    connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))
    connection_item = _map_by_id(connections).get(normalized_connection_id, {})
    return _format_lookup_label(connection_item) if connection_item else normalized_connection_id


def _resolve_dataset_summary(dataset_id: object) -> tuple[str, str]:
    normalized_dataset_id = str(dataset_id or "").strip()
    if not normalized_dataset_id:
        return "-", "-"
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    datasource_item = _map_by_id(datasources).get(normalized_dataset_id, {})
    if not datasource_item:
        return normalized_dataset_id, "-"
    payload = _safe_dict(datasource_item.get("payload") or {})
    connection_label = _resolve_connection_label(payload.get("connection_id"))
    dataset_label = _format_lookup_label(datasource_item)
    return dataset_label, connection_label


def _resolve_test_suite_label(suite_id: object) -> str:
    normalized_suite_id = str(suite_id or "").strip()
    if not normalized_suite_id:
        return "-"
    suites = _safe_list(st.session_state.get(TEST_SUITES_KEY, []))
    suite_item = _map_by_id(suites).get(normalized_suite_id, {})
    return _format_lookup_label(suite_item) if suite_item else normalized_suite_id


def _resolve_queue_label(queue_id: object) -> str:
    normalized_queue_id = str(queue_id or "").strip()
    if not normalized_queue_id:
        return "-"
    brokers = _safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    for broker in brokers:
        broker_id = str(broker.get("id") or "").strip()
        if not broker_id:
            continue
        queues = load_test_editor_queues_for_broker(broker_id, force=False)
        queue_item = _map_by_id(_safe_list(queues)).get(normalized_queue_id, {})
        if queue_item:
            return _format_lookup_label(queue_item)
    return normalized_queue_id


def _command_leading_icon(command_item: dict) -> str:
    configuration_json = _safe_dict(command_item.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json)
    if command_code == "initConstant":
        source_type = _normalized_value_type(configuration_json)
        return CONSTANT_SOURCE_ICON_BY_TYPE.get(source_type, ":material/data_object:")
    if command_code in TEST_ASSERT_COMMAND_CODES:
        return ":material/bug_report:"
    return COMMAND_ICON_BY_CODE.get(command_code, COMMAND_ICON_DEFAULT)


def _build_assert_summary(command_item: dict) -> str:
    configuration_json = _safe_dict(command_item.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json) or "assert"
    variable_name = _extract_variable_name(configuration_json.get("actual"))
    data_label = _assert_data_label(command_code)
    if command_code in {"jsonEquals", "jsonArrayEquals"}:
        return f"**Expected {data_label} equals to** {_italicize_entity(variable_name)}"
    if command_code in {"jsonContains", "jsonArrayContains"}:
        return f"**Expected {data_label} contains** {_italicize_entity(variable_name)}"
    if command_code in {"jsonEmpty", "jsonArrayEmpty"}:
        return f"**{data_label}** {_italicize_entity(variable_name)} **is empty**"
    if command_code in {"jsonNotEmpty", "jsonArrayNotEmpty"}:
        return f"**{data_label}** {_italicize_entity(variable_name)} **is not empty**"
    phrase = ASSERT_PHRASE_BY_CODE.get(command_code, "assert").capitalize()
    return f"**{phrase}** {_italicize_entity(variable_name)}".strip()


def _build_suite_command_summary(command_item: dict) -> str:
    configuration_json = _safe_dict(command_item.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json) or "-"

    if command_code == "initConstant":
        constant_name = str(configuration_json.get("name") or "").strip() or "-"
        source_type = _normalized_value_type(configuration_json)
        variable_type_label = VARIABLE_TYPE_LABELS_BY_SOURCE_TYPE.get(source_type, "generic")
        return f"**Initialize {variable_type_label} variable** {_italicize_entity(constant_name)}"
    if command_code == "deleteConstant":
        constant_name = str(configuration_json.get("name") or "").strip() or "-"
        return f"**Delete variable** {_italicize_entity(constant_name)}"
    if command_code == "sleep":
        duration = _safe_int(configuration_json.get("duration"), 0)
        duration_label = f"{duration}s" if duration else "-"
        return f"**Sleep** {_italicize_entity(duration_label)}"
    if command_code == "readApi":
        url = str(configuration_json.get("url") or "").strip() or "-"
        return f"**Read API** {_italicize_entity(url)}"
    if command_code == "writeApi":
        method = str(configuration_json.get("method") or "POST").strip().upper() or "POST"
        url = str(configuration_json.get("url") or "").strip() or "-"
        return f"**Write API {method}** {_italicize_entity(url)}"
    if command_code == "sendMessageQueue":
        variable_name = _extract_variable_name(configuration_json.get("source"))
        queue_label = _resolve_queue_label(
            configuration_json.get("queue_id") or configuration_json.get("queueId")
        )
        return f"**Send variable** {_italicize_entity(variable_name)} **to queue** {_italicize_entity(queue_label)}"
    if command_code == "saveTable":
        table_name = str(configuration_json.get("table_name") or configuration_json.get("tableName") or "").strip() or "-"
        variable_name = _extract_variable_name(configuration_json.get("source"))
        return f"**Save variable** {_italicize_entity(variable_name)} **to table** {_italicize_entity(table_name)}"
    if command_code == "dropTable":
        table_name = str(configuration_json.get("table_name") or configuration_json.get("tableName") or "").strip() or "-"
        return f"**Drop table** {_italicize_entity(table_name)}"
    if command_code == "cleanTable":
        table_name = str(configuration_json.get("table_name") or configuration_json.get("tableName") or "").strip() or "-"
        return f"**Clean table** {_italicize_entity(table_name)}"
    if command_code == "exportDataset":
        variable_name = _extract_variable_name(configuration_json.get("source"))
        table_name = str(
            configuration_json.get("table_name")
            or configuration_json.get("tableName")
            or "-"
        ).strip() or "-"
        return f"**Export variable** {_italicize_entity(variable_name)} **to table** {_italicize_entity(table_name)}"
    if command_code == "dropDataset":
        dataset_label, connection_label = _resolve_dataset_summary(
            configuration_json.get("dataset_id") or configuration_json.get("datasetId")
        )
        return f"**Drop dataset** {_italicize_entity(dataset_label)} **from** {_italicize_entity(connection_label)} **database**"
    if command_code == "cleanDataset":
        dataset_label, connection_label = _resolve_dataset_summary(
            configuration_json.get("dataset_id") or configuration_json.get("datasetId")
        )
        return f"**Clean dataset** {_italicize_entity(dataset_label)} **from** {_italicize_entity(connection_label)} **database**"
    if command_code == "runSuite":
        suite_label = _resolve_test_suite_label(
            configuration_json.get("suite_id") or configuration_json.get("suiteId")
        )
        return f"**Run suite** {_italicize_entity(suite_label)}"
    if command_code in TEST_ASSERT_COMMAND_CODES:
        return _build_assert_summary(command_item)
    label = _command_ui_label(command_item)
    return label


def _build_suite_command_markdown(command_item: dict) -> str:
    return _build_suite_command_summary(command_item)


def _render_suite_command_card(
    command_item: dict,
    *,
    key_prefix: str,
    action_specs: list[dict] | None = None,
) -> dict[str, bool]:
    button_results: dict[str, bool] = {}
    action_specs = action_specs or []
    with st.container(border=True):
        row_cols = st.columns([1, 5, 8, *([1] * len(action_specs))], gap="small", vertical_alignment="center")
        with row_cols[0]:
            button_results["command_icon"] = st.button(
                "",
                key=f"{key_prefix}_command_icon",
                icon=_command_leading_icon(command_item),
                help=_command_ui_label(command_item),
                type="tertiary",
                use_container_width=True,
            )
        with row_cols[1]:
            st.markdown(_build_suite_command_markdown(command_item))
        with row_cols[2]:
            description = _command_description_text(command_item)
            if description:
                st.caption(description)
        for column_index, action_spec in enumerate(action_specs, start=3):
            with row_cols[column_index]:
                button_results[str(action_spec.get("name") or column_index)] = st.button(
                    "",
                    key=str(action_spec.get("key") or f"{key_prefix}_action_{column_index}"),
                    icon=str(action_spec.get("icon") or COMMAND_ICON_DEFAULT),
                    help=str(action_spec.get("help") or ""),
                    type=str(action_spec.get("type") or "tertiary"),
                    use_container_width=bool(action_spec.get("use_container_width", True)),
                    disabled=bool(action_spec.get("disabled", False)),
                )
    return button_results


def _default_context_for_hook_phase(hook_phase: str) -> str:
    normalized_phase = str(hook_phase or "").strip().lower()
    if normalized_phase in {"before-all", "after-all"}:
        return "global"
    return "local"


def _default_context_for_item(item: dict | None) -> str:
    if not isinstance(item, dict):
        return "local"
    if str(item.get("kind") or "").strip().lower() == "hook":
        return _default_context_for_hook_phase(str(item.get("hook_phase") or ""))
    return "local"


def _resolve_hook_command_group(configuration_json: dict | None) -> str:
    command_code = _normalize_command_code(configuration_json)
    command_type = _normalize_command_type(configuration_json)
    if command_type == "context" and command_code in HOOK_CONTEXT_COMMAND_CODES:
        return "context"
    if command_type == "action" and command_code in HOOK_ACTION_COMMAND_CODES:
        return "action"
    return ""


def _resolve_test_command_group(configuration_json: dict | None) -> str:
    command_code = _normalize_command_code(configuration_json)
    command_type = _normalize_command_type(configuration_json)
    if command_type == "context" and command_code in TEST_CONSTANT_COMMAND_CODES:
        return "constant"
    if command_type == "action" and command_code in TEST_ACTION_COMMAND_MAPPING.values():
        return "action"
    if command_type == "assert" and command_code in TEST_ASSERT_COMMAND_CODES:
        return "assert"
    return ""


def _command_group_label(command_group: str) -> str:
    normalized_group = str(command_group or "").strip().lower()
    return COMMAND_GROUP_LABELS.get(normalized_group, "command")


def _command_group_title(command_group: str) -> str:
    return _command_group_label(command_group).capitalize()


def _command_group_intro_label(command_group: str, *, mode: str) -> str:
    action = "Insert new" if str(mode or "").strip().lower() == "add" else "Modify"
    return f"{action} {_command_group_label(command_group)}"


def _command_group_primary_action_label(command_group: str, *, mode: str) -> str:
    action = "Add" if str(mode or "").strip().lower() == "add" else "Save"
    return f"{action} {_command_group_label(command_group)}"


def _command_group_added_feedback(command_group: str) -> str:
    return f"New {_command_group_label(command_group)} added."


def _command_group_updated_feedback(command_group: str) -> str:
    return f"{_command_group_title(command_group)} updated."


def _new_suite_item(kind: str, hook_phase: str | None = None) -> dict:
    return {
        "id": None,
        "kind": kind,
        "hook_phase": hook_phase,
        "description": "",
        "position": 0,
        "on_failure": "ABORT",
        "operations": [],
        "_ui_key": new_ui_key(),
    }


def _load_test_suites(force: bool = False) -> list[dict]:
    if force or TEST_SUITES_KEY not in st.session_state:
        st.session_state[TEST_SUITES_KEY] = get_all_test_suites()
    suites = st.session_state.get(TEST_SUITES_KEY, [])
    return suites if isinstance(suites, list) else []


def _ensure_selected_suite_id(suites: list[dict]) -> str:
    suite_ids = [str(item.get("id")) for item in suites if item.get("id")]
    current_suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "").strip()
    if current_suite_id in suite_ids:
        return current_suite_id
    selected_suite_id = suite_ids[0] if suite_ids else ""
    st.session_state[SELECTED_TEST_SUITE_ID_KEY] = selected_suite_id or None
    return selected_suite_id


def _coerce_test_position(value: object) -> int:
    try:
        position = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return position if position > 0 else 0


def _test_position(test: dict, index: int) -> int:
    return _coerce_test_position(test.get("position")) or index


def _find_test_by_position(draft: dict, position: int) -> tuple[int, dict | None]:
    target_position = _coerce_test_position(position)
    tests = draft.get("tests") or []
    if not isinstance(tests, list) or not target_position:
        return -1, None
    for index, test in enumerate(tests, start=1):
        if not isinstance(test, dict):
            continue
        current_position = _test_position(test, index)
        test["position"] = current_position
        if current_position == target_position:
            return index, test
    return -1, None


def _ensure_selected_test_position(draft: dict) -> int:
    tests = draft.get("tests") or []
    if not isinstance(tests, list) or not tests:
        st.session_state.pop(SELECTED_TEST_POSITION_KEY, None)
        return 0

    positions = [
        _test_position(test, index)
        for index, test in enumerate(tests, start=1)
        if isinstance(test, dict)
    ]
    if not positions:
        st.session_state.pop(SELECTED_TEST_POSITION_KEY, None)
        return 0

    requested_position = _coerce_test_position(st.session_state.get(SELECTED_TEST_POSITION_KEY))
    if requested_position in positions:
        selected_position = requested_position
    elif requested_position > positions[-1]:
        selected_position = positions[-1]
    else:
        selected_position = positions[0]

    st.session_state[SELECTED_TEST_POSITION_KEY] = selected_position
    return selected_position


def _load_selected_draft() -> dict:
    suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "").strip()
    if not suite_id:
        draft = build_test_suite_draft({})
        st.session_state[TEST_SUITE_DRAFT_KEY] = draft
        return draft

    payload = get_test_suite_by_id(suite_id)
    draft = build_test_suite_draft(payload)
    st.session_state[TEST_SUITE_DRAFT_KEY] = draft
    return draft


def _resolve_editor_draft(suite_id: str) -> dict:
    draft = st.session_state.get(TEST_SUITE_DRAFT_KEY)
    if not suite_id:
        return draft if isinstance(draft, dict) else _load_selected_draft()

    if not isinstance(draft, dict):
        return _load_selected_draft()

    draft_suite_id = str(draft.get("id") or "").strip()
    if draft_suite_id != suite_id:
        return _load_selected_draft()
    return draft


def _load_execution_history(suite_id: str) -> list[dict]:
    if not suite_id:
        st.session_state[TEST_SUITE_EXECUTIONS_KEY] = []
        st.session_state.pop(SELECTED_TEST_SUITE_EXECUTION_ID_KEY, None)
        st.session_state.pop(PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY, None)
        return []

    executions = get_test_suite_executions(suite_id, limit=20)
    st.session_state[TEST_SUITE_EXECUTIONS_KEY] = executions

    execution_ids = [str(item.get("id")) for item in executions if item.get("id")]
    selected_execution_id = str(st.session_state.get(SELECTED_TEST_SUITE_EXECUTION_ID_KEY) or "").strip()
    preferred_execution_id = str(st.session_state.get(TEST_SUITE_LAST_EXECUTION_ID_KEY) or "").strip()
    pending_execution_id = str(st.session_state.get(PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY) or "").strip()

    if execution_ids:
        next_selected_execution_id = selected_execution_id if selected_execution_id in execution_ids else ""

        if pending_execution_id and pending_execution_id in execution_ids:
            next_selected_execution_id = pending_execution_id
            st.session_state.pop(PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY, None)
        elif not next_selected_execution_id:
            next_selected_execution_id = (
                preferred_execution_id if preferred_execution_id in execution_ids else execution_ids[0]
            )

        if next_selected_execution_id and next_selected_execution_id != selected_execution_id:
            st.session_state[SELECTED_TEST_SUITE_EXECUTION_ID_KEY] = next_selected_execution_id
    else:
        st.session_state.pop(SELECTED_TEST_SUITE_EXECUTION_ID_KEY, None)

    return executions if isinstance(executions, list) else []


def _format_execution_label(execution: dict) -> str:
    started_at = str(execution.get("started_at") or "-")
    ## format datetime YYYY-MM-DD HH:MM:SS
    if started_at != "-":
        try:
            parsed = datetime.fromisoformat(started_at)
            started_at = parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    status = str(execution.get("status") or "?")
    return f"Executed at {started_at} - status: {status}"


def _find_selected_execution(executions: list[dict]) -> dict | None:
    selected_execution_id = str(st.session_state.get(SELECTED_TEST_SUITE_EXECUTION_ID_KEY) or "").strip()
    for execution in executions:
        if str(execution.get("id") or "").strip() == selected_execution_id:
            return execution
    return None


def _render_execution_summary(execution: dict | None):
    if not isinstance(execution, dict):
        return

    with st.container(border=True):
        cols = st.columns(3, gap="small")
        with cols[0]:
            st.caption("Status")
            st.write(str(execution.get("status") or "-"))
        with cols[1]:
            st.caption("Started at")
            st.write(str(execution.get("started_at") or "-"))
        with cols[2]:
            st.caption("Requested item")
            st.write(
                str(
                    execution.get("requested_test_id")
                    or execution.get("test_suite_description")
                    or "-"
                )
            )

        error_message = str(execution.get("error_message") or "").strip()
        if error_message:
            st.error(error_message)


def _persist_changes():
    _persist_current_draft(success_message="Test suite updated.", rerun=True)


def _persist_current_draft(*, success_message: str = "Test suite updated.", rerun: bool = True):
    draft = st.session_state.get(TEST_SUITE_DRAFT_KEY, {})
    if isinstance(draft, dict) and str(draft.get("id") or "").strip():
        payload = draft_to_test_suite_payload(draft)
        payload["id"] = str(draft.get("id") or "").strip()
        update_test_suite(payload)
        _load_selected_draft()
        _load_test_suites(force=True)
        st.session_state[TEST_SUITE_FEEDBACK_KEY] = success_message
    else:
        st.session_state[TEST_SUITE_DRAFT_KEY] = draft
    if rerun:
        st.rerun()


def _clear_state_prefix(prefix: str) -> None:
    for state_key in list(st.session_state.keys()):
        if str(state_key).startswith(prefix):
            st.session_state.pop(state_key, None)


def _select_persisted_tab(options: list[str], state_key: str, *, default: str | None = None) -> str:
    normalized_options = [str(option or "").strip() for option in options if str(option or "").strip()]
    if not normalized_options:
        return ""

    fallback = str(default or normalized_options[0]).strip()
    if fallback not in normalized_options:
        fallback = normalized_options[0]

    current = str(st.session_state.get(state_key) or "").strip()
    if current not in normalized_options:
        current = fallback
        st.session_state[state_key] = current

    segmented_control = getattr(st, "segmented_control", None)
    if callable(segmented_control):
        try:
            selected = segmented_control(
                "Section",
                options=normalized_options,
                key=state_key,
                label_visibility="collapsed",
            )
        except TypeError:
            selected = segmented_control(
                "Section",
                options=normalized_options,
                key=state_key,
            )
        normalized_selected = str(selected or "").strip()
        if normalized_selected in normalized_options:
            return normalized_selected
        return str(st.session_state.get(state_key) or current).strip() or current

    radio = getattr(st, "radio", None)
    if callable(radio):
        selected = radio(
            "Section",
            options=normalized_options,
            key=state_key,
            horizontal=True,
            label_visibility="collapsed",
        )
        normalized_selected = str(selected or "").strip()
        if normalized_selected in normalized_options:
            return normalized_selected
        return str(st.session_state.get(state_key) or current).strip() or current

    return current


def _extract_api_error_detail(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            payload = response.json()
        except Exception:
            payload = None
        if isinstance(payload, dict):
            detail = str(payload.get("detail") or "").strip()
            if detail:
                return detail
        response_text = str(getattr(response, "text", "") or "").strip()
        if response_text:
            return response_text
    return str(exc)


def _friendly_suite_validation_message(detail: str) -> str:
    raw_detail = str(detail or "").strip()
    lowered = raw_detail.lower()
    if "already defined in scope" in lowered:
        return "This order declares the same variable twice in the same scope."
    if "cannot be deleted in section" in lowered:
        return "This order deletes a variable from a scope that cannot be changed here."
    if "is not writable in section" in lowered:
        return "This order writes a variable in a scope that is not allowed here."
    if "incompatible type" in lowered:
        return "This order uses a variable with a type that is not compatible for the command."
    if "constant reference" in lowered and "not visible" in lowered:
        return "This order uses a variable before it is declared or after it has been deleted."
    return "This order is not valid for variable dependencies in the suite."


def _render_persist_error(exc: Exception):
    detail = _extract_api_error_detail(exc)
    friendly_message = _friendly_suite_validation_message(detail)
    if friendly_message == "This order is not valid for variable dependencies in the suite." and detail:
        st.error(detail)
        return
    st.error(friendly_message)


def _render_command_feedback():
    suite_feedback = str(st.session_state.pop(TEST_SUITE_FEEDBACK_KEY, "") or "").strip()
    if suite_feedback:
        st.success(suite_feedback)
    feedback = str(st.session_state.pop(SUITE_FEEDBACK_KEY, "") or "").strip()
    if feedback:
        st.success(feedback)


def _close_add_operation_dialog():
    st.session_state[ADD_TEST_OPERATION_DIALOG_OPEN_KEY] = False
    st.session_state.pop(ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY, None)


def _consume_add_operation_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(ADD_TEST_OPERATION_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[ADD_TEST_OPERATION_DIALOG_OPEN_KEY] = False
    return is_open_requested


@st.dialog("Add new test", width="medium")
def _render_add_test_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(ADD_TEST_DIALOG_NONCE_KEY, 0))
    description_key = f"suite_add_test_description_{dialog_nonce}"
    on_failure_key = f"suite_add_test_on_failure_{dialog_nonce}"

    if description_key not in st.session_state:
        st.session_state[description_key] = ""
    if on_failure_key not in st.session_state:
        st.session_state[on_failure_key] = "ABORT"

    st.text_input("Description", key=description_key)
    st.selectbox(
        "On failure",
        options=["ABORT", "CONTINUE"],
        key=on_failure_key,
        format_func=lambda value: "Abort suite" if str(value).upper() == "ABORT" else "Continue",
    )

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"suite_add_test_save_{dialog_nonce}",
            icon=":material/add_circle:",
            type="secondary",
            use_container_width=True,
        ):
            original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
            tests = draft.setdefault("tests", [])
            if not isinstance(tests, list):
                tests = []
                draft["tests"] = tests

            test_item = _new_suite_item("test")
            test_item["description"] = str(st.session_state.get(description_key) or "").strip()
            test_item["on_failure"] = str(st.session_state.get(on_failure_key) or "ABORT").strip().upper() or "ABORT"
            test_item["position"] = len(tests) + 1
            tests.append(test_item)
            st.session_state[SELECTED_TEST_POSITION_KEY] = test_item["position"]

            try:
                _persist_current_draft(success_message="Test added.", rerun=False)
            except Exception as exc:
                st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                _render_persist_error(exc)
                return
            _close_add_test_dialog()
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"suite_add_test_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_add_test_dialog()
            st.rerun()


@st.dialog("Add data source", width="large")
def _render_add_source_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(SOURCE_ADD_DIALOG_NONCE_KEY, 0))
    item_ui_key = str(st.session_state.get(SOURCE_ADD_DIALOG_TARGET_UI_KEY) or "").strip()
    dialog_mode = str(st.session_state.get(SOURCE_DIALOG_MODE_KEY) or "add").strip().lower() or "add"
    original_source_code = str(st.session_state.get(SOURCE_DIALOG_SOURCE_CODE_KEY) or "").strip()
    item = find_draft_test_by_ui_key(draft, item_ui_key)

    if not isinstance(item, dict):
        st.error("Elemento di destinazione non trovato.")
        if st.button(
            "Cancel",
            key=f"suite_add_source_missing_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_add_source_dialog()
            st.rerun()
        return

    load_test_editor_context(force=False)
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    source_index, source_to_edit = _find_source_index_by_code(item, original_source_code)

    if dialog_mode == "edit":
        if not isinstance(source_to_edit, dict):
            st.error("Source da modificare non trovato.")
            if st.button(
                "Cancel",
                key=f"suite_edit_source_missing_cancel_{dialog_nonce}",
                use_container_width=True,
            ):
                _close_add_source_dialog()
                st.rerun()
            return
        source_code_key = _command_form_key("suite_add_source", dialog_nonce, "source_code")
        source_type_key = _command_form_key("suite_add_source", dialog_nonce, "source_type")
        dataset_id_key = _command_form_key("suite_add_source", dialog_nonce, "dataset_id")
        json_array_id_key = _command_form_key("suite_add_source", dialog_nonce, "json_array_id")
        if source_code_key not in st.session_state:
            st.session_state[source_code_key] = str(source_to_edit.get("sourceCode") or "")
        if source_type_key not in st.session_state:
            st.session_state[source_type_key] = str(source_to_edit.get("sourceType") or "dataset")
        if dataset_id_key not in st.session_state:
            st.session_state[dataset_id_key] = str(source_to_edit.get("datasetId") or "")
        if json_array_id_key not in st.session_state:
            st.session_state[json_array_id_key] = str(source_to_edit.get("jsonArrayId") or "")

    st.markdown("**Modify source**" if dialog_mode == "edit" else "**Insert new source**")
    _render_add_source_form(
        dialog_nonce,
        datasources,
        json_arrays,
        key_prefix="suite_add_source",
    )
    _render_add_source_preview(
        dialog_nonce,
        datasources,
        json_arrays,
        key_prefix="suite_add_source",
    )

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save source" if dialog_mode == "edit" else "Add source",
            key=f"suite_add_source_save_{dialog_nonce}",
            icon=":material/save:" if dialog_mode == "edit" else ":material/add_circle:",
            type="secondary",
            use_container_width=True,
        ):
            original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
            source_item, validation_error = _build_source_draft_with_prefix(
                dialog_nonce,
                datasources,
                json_arrays,
                key_prefix="suite_add_source",
            )
            if validation_error:
                st.error(validation_error)
                return
            duplicate_error = _validate_source_code_for_item(
                item,
                (source_item or {}).get("sourceCode"),
                ignore_source_code=original_source_code if dialog_mode == "edit" else None,
            )
            if duplicate_error:
                st.error(duplicate_error)
                return
            if dialog_mode == "edit":
                _update_source_in_item(item, source_index, source_item or {})
            else:
                _append_source_to_item(item, source_item or {})
            try:
                _persist_current_draft(
                    success_message="Source updated." if dialog_mode == "edit" else "New source added.",
                    rerun=False,
                )
            except Exception as exc:
                st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                _render_persist_error(exc)
                return
            _close_add_source_dialog()
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"suite_add_source_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_add_source_dialog()
            st.rerun()

@st.dialog("Add hook command", width="large")
def _render_add_hook_command_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(HOOK_ADD_COMMAND_DIALOG_NONCE_KEY, 0))
    item_ui_key = str(st.session_state.get(HOOK_ADD_COMMAND_DIALOG_TARGET_UI_KEY) or "").strip()
    command_group = str(st.session_state.get(HOOK_ADD_COMMAND_DIALOG_GROUP_KEY) or "context").strip().lower()
    hook_item = find_draft_test_by_ui_key(draft, item_ui_key)
    command_intro_label = _command_group_intro_label(command_group, mode="add")
    primary_action_label = _command_group_primary_action_label(command_group, mode="add")

    if not isinstance(hook_item, dict):
        st.error("Hook di destinazione non trovato.")
        if st.button("Cancel", key=f"suite_add_hook_missing_cancel_{dialog_nonce}", use_container_width=True):
            _close_hook_command_dialog()
            st.rerun()
        return

    load_test_editor_context(force=False)
    load_database_connections(force=False)

    json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = _safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))
    default_context = _default_context_for_item(hook_item)

    st.markdown(f"**{command_intro_label}**")
    command_code = _render_hook_command_form(
        dialog_nonce,
        command_group,
        json_arrays,
        datasources,
        brokers,
        connections,
        draft,
        hook_item,
        stop_before_index=len(_operation_list(hook_item)),
        default_context=default_context,
        key_prefix="suite_add_hook",
    )

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            primary_action_label,
            key=f"suite_add_hook_command_save_{dialog_nonce}",
            icon=":material/add_circle:",
            type="secondary",
            use_container_width=True,
        ):
            operation_item, validation_error = _build_hook_command_draft_with_prefix(
                dialog_nonce,
                command_code,
                key_prefix="suite_add_hook",
            )
            if validation_error:
                st.error(validation_error)
                return
            append_operation_to_test(hook_item, operation_item or {})
            _close_hook_command_dialog()
            st.session_state[SUITE_FEEDBACK_KEY] = _command_group_added_feedback(command_group)
            _persist_changes()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"suite_add_hook_command_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_hook_command_dialog()
            st.rerun()


def _open_add_test_dialog():
    st.session_state[ADD_TEST_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_TEST_DIALOG_NONCE_KEY] = int(st.session_state.get(ADD_TEST_DIALOG_NONCE_KEY, 0)) + 1


def _close_add_test_dialog():
    st.session_state[ADD_TEST_DIALOG_OPEN_KEY] = False


def _get_hook_item(draft: dict, hook_phase: str) -> dict | None:
    hooks = draft.get("hooks")
    if not isinstance(hooks, dict):
        return None

    hook = hooks.get(hook_phase)
    if not isinstance(hook, dict):
        return None

    hook["_ui_key"] = str(hook.get("_ui_key") or new_ui_key())
    operations = hook.get("operations")
    if not isinstance(operations, list):
        hook["operations"] = []
    return hook


def _ensure_hook_item(draft: dict, hook_phase: str) -> dict:
    hooks = draft.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        draft["hooks"] = hooks

    hook = _get_hook_item(draft, hook_phase)
    if isinstance(hook, dict):
        return hook

    hook = _new_suite_item("hook", hook_phase=hook_phase)
    hooks[hook_phase] = hook
    return hook

def _open_add_operation_dialog_for_item(item_ui_key: str):
    st.session_state[ADD_TEST_OPERATION_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY] = str(item_ui_key or "")
    st.session_state[ADD_TEST_OPERATION_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(ADD_TEST_OPERATION_DIALOG_NONCE_KEY, 0)) + 1
    )


def _open_hook_command_dialog_for_hook(draft: dict, hook_phase: str, group: str):
    hook = _ensure_hook_item(draft, hook_phase)
    st.session_state[HOOK_ADD_COMMAND_DIALOG_OPEN_KEY] = True
    st.session_state[HOOK_ADD_COMMAND_DIALOG_TARGET_UI_KEY] = str(hook.get("_ui_key") or "")
    st.session_state[HOOK_ADD_COMMAND_DIALOG_GROUP_KEY] = str(group or "context").strip().lower()
    st.session_state[HOOK_ADD_COMMAND_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(HOOK_ADD_COMMAND_DIALOG_NONCE_KEY, 0)) + 1
    )


def _open_test_command_dialog_for_item(item_ui_key: str, group: str):
    st.session_state[TEST_ADD_COMMAND_DIALOG_OPEN_KEY] = True
    st.session_state[TEST_ADD_COMMAND_DIALOG_TARGET_UI_KEY] = str(item_ui_key or "")
    st.session_state[TEST_ADD_COMMAND_DIALOG_GROUP_KEY] = str(group or "constant").strip().lower()
    st.session_state[TEST_ADD_COMMAND_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(TEST_ADD_COMMAND_DIALOG_NONCE_KEY, 0)) + 1
    )


def _open_add_source_dialog_for_item(item_ui_key: str):
    st.session_state[SOURCE_ADD_DIALOG_OPEN_KEY] = True
    st.session_state[SOURCE_ADD_DIALOG_TARGET_UI_KEY] = str(item_ui_key or "")
    st.session_state[SOURCE_DIALOG_MODE_KEY] = "add"
    st.session_state.pop(SOURCE_DIALOG_SOURCE_CODE_KEY, None)
    st.session_state[SOURCE_ADD_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(SOURCE_ADD_DIALOG_NONCE_KEY, 0)) + 1
    )


def _open_edit_source_dialog_for_item(item_ui_key: str, source_code: str):
    st.session_state[SOURCE_ADD_DIALOG_OPEN_KEY] = True
    st.session_state[SOURCE_ADD_DIALOG_TARGET_UI_KEY] = str(item_ui_key or "")
    st.session_state[SOURCE_DIALOG_MODE_KEY] = "edit"
    st.session_state[SOURCE_DIALOG_SOURCE_CODE_KEY] = str(source_code or "")
    st.session_state[SOURCE_ADD_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(SOURCE_ADD_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_test_command_dialog():
    st.session_state[TEST_ADD_COMMAND_DIALOG_OPEN_KEY] = False
    st.session_state.pop(TEST_ADD_COMMAND_DIALOG_TARGET_UI_KEY, None)
    st.session_state.pop(TEST_ADD_COMMAND_DIALOG_GROUP_KEY, None)


def _close_add_source_dialog():
    st.session_state[SOURCE_ADD_DIALOG_OPEN_KEY] = False
    st.session_state.pop(SOURCE_ADD_DIALOG_TARGET_UI_KEY, None)
    st.session_state.pop(SOURCE_DIALOG_MODE_KEY, None)
    st.session_state.pop(SOURCE_DIALOG_SOURCE_CODE_KEY, None)


def _open_inline_test_command_editor(operation_ui_key: str):
    st.session_state[TEST_EDITOR_INLINE_COMMAND_UI_KEY] = str(operation_ui_key or "")
    st.session_state[TEST_EDITOR_INLINE_COMMAND_NONCE_KEY] = (
        int(st.session_state.get(TEST_EDITOR_INLINE_COMMAND_NONCE_KEY, 0)) + 1
    )


def _close_inline_test_command_editor():
    st.session_state.pop(TEST_EDITOR_INLINE_COMMAND_UI_KEY, None)


def _inline_test_command_nonce() -> int:
    return int(st.session_state.get(TEST_EDITOR_INLINE_COMMAND_NONCE_KEY, 0))


def _is_inline_test_command_active(operation_ui_key: str) -> bool:
    active_operation_ui_key = str(st.session_state.get(TEST_EDITOR_INLINE_COMMAND_UI_KEY) or "").strip()
    return bool(active_operation_ui_key and active_operation_ui_key == str(operation_ui_key or "").strip())


def _open_edit_command_dialog(item_ui_key: str, command_ui_key: str, owner_kind: str, command_group: str):
    st.session_state[COMMAND_EDIT_DIALOG_OPEN_KEY] = True
    st.session_state[COMMAND_EDIT_DIALOG_TARGET_ITEM_UI_KEY] = str(item_ui_key or "")
    st.session_state[COMMAND_EDIT_DIALOG_TARGET_COMMAND_UI_KEY] = str(command_ui_key or "")
    st.session_state[COMMAND_EDIT_DIALOG_OWNER_KIND_KEY] = str(owner_kind or "").strip().lower()
    st.session_state[COMMAND_EDIT_DIALOG_GROUP_KEY] = str(command_group or "").strip().lower()
    st.session_state[COMMAND_EDIT_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(COMMAND_EDIT_DIALOG_NONCE_KEY, 0)) + 1
    )


def _mark_inline_api_command_for_reopen(operation_ui_key: str) -> None:
    st.session_state[INLINE_API_REOPEN_COMMAND_UI_KEY] = str(operation_ui_key or "")


def _consume_inline_api_command_reopen(operation_ui_key: str) -> bool:
    reopen_ui_key = str(st.session_state.get(INLINE_API_REOPEN_COMMAND_UI_KEY) or "")
    if reopen_ui_key and reopen_ui_key == str(operation_ui_key or ""):
        st.session_state.pop(INLINE_API_REOPEN_COMMAND_UI_KEY, None)
        return True
    return False


def _open_reorder_command_dialog_for_item(item: dict):
    item_ui_key = str((item or {}).get("_ui_key") or "").strip()
    if not item_ui_key:
        return
    st.session_state[COMMAND_REORDER_DIALOG_OPEN_KEY] = True
    st.session_state[COMMAND_REORDER_DIALOG_TARGET_ITEM_UI_KEY] = item_ui_key
    st.session_state[COMMAND_REORDER_DIALOG_OPERATIONS_KEY] = deepcopy(_operation_list(item))
    st.session_state[COMMAND_REORDER_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(COMMAND_REORDER_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_edit_command_dialog():
    st.session_state[COMMAND_EDIT_DIALOG_OPEN_KEY] = False
    st.session_state.pop(COMMAND_EDIT_DIALOG_TARGET_ITEM_UI_KEY, None)
    st.session_state.pop(COMMAND_EDIT_DIALOG_TARGET_COMMAND_UI_KEY, None)
    st.session_state.pop(COMMAND_EDIT_DIALOG_OWNER_KIND_KEY, None)
    st.session_state.pop(COMMAND_EDIT_DIALOG_GROUP_KEY, None)


def _close_reorder_command_dialog():
    st.session_state[COMMAND_REORDER_DIALOG_OPEN_KEY] = False
    st.session_state.pop(COMMAND_REORDER_DIALOG_TARGET_ITEM_UI_KEY, None)
    st.session_state.pop(COMMAND_REORDER_DIALOG_OPERATIONS_KEY, None)


def _close_hook_command_dialog():
    st.session_state[HOOK_ADD_COMMAND_DIALOG_OPEN_KEY] = False
    st.session_state.pop(HOOK_ADD_COMMAND_DIALOG_TARGET_UI_KEY, None)
    st.session_state.pop(HOOK_ADD_COMMAND_DIALOG_GROUP_KEY, None)


def _consume_hook_command_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(HOOK_ADD_COMMAND_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[HOOK_ADD_COMMAND_DIALOG_OPEN_KEY] = False
    return is_open_requested


def _consume_add_source_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(SOURCE_ADD_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[SOURCE_ADD_DIALOG_OPEN_KEY] = False
    return is_open_requested

def _consume_edit_command_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(COMMAND_EDIT_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[COMMAND_EDIT_DIALOG_OPEN_KEY] = False
    return is_open_requested


def _reorder_dialog_operations() -> list[dict]:
    operations = st.session_state.get(COMMAND_REORDER_DIALOG_OPERATIONS_KEY, [])
    if not isinstance(operations, list):
        return []
    return [operation for operation in operations if isinstance(operation, dict)]


def _move_reorder_operation(from_index: int, to_index: int):
    operations = list(_reorder_dialog_operations())
    if not (0 <= from_index < len(operations)) or not (0 <= to_index < len(operations)):
        return
    operations[from_index], operations[to_index] = operations[to_index], operations[from_index]
    st.session_state[COMMAND_REORDER_DIALOG_OPERATIONS_KEY] = operations


def _find_operation_index_by_ui_key(item: dict, operation_ui_key: str) -> int:
    operations = item.get("operations") or []
    if not isinstance(operations, list):
        return -1
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            continue
        current_ui_key = str(operation.get("_ui_key") or "")
        if not current_ui_key:
            current_ui_key = f"{str(item.get('_ui_key') or '')}_op_{index}"
            operation["_ui_key"] = current_ui_key
        if current_ui_key == str(operation_ui_key or ""):
            return index
    return -1


def _find_operation_by_ui_key(item: dict, operation_ui_key: str) -> tuple[int, dict | None]:
    operation_index = _find_operation_index_by_ui_key(item, operation_ui_key)
    operations = item.get("operations") or []
    if operation_index < 0 or not isinstance(operations, list):
        return -1, None
    operation = operations[operation_index]
    return operation_index, operation if isinstance(operation, dict) else None


def _advanced_hook_section_state_key(hook_phase: str) -> str:
    return f"{ADVANCED_HOOK_SECTION_TAB_KEY_PREFIX}_{str(hook_phase or '').strip().lower()}"


def _advanced_hook_selected_command_state_key(hook_phase: str) -> str:
    return f"{ADVANCED_HOOK_SELECTED_COMMAND_KEY_PREFIX}_{str(hook_phase or '').strip().lower()}"


def _advanced_hook_api_tab_state_key(operation_ui_key: str) -> str:
    return f"{ADVANCED_HOOK_API_TAB_KEY_PREFIX}_{str(operation_ui_key or '').strip()}"


def _strip_command_markdown(label: object) -> str:
    return str(label or "").replace("**", "").replace("*", "").strip()


def _build_advanced_hook_command_list_label(command_item: dict) -> str:
    configuration_json = _safe_dict(command_item.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json)
    result_target_label = _api_result_target_label(configuration_json)
    if command_code == "readApi":
        if result_target_label:
            return (
                f"**Fetch data from a REST API** "
                f"**response stored in variable** {_italicize_entity(result_target_label)}"
            )
        return "**Fetch data from a REST API**"
    if command_code == "writeApi":
        method = str(configuration_json.get("method") or "POST").strip().upper() or "POST"
        if result_target_label:
            return (
                f"**Send data to a REST API {method}** "
                f"**response stored in variable** {_italicize_entity(result_target_label)}"
            )
        return f"**Send data to a REST API {method}**"
    return _build_suite_command_summary(command_item)


def _advanced_hook_operation_entries(item: dict | None) -> list[tuple[int, dict, str]]:
    operation_entries: list[tuple[int, dict, str]] = []
    current_item = item or {}
    for op_idx, operation in enumerate(_operation_list(item)):
        if not isinstance(operation, dict):
            continue
        item_ui_key = str(current_item.get("_ui_key") or new_ui_key())
        current_item["_ui_key"] = item_ui_key
        operation_ui_key = str(operation.get("_ui_key") or f"{item_ui_key}_op_{op_idx}")
        operation["_ui_key"] = operation_ui_key
        operation_entries.append((op_idx, operation, operation_ui_key))
    return operation_entries


def _resolve_advanced_hook_selected_command(item: dict | None, hook_phase: str) -> str:
    state_key = _advanced_hook_selected_command_state_key(hook_phase)
    operation_entries = _advanced_hook_operation_entries(item)
    valid_ui_keys = {operation_ui_key for _, _, operation_ui_key in operation_entries}
    current = str(st.session_state.get(state_key) or "").strip()
    if current in valid_ui_keys:
        return current
    if operation_entries:
        next_ui_key = operation_entries[0][2]
        st.session_state[state_key] = next_ui_key
        return next_ui_key
    st.session_state.pop(state_key, None)
    return ""


def _set_advanced_hook_selected_command(hook_phase: str, operation_ui_key: str) -> None:
    state_key = _advanced_hook_selected_command_state_key(hook_phase)
    normalized_ui_key = str(operation_ui_key or "").strip()
    if normalized_ui_key:
        st.session_state[state_key] = normalized_ui_key
    else:
        st.session_state.pop(state_key, None)


def _reassign_advanced_hook_selected_command_after_delete(item: dict, hook_phase: str, deleted_operation_ui_key: str) -> None:
    deleted_index, _ = _find_operation_by_ui_key(item, deleted_operation_ui_key)
    deleted_index = max(deleted_index, 0)
    if _delete_operation_by_ui_key(item, deleted_operation_ui_key):
        operation_entries = _advanced_hook_operation_entries(item)
        if not operation_entries:
            _set_advanced_hook_selected_command(hook_phase, "")
            return
        fallback_index = min(deleted_index, len(operation_entries) - 1)
        _set_advanced_hook_selected_command(hook_phase, operation_entries[fallback_index][2])


def _update_operation_in_item(item: dict, operation_index: int, updated_operation: dict):
    operations = item.get("operations") or []
    if not isinstance(operations, list) or not (0 <= operation_index < len(operations)):
        return
    existing_operation = operations[operation_index]
    if not isinstance(existing_operation, dict):
        existing_operation = {}
    operations[operation_index] = {
        **existing_operation,
        **updated_operation,
        "id": existing_operation.get("id"),
        "order": existing_operation.get("order", operation_index + 1),
        "_ui_key": existing_operation.get("_ui_key"),
    }


def _delete_operation_by_ui_key(item: dict, operation_ui_key: str) -> bool:
    operation_index = _find_operation_index_by_ui_key(item, operation_ui_key)
    operations = item.get("operations") or []
    if not isinstance(operations, list) or not (0 <= operation_index < len(operations)):
        return False
    operations.pop(operation_index)
    return True


def _move_operation_in_item(item: dict, from_index: int, to_index: int) -> bool:
    operations = item.get("operations") or []
    if not isinstance(operations, list):
        return False
    if not (0 <= from_index < len(operations)) or not (0 <= to_index < len(operations)):
        return False
    operations[from_index], operations[to_index] = operations[to_index], operations[from_index]
    item["operations"] = _resequence_operations(operations)
    return True


def _resequence_operations(operations_source: list[dict] | None) -> list[dict]:
    resequenced: list[dict] = []
    for index, operation in enumerate(operations_source or [], start=1):
        if not isinstance(operation, dict):
            continue
        resequenced.append(
            {
                **operation,
                "order": index,
                "_ui_key": str(operation.get("_ui_key") or new_ui_key()),
            }
        )
    return resequenced


def _build_hook_command_draft(dialog_nonce: int, command_code: str) -> tuple[dict | None, str | None]:
    description = str(
        st.session_state.get(f"suite_add_hook_command_description_{dialog_nonce}") or ""
    ).strip()

    cfg: dict[str, object]
    if command_code == "initConstant":
        name = str(st.session_state.get(f"suite_add_hook_init_constant_name_{dialog_nonce}") or "").strip()
        context = str(
            st.session_state.get(f"suite_add_hook_init_constant_context_{dialog_nonce}") or "local"
        ).strip()
        source_type = str(
            st.session_state.get(f"suite_add_hook_init_constant_source_type_{dialog_nonce}") or "value"
        ).strip()
        if source_type == "raw":
            source_type = "value"
        if not name:
            return None, "Il campo Name e' obbligatorio."
        if source_type not in CONSTANT_SOURCE_OPTIONS:
            return None, "Runtime value type non supportato."
        cfg = {
            "commandCode": "setVariable",
            "commandType": "context",
            "name": name,
            "context": context,
            "valueType": source_type,
        }
        if source_type in {"value", "json"}:
            parsed_value, parse_error = _parse_json_input(
                st.session_state.get(f"suite_add_hook_init_constant_value_{dialog_nonce}")
            )
            if parse_error:
                return None, parse_error
            cfg["value"] = parsed_value
        elif source_type == "function":
            function_name = str(
                st.session_state.get(f"suite_add_hook_init_constant_function_name_{dialog_nonce}") or "now"
            ).strip().lower()
            cfg["functionName"] = function_name
    elif command_code == "deleteConstant":
        name = str(st.session_state.get(f"suite_add_hook_delete_constant_name_{dialog_nonce}") or "").strip()
        context = str(
            st.session_state.get(f"suite_add_hook_delete_constant_context_{dialog_nonce}") or "local"
        ).strip()
        if not name:
            return None, "Il campo Name e' obbligatorio."
        cfg = {
            "commandCode": "deleteVariable",
            "commandType": "context",
            "name": name,
            "context": context,
        }
    elif command_code == "readApi":
        url = str(st.session_state.get(f"suite_add_hook_read_api_url_{dialog_nonce}") or "").strip()
        if not url:
            return None, "Il campo URL e' obbligatorio."
        query_params, query_params_error = _parse_json_input(
            st.session_state.get(f"suite_add_hook_read_api_query_params_{dialog_nonce}")
        )
        if query_params_error:
            return None, query_params_error.replace("JSON", "Query params")
        if query_params is not None and not isinstance(query_params, (dict, list)):
            return None, "Il campo Query params deve essere un oggetto o array JSON."
        headers, headers_error = _parse_optional_json_object_input(
            st.session_state.get(f"suite_add_hook_read_api_headers_{dialog_nonce}"),
            "Headers",
        )
        if headers_error:
            return None, headers_error
        result_target = _normalize_api_result_target_input(
            st.session_state.get(f"suite_add_hook_read_api_result_target_{dialog_nonce}")
        )
        timeout_seconds = _safe_int(
            st.session_state.get(f"suite_add_hook_read_api_timeout_seconds_{dialog_nonce}"),
            30,
        )
        cfg = {
            "commandCode": "readApi",
            "commandType": "action",
            "url": url,
            "timeoutSeconds": timeout_seconds or 30,
        }
        if query_params is not None:
            cfg["queryParams"] = query_params
        if headers:
            cfg["headers"] = headers
        if result_target:
            cfg["result_target"] = result_target
    elif command_code == "writeApi":
        method = str(
            st.session_state.get(f"suite_add_hook_write_api_method_{dialog_nonce}") or "POST"
        ).strip().upper()
        url = str(st.session_state.get(f"suite_add_hook_write_api_url_{dialog_nonce}") or "").strip()
        if not url:
            return None, "Il campo URL e' obbligatorio."
        query_params, query_params_error = _parse_json_input(
            st.session_state.get(f"suite_add_hook_write_api_query_params_{dialog_nonce}")
        )
        if query_params_error:
            return None, query_params_error.replace("JSON", "Query params")
        if query_params is not None and not isinstance(query_params, (dict, list)):
            return None, "Il campo Query params deve essere un oggetto o array JSON."
        headers, headers_error = _parse_optional_json_object_input(
            st.session_state.get(f"suite_add_hook_write_api_headers_{dialog_nonce}"),
            "Headers",
        )
        if headers_error:
            return None, headers_error
        body_type = str(
            st.session_state.get(f"suite_add_hook_write_api_body_type_{dialog_nonce}") or "json"
        ).strip() or "json"
        if body_type == "json":
            body_payload, body_error = _parse_json_input(
                st.session_state.get(f"suite_add_hook_write_api_body_{dialog_nonce}")
            )
            if body_error:
                return None, body_error
        elif body_type == "formUrlEncoded":
            body_payload, body_error = collect_guided_kv_rows(
                st.session_state.get(f"suite_add_hook_write_api_form_rows_{dialog_nonce}") or [],
                f"suite_add_hook_write_api_form_rows_row_{dialog_nonce}",
                "Body",
                allowed_modes=FORM_URLENCODED_ALLOWED_MODES,
                scalar_only=True,
            )
            if body_error:
                return None, body_error
        else:
            body_payload = str(
                st.session_state.get(f"suite_add_hook_write_api_body_{dialog_nonce}") or ""
            )
        result_target = _normalize_api_result_target_input(
            st.session_state.get(f"suite_add_hook_write_api_result_target_{dialog_nonce}")
        )
        timeout_seconds = _safe_int(
            st.session_state.get(f"suite_add_hook_write_api_timeout_seconds_{dialog_nonce}"),
            30,
        )
        cfg = {
            "commandCode": "writeApi",
            "commandType": "action",
            "method": method,
            "url": url,
            "bodyType": body_type,
            "timeoutSeconds": timeout_seconds or 30,
        }
        if query_params is not None:
            cfg["queryParams"] = query_params
        if headers:
            cfg["headers"] = headers
        if body_payload not in (None, ""):
            cfg["body"] = body_payload
        if result_target:
            cfg["result_target"] = result_target
    elif command_code == "saveTable":
        table_name = str(st.session_state.get(f"suite_add_hook_save_table_name_{dialog_nonce}") or "").strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "saveTable",
            "commandType": "action",
            "table_name": table_name,
        }
        if not _apply_reference_selection(
            cfg,
            selection=st.session_state.get(f"suite_add_hook_save_table_source_{dialog_nonce}"),
            path_key="source",
            source_code_key="sourceCode",
        ):
            return None, "Il campo Source variable e' obbligatorio."
        result_target = _normalize_api_result_target_input(
            st.session_state.get(f"suite_add_hook_save_table_result_target_{dialog_nonce}")
        )
        if result_target:
            cfg["result_target"] = result_target
    elif command_code == "dropTable":
        table_name = str(st.session_state.get(f"suite_add_hook_drop_table_name_{dialog_nonce}") or "").strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "dropTable",
            "commandType": "action",
            "table_name": table_name,
        }
    elif command_code == "cleanTable":
        table_name = str(st.session_state.get(f"suite_add_hook_clean_table_name_{dialog_nonce}") or "").strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "cleanTable",
            "commandType": "action",
            "table_name": table_name,
        }
    elif command_code == "exportDataset":
        connection_id = str(
            st.session_state.get(f"suite_add_hook_export_dataset_connection_id_{dialog_nonce}") or ""
        ).strip()
        table_name = str(
            st.session_state.get(f"suite_add_hook_export_dataset_table_name_{dialog_nonce}") or ""
        ).strip()
        if not connection_id:
            return None, "Il campo Connection e' obbligatorio."
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "exportDataset",
            "commandType": "action",
            "connection_id": connection_id,
            "table_name": table_name,
            "mode": str(
                st.session_state.get(f"suite_add_hook_export_dataset_mode_{dialog_nonce}") or "append"
            ).strip(),
        }
        if not _apply_reference_selection(
            cfg,
            selection=st.session_state.get(f"suite_add_hook_export_dataset_source_{dialog_nonce}"),
            path_key="source",
            source_code_key="sourceCode",
        ):
            return None, "Il campo Source variable e' obbligatorio."
        dataset_id = str(
            st.session_state.get(f"suite_add_hook_export_dataset_dataset_id_{dialog_nonce}") or ""
        ).strip()
        dataset_description = str(
            st.session_state.get(f"suite_add_hook_export_dataset_dataset_description_{dialog_nonce}") or ""
        ).strip()
        result_target = _normalize_api_result_target_input(
            st.session_state.get(f"suite_add_hook_export_dataset_result_target_{dialog_nonce}")
        )
        mapping_keys = _normalize_compare_keys_input(
            st.session_state.get(f"suite_add_hook_export_dataset_mapping_keys_{dialog_nonce}")
        )
        if dataset_id:
            cfg["dataset_id"] = dataset_id
        if dataset_description:
            cfg["dataset_description"] = dataset_description
        if result_target:
            cfg["result_target"] = result_target
        if mapping_keys:
            cfg["mapping_keys"] = mapping_keys
    elif command_code == "dropDataset":
        dataset_id = str(
            st.session_state.get(f"suite_add_hook_drop_dataset_id_{dialog_nonce}") or ""
        ).strip()
        if not dataset_id:
            return None, "Il campo Dataset e' obbligatorio."
        cfg = {
            "commandCode": "dropDataset",
            "commandType": "action",
            "dataset_id": dataset_id,
        }
    elif command_code == "cleanDataset":
        dataset_id = str(
            st.session_state.get(f"suite_add_hook_clean_dataset_id_{dialog_nonce}") or ""
        ).strip()
        if not dataset_id:
            return None, "Il campo Dataset e' obbligatorio."
        cfg = {
            "commandCode": "cleanDataset",
            "commandType": "action",
            "dataset_id": dataset_id,
        }
    else:
        return None, f"Command type non supportato: {command_code}"

    return {
        "description": description,
        "operation_type": command_code,
        "configuration_json": cfg,
    }, None


def _build_test_command_draft(dialog_nonce: int, command_ui_code: str) -> tuple[dict | None, str | None]:
    description = str(
        st.session_state.get(f"suite_add_test_command_description_{dialog_nonce}") or ""
    ).strip()

    command_code = TEST_ACTION_COMMAND_MAPPING.get(command_ui_code, command_ui_code)
    cfg: dict[str, object]
    if command_code == "initConstant":
        name = str(st.session_state.get(f"suite_add_test_init_constant_name_{dialog_nonce}") or "").strip()
        context = str(
            st.session_state.get(f"suite_add_test_init_constant_context_{dialog_nonce}") or "local"
        ).strip()
        source_type = str(
            st.session_state.get(f"suite_add_test_init_constant_source_type_{dialog_nonce}") or "value"
        ).strip()
        if source_type == "raw":
            source_type = "value"
        if not name:
            return None, "Il campo Name e' obbligatorio."
        if source_type not in CONSTANT_SOURCE_OPTIONS:
            return None, "Runtime value type non supportato."
        cfg = {
            "commandCode": "setVariable",
            "commandType": "context",
            "name": name,
            "context": context,
            "valueType": source_type,
        }
        if source_type in {"value", "json"}:
            parsed_value, parse_error = _parse_json_input(
                st.session_state.get(f"suite_add_test_init_constant_value_{dialog_nonce}")
            )
            if parse_error:
                return None, parse_error
            cfg["value"] = parsed_value
        elif source_type == "function":
            function_name = str(
                st.session_state.get(f"suite_add_test_init_constant_function_name_{dialog_nonce}") or "now"
            ).strip().lower()
            cfg["functionName"] = function_name
    elif command_code == "readApi":
        url = str(st.session_state.get(f"suite_add_test_read_api_url_{dialog_nonce}") or "").strip()
        if not url:
            return None, "Il campo URL e' obbligatorio."
        query_params, query_params_error = _parse_json_input(
            st.session_state.get(f"suite_add_test_read_api_query_params_{dialog_nonce}")
        )
        if query_params_error:
            return None, query_params_error.replace("JSON", "Query params")
        if query_params is not None and not isinstance(query_params, (dict, list)):
            return None, "Il campo Query params deve essere un oggetto o array JSON."
        headers, headers_error = _parse_optional_json_object_input(
            st.session_state.get(f"suite_add_test_read_api_headers_{dialog_nonce}"),
            "Headers",
        )
        if headers_error:
            return None, headers_error
        result_target = _normalize_api_result_target_input(
            st.session_state.get(f"suite_add_test_read_api_result_target_{dialog_nonce}")
        )
        timeout_seconds = _safe_int(
            st.session_state.get(f"suite_add_test_read_api_timeout_seconds_{dialog_nonce}"),
            30,
        )
        cfg = {
            "commandCode": "readApi",
            "commandType": "action",
            "url": url,
            "timeoutSeconds": timeout_seconds or 30,
        }
        if query_params is not None:
            cfg["queryParams"] = query_params
        if headers:
            cfg["headers"] = headers
        if result_target:
            cfg["result_target"] = result_target
    elif command_code == "writeApi":
        method = str(
            st.session_state.get(f"suite_add_test_write_api_method_{dialog_nonce}") or "POST"
        ).strip().upper()
        url = str(st.session_state.get(f"suite_add_test_write_api_url_{dialog_nonce}") or "").strip()
        if not url:
            return None, "Il campo URL e' obbligatorio."
        query_params, query_params_error = _parse_json_input(
            st.session_state.get(f"suite_add_test_write_api_query_params_{dialog_nonce}")
        )
        if query_params_error:
            return None, query_params_error.replace("JSON", "Query params")
        if query_params is not None and not isinstance(query_params, (dict, list)):
            return None, "Il campo Query params deve essere un oggetto o array JSON."
        headers, headers_error = _parse_optional_json_object_input(
            st.session_state.get(f"suite_add_test_write_api_headers_{dialog_nonce}"),
            "Headers",
        )
        if headers_error:
            return None, headers_error
        body_type = str(
            st.session_state.get(f"suite_add_test_write_api_body_type_{dialog_nonce}") or "json"
        ).strip() or "json"
        if body_type == "json":
            body_payload, body_error = _parse_json_input(
                st.session_state.get(f"suite_add_test_write_api_body_{dialog_nonce}")
            )
            if body_error:
                return None, body_error
        elif body_type == "formUrlEncoded":
            body_payload, body_error = collect_guided_kv_rows(
                st.session_state.get(f"suite_add_test_write_api_form_rows_{dialog_nonce}") or [],
                f"suite_add_test_write_api_form_rows_row_{dialog_nonce}",
                "Body",
                allowed_modes=FORM_URLENCODED_ALLOWED_MODES,
                scalar_only=True,
            )
            if body_error:
                return None, body_error
        else:
            body_payload = str(
                st.session_state.get(f"suite_add_test_write_api_body_{dialog_nonce}") or ""
            )
        result_target = _normalize_api_result_target_input(
            st.session_state.get(f"suite_add_test_write_api_result_target_{dialog_nonce}")
        )
        timeout_seconds = _safe_int(
            st.session_state.get(f"suite_add_test_write_api_timeout_seconds_{dialog_nonce}"),
            30,
        )
        cfg = {
            "commandCode": "writeApi",
            "commandType": "action",
            "method": method,
            "url": url,
            "bodyType": body_type,
            "timeoutSeconds": timeout_seconds or 30,
        }
        if query_params is not None:
            cfg["queryParams"] = query_params
        if headers:
            cfg["headers"] = headers
        if body_payload not in (None, ""):
            cfg["body"] = body_payload
        if result_target:
            cfg["result_target"] = result_target
    elif command_code == "sendMessageQueue":
        queue_id = str(
            st.session_state.get(f"suite_add_test_send_message_queue_id_{dialog_nonce}") or ""
        ).strip()
        if not queue_id:
            return None, "Il campo Queue e' obbligatorio."
        cfg = {
            "commandCode": "sendMessageQueue",
            "commandType": "action",
            "queue_id": queue_id,
        }
        if not _apply_reference_selection(
            cfg,
            selection=st.session_state.get(f"suite_add_test_send_message_source_{dialog_nonce}"),
            path_key="source",
            source_code_key="sourceCode",
        ):
            return None, "Il campo Source variable e' obbligatorio."
        template_enabled = bool(
            st.session_state.get(f"suite_add_test_send_message_template_enabled_{dialog_nonce}")
        )
        template_for_each = _normalize_json_path_input(
            st.session_state.get(f"suite_add_test_send_message_template_for_each_{dialog_nonce}")
        )
        template_fields = _normalize_compare_keys_input(
            st.session_state.get(f"suite_add_test_send_message_template_fields_{dialog_nonce}")
        )
        template_constants, template_constants_error = _parse_message_template_constants(
            st.session_state.get(f"suite_add_test_send_message_template_constants_rows_{dialog_nonce}")
        )
        if template_constants_error:
            return None, template_constants_error
        result_target = _normalize_api_result_target_input(
            st.session_state.get(f"suite_add_test_send_message_result_target_{dialog_nonce}")
        )
        if template_enabled:
            if not template_fields and not template_constants:
                return None, "Message template requires at least one field or constant."
            cfg["message_template"] = {
                "fields": template_fields,
                "constants": template_constants,
            }
            if template_for_each:
                cfg["message_template"]["forEach"] = template_for_each
        if result_target:
            cfg["result_target"] = result_target
    elif command_code == "saveTable":
        table_name = str(st.session_state.get(f"suite_add_test_save_table_name_{dialog_nonce}") or "").strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "saveTable",
            "commandType": "action",
            "table_name": table_name,
        }
        if not _apply_reference_selection(
            cfg,
            selection=st.session_state.get(f"suite_add_test_save_table_source_{dialog_nonce}"),
            path_key="source",
            source_code_key="sourceCode",
        ):
            return None, "Il campo Source variable e' obbligatorio."
        result_target = _normalize_api_result_target_input(
            st.session_state.get(f"suite_add_test_save_table_result_target_{dialog_nonce}")
        )
        if result_target:
            cfg["result_target"] = result_target
    elif command_code == "dropTable":
        table_name = str(st.session_state.get(f"suite_add_test_drop_table_name_{dialog_nonce}") or "").strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "dropTable",
            "commandType": "action",
            "table_name": table_name,
        }
    elif command_code == "cleanTable":
        table_name = str(st.session_state.get(f"suite_add_test_clean_table_name_{dialog_nonce}") or "").strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "cleanTable",
            "commandType": "action",
            "table_name": table_name,
        }
    elif command_code == "exportDataset":
        connection_id = str(
            st.session_state.get(f"suite_add_test_export_dataset_connection_id_{dialog_nonce}") or ""
        ).strip()
        table_name = str(
            st.session_state.get(f"suite_add_test_export_dataset_table_name_{dialog_nonce}") or ""
        ).strip()
        if not connection_id:
            return None, "Il campo Connection e' obbligatorio."
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        cfg = {
            "commandCode": "exportDataset",
            "commandType": "action",
            "connection_id": connection_id,
            "table_name": table_name,
            "mode": str(
                st.session_state.get(f"suite_add_test_export_dataset_mode_{dialog_nonce}") or "append"
            ).strip(),
        }
        if not _apply_reference_selection(
            cfg,
            selection=st.session_state.get(f"suite_add_test_export_dataset_source_{dialog_nonce}"),
            path_key="source",
            source_code_key="sourceCode",
        ):
            return None, "Il campo Source variable e' obbligatorio."
        dataset_id = str(
            st.session_state.get(f"suite_add_test_export_dataset_dataset_id_{dialog_nonce}") or ""
        ).strip()
        dataset_description = str(
            st.session_state.get(f"suite_add_test_export_dataset_dataset_description_{dialog_nonce}") or ""
        ).strip()
        result_target = _normalize_api_result_target_input(
            st.session_state.get(f"suite_add_test_export_dataset_result_target_{dialog_nonce}")
        )
        mapping_keys = _normalize_compare_keys_input(
            st.session_state.get(f"suite_add_test_export_dataset_mapping_keys_{dialog_nonce}")
        )
        if dataset_id:
            cfg["dataset_id"] = dataset_id
        if dataset_description:
            cfg["dataset_description"] = dataset_description
        if result_target:
            cfg["result_target"] = result_target
        if mapping_keys:
            cfg["mapping_keys"] = mapping_keys
    elif command_code == "dropDataset":
        dataset_id = str(
            st.session_state.get(f"suite_add_test_drop_dataset_id_{dialog_nonce}") or ""
        ).strip()
        if not dataset_id:
            return None, "Il campo Dataset e' obbligatorio."
        cfg = {
            "commandCode": "dropDataset",
            "commandType": "action",
            "dataset_id": dataset_id,
        }
    elif command_code == "cleanDataset":
        dataset_id = str(
            st.session_state.get(f"suite_add_test_clean_dataset_id_{dialog_nonce}") or ""
        ).strip()
        if not dataset_id:
            return None, "Il campo Dataset e' obbligatorio."
        cfg = {
            "commandCode": "cleanDataset",
            "commandType": "action",
            "dataset_id": dataset_id,
        }
    elif command_code in TEST_ASSERT_COMMAND_CODES:
        cfg = {
            "commandCode": command_code,
            "commandType": "assert",
        }
        error_message = str(
            st.session_state.get(f"suite_add_test_assert_error_message_{dialog_nonce}") or ""
        ).strip()
        if not _apply_reference_selection(
            cfg,
            selection=st.session_state.get(f"suite_add_test_assert_actual_{dialog_nonce}"),
            path_key="actual",
            source_code_key="actualSourceCode",
        ):
            return None, "Il campo Actual variable e' obbligatorio."
        if error_message:
            cfg["error_message"] = error_message
        if command_code in {"jsonEquals", "jsonContains"}:
            expected_mode = str(
                st.session_state.get(f"suite_add_test_assert_expected_mode_{dialog_nonce}") or "manual"
            ).strip().lower()
            if expected_mode == "variable":
                expected_cfg: dict[str, object] = {}
                if not _apply_reference_selection(
                    expected_cfg,
                    selection=st.session_state.get(f"suite_add_test_assert_expected_variable_{dialog_nonce}"),
                    path_key="expectedRefPath",
                    source_code_key="expectedSourceCode",
                ):
                    return None, "Il campo Expected variable e' obbligatorio."
                if expected_cfg.get("expectedSourceCode"):
                    cfg["expectedSourceCode"] = expected_cfg["expectedSourceCode"]
                else:
                    cfg["expected"] = {"$ref": expected_cfg["expectedRefPath"]}
            else:
                expected, expected_error = _parse_json_input(
                    st.session_state.get(f"suite_add_test_assert_expected_{dialog_nonce}")
                )
                if expected_error:
                    return None, expected_error
                if expected is None:
                    return None, "Il campo Expected e' obbligatorio."
                if command_code == "jsonContains" and not isinstance(expected, dict):
                    return None, "Expected deve essere un oggetto JSON."
                cfg["expected"] = expected
        if command_code == "jsonEquals" and cfg.get("expected") is None:
            return None, "Il campo Expected e' obbligatorio."
        if command_code == "jsonContains":
            compare_keys = _normalize_compare_keys_input(
                st.session_state.get(f"suite_add_test_assert_compare_keys_{dialog_nonce}")
            )
            if not compare_keys:
                return None, "Il campo Compare keys e' obbligatorio."
            cfg["compare_keys"] = compare_keys
        if command_code in {"jsonArrayContains", "jsonArrayEquals"}:
            expected_json_array_id = str(
                st.session_state.get(f"suite_add_test_assert_expected_json_array_id_{dialog_nonce}") or ""
            ).strip()
            if not expected_json_array_id:
                return None, "Il campo Expected json-array e' obbligatorio."
            cfg["expected_json_array_id"] = expected_json_array_id
            compare_keys = _normalize_compare_keys_input(
                st.session_state.get(f"suite_add_test_assert_compare_keys_{dialog_nonce}")
            )
            if not compare_keys:
                return None, "Il campo Compare keys e' obbligatorio."
            cfg["compare_keys"] = compare_keys
    else:
        return None, f"Command type non supportato: {command_ui_code}"

    return {
        "description": description,
        "operation_type": command_code,
        "configuration_json": cfg,
    }, None


def _initialize_hook_command_form(
    dialog_nonce: int,
    command_item: dict,
    brokers: list[dict],
    *,
    default_context: str,
    key_prefix: str,
):
    initialized_key = _command_form_key(key_prefix, dialog_nonce, "initialized")
    if st.session_state.get(initialized_key):
        return

    configuration_json = _safe_dict(command_item.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json)
    st.session_state[_command_form_key(key_prefix, dialog_nonce, "description")] = str(
        command_item.get("description") or ""
    )
    st.session_state[_command_form_key(key_prefix, dialog_nonce, "command_type")] = command_code

    if command_code == "initConstant":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_name")] = str(
            configuration_json.get("name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_context")] = default_context
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_source_type")] = str(
            configuration_json.get("valueType") or configuration_json.get("sourceType") or "value"
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_value")] = _stringify_form_value(
            configuration_json.get("value")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_function_name")] = str(
            configuration_json.get("functionName") or "now"
        )
    elif command_code == "deleteConstant":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "delete_constant_name")] = str(
            configuration_json.get("name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "delete_constant_context")] = default_context
    elif command_code == "readApi":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "read_api_url")] = str(
            configuration_json.get("url") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "read_api_query_params")] = _stringify_form_value(
            configuration_json.get("queryParams")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "read_api_headers")] = _stringify_form_value(
            configuration_json.get("headers")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "read_api_timeout_seconds")] = _safe_int(
            configuration_json.get("timeoutSeconds"),
            30,
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "read_api_result_target")] = (
            _api_result_target_label(configuration_json)
        )
    elif command_code == "writeApi":
        body_type = str(configuration_json.get("bodyType") or "json").strip()
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_method")] = str(
            configuration_json.get("method") or "POST"
        ).upper()
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_url")] = str(
            configuration_json.get("url") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_query_params")] = _stringify_form_value(
            configuration_json.get("queryParams")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_headers")] = _stringify_form_value(
            configuration_json.get("headers")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_body_type")] = body_type
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_body")] = _stringify_form_value(
            configuration_json.get("body")
        )
        ensure_guided_kv_state(
            _command_form_key(key_prefix, dialog_nonce, "write_api_form_rows"),
            configuration_json.get("body") if body_type == "formUrlEncoded" else {},
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_timeout_seconds")] = _safe_int(
            configuration_json.get("timeoutSeconds"),
            30,
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_result_target")] = (
            _api_result_target_label(configuration_json)
        )
    elif command_code == "saveTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_source")] = _source_selection_value(
            configuration_json.get("source"),
            configuration_json.get("sourceCode"),
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_result_target")] = (
            _api_result_target_label(configuration_json)
        )
    elif command_code == "dropTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "drop_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
    elif command_code == "cleanTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "clean_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
    elif command_code == "exportDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_connection_id")] = str(
            configuration_json.get("connection_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_source")] = _source_selection_value(
            configuration_json.get("source"),
            configuration_json.get("sourceCode"),
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_mode")] = str(
            configuration_json.get("mode") or "append"
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_mapping_keys")] = _normalize_compare_keys_input(
            configuration_json.get("mapping_keys")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_description")] = str(
            configuration_json.get("dataset_description") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_result_target")] = (
            _api_result_target_label(configuration_json)
        )
    elif command_code == "dropDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "drop_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
    elif command_code == "cleanDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "clean_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )

    st.session_state[initialized_key] = True


def _initialize_test_command_form(
    dialog_nonce: int,
    command_item: dict,
    json_arrays: list[dict],
    brokers: list[dict],
    *,
    key_prefix: str,
):
    initialized_key = _command_form_key(key_prefix, dialog_nonce, "initialized")
    if st.session_state.get(initialized_key):
        return

    configuration_json = _safe_dict(command_item.get("configuration_json") or {})
    command_code = _normalize_command_code(configuration_json)
    st.session_state[_command_form_key(key_prefix, dialog_nonce, "description")] = str(
        command_item.get("description") or ""
    )
    st.session_state[_command_form_key(key_prefix, dialog_nonce, "command_type")] = command_code

    if command_code == "initConstant":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_name")] = str(
            configuration_json.get("name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_context")] = "local"
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_source_type")] = str(
            configuration_json.get("valueType") or configuration_json.get("sourceType") or "value"
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_value")] = _stringify_form_value(
            configuration_json.get("value")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "init_constant_function_name")] = str(
            configuration_json.get("functionName") or "now"
        )
    elif command_code == "readApi":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "read_api_url")] = str(
            configuration_json.get("url") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "read_api_query_params")] = _stringify_form_value(
            configuration_json.get("queryParams")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "read_api_headers")] = _stringify_form_value(
            configuration_json.get("headers")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "read_api_timeout_seconds")] = _safe_int(
            configuration_json.get("timeoutSeconds"),
            30,
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "read_api_result_target")] = (
            _api_result_target_label(configuration_json)
        )
    elif command_code == "writeApi":
        body_type = str(configuration_json.get("bodyType") or "json").strip()
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_method")] = str(
            configuration_json.get("method") or "POST"
        ).upper()
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_url")] = str(
            configuration_json.get("url") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_query_params")] = _stringify_form_value(
            configuration_json.get("queryParams")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_headers")] = _stringify_form_value(
            configuration_json.get("headers")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_body_type")] = body_type
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_body")] = _stringify_form_value(
            configuration_json.get("body")
        )
        ensure_guided_kv_state(
            _command_form_key(key_prefix, dialog_nonce, "write_api_form_rows"),
            configuration_json.get("body") if body_type == "formUrlEncoded" else {},
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_timeout_seconds")] = _safe_int(
            configuration_json.get("timeoutSeconds"),
            30,
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "write_api_result_target")] = (
            _api_result_target_label(configuration_json)
        )
    elif command_code == "sendMessageQueue":
        queue_id = str(configuration_json.get("queue_id") or "")
        message_template = _safe_dict(
            configuration_json.get("message_template")
            or configuration_json.get("messageTemplate")
            or {}
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_broker_id")] = (
            _find_broker_id_for_queue_id(queue_id, brokers)
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_queue_id")] = queue_id
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_source")] = _source_selection_value(
            configuration_json.get("source"),
            configuration_json.get("sourceCode"),
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_template_enabled")] = bool(
            message_template
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_template_for_each")] = str(
            message_template.get("forEach") or message_template.get("for_each") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_template_fields")] = (
            _normalize_compare_keys_input(message_template.get("fields"))
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_template_constants_rows")] = (
            _send_message_template_constant_rows(message_template.get("constants"))
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_template_panel_open")] = False
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "send_message_result_target")] = (
            _api_result_target_label(configuration_json)
        )
    elif command_code == "saveTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_source")] = _source_selection_value(
            configuration_json.get("source"),
            configuration_json.get("sourceCode"),
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "save_table_result_target")] = (
            _api_result_target_label(configuration_json)
        )
    elif command_code == "dropTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "drop_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
    elif command_code == "cleanTable":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "clean_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
    elif command_code == "exportDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_connection_id")] = str(
            configuration_json.get("connection_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_table_name")] = str(
            configuration_json.get("table_name") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_source")] = _source_selection_value(
            configuration_json.get("source"),
            configuration_json.get("sourceCode"),
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_mode")] = str(
            configuration_json.get("mode") or "append"
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_mapping_keys")] = _normalize_compare_keys_input(
            configuration_json.get("mapping_keys")
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_description")] = str(
            configuration_json.get("dataset_description") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "export_dataset_result_target")] = (
            _api_result_target_label(configuration_json)
        )
    elif command_code == "dropDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "drop_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
    elif command_code == "cleanDataset":
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "clean_dataset_id")] = str(
            configuration_json.get("dataset_id") or ""
        )
    elif command_code in TEST_ASSERT_COMMAND_CODES:
        expected_value = configuration_json.get("expected")
        expected_mode = "manual"
        expected_variable = ""
        expected_manual = ""
        expected_ref = _extract_expected_ref_path(expected_value)
        if expected_ref:
            expected_mode = "variable"
            expected_variable = expected_ref
        elif str(configuration_json.get("expectedSourceCode") or "").strip():
            expected_mode = "variable"
            expected_variable = _source_selection_value(
                None,
                configuration_json.get("expectedSourceCode"),
            )
        elif expected_value is not None:
            expected_manual = _stringify_form_value(expected_value)
        elif command_code == "jsonContains":
            legacy_expected_json_array_id = configuration_json.get("expected_json_array_id")
            legacy_payload, legacy_error = _resolve_expected_json_array_payload(
                json_arrays,
                legacy_expected_json_array_id,
            )
            if legacy_error is None and isinstance(legacy_payload, dict):
                expected_manual = _stringify_form_value(legacy_payload)
            elif legacy_error is None and isinstance(legacy_payload, list) and legacy_payload:
                first_item = legacy_payload[0]
                if isinstance(first_item, dict):
                    expected_manual = _stringify_form_value(first_item)

        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_error_message")] = str(
            configuration_json.get("error_message") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_actual")] = _source_selection_value(
            configuration_json.get("actual"),
            configuration_json.get("actualSourceCode"),
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_expected_mode")] = expected_mode
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_expected")] = expected_manual
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_expected_variable")] = expected_variable
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_expected_json_array_id")] = str(
            configuration_json.get("expected_json_array_id") or ""
        )
        st.session_state[_command_form_key(key_prefix, dialog_nonce, "assert_compare_keys")] = _normalize_compare_keys_input(
            configuration_json.get("compare_keys")
        )

    st.session_state[initialized_key] = True


def _render_hook_command_form(
    dialog_nonce: int,
    command_group: str,
    json_arrays: list[dict],
    datasources: list[dict],
    brokers: list[dict],
    connections: list[dict],
    draft: dict,
    item: dict,
    *,
    stop_before_index: int | None,
    default_context: str,
    key_prefix: str,
) -> str:
    allowed_command_codes = HOOK_CONTEXT_COMMAND_CODES if command_group == "context" else HOOK_ACTION_COMMAND_CODES
    command_type_key = _command_form_key(key_prefix, dialog_nonce, "command_type")
    current_command_code = str(st.session_state.get(command_type_key) or "").strip()
    if current_command_code not in allowed_command_codes and allowed_command_codes:
        st.session_state[command_type_key] = allowed_command_codes[0]

    command_code = st.selectbox(
        "Command type",
        options=allowed_command_codes,
        format_func=_hook_command_type_label,
        key=command_type_key,
    )

    if command_code == "initConstant":
        st.text_input("Name", key=_command_form_key(key_prefix, dialog_nonce, "init_constant_name"), placeholder="rows")
        context_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_context")
        st.session_state[context_key] = default_context
        source_type_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_source_type")
        current_source_type = str(st.session_state.get(source_type_key) or "").strip()
        if current_source_type not in CONSTANT_SOURCE_OPTIONS:
            st.session_state[source_type_key] = CONSTANT_SOURCE_OPTIONS[0]
        source_type = st.selectbox("Runtime value type", options=CONSTANT_SOURCE_OPTIONS, key=source_type_key)
        if source_type in {"value", "json"}:
            st.text_area(
                "Value",
                key=_command_form_key(key_prefix, dialog_nonce, "init_constant_value"),
                height=180,
                help="Per `value` puoi inserire testo o JSON. Per `json` inserisci JSON valido.",
            )
        elif source_type == "function":
            st.selectbox(
                "Function",
                options=["now", "today"],
                key=_command_form_key(key_prefix, dialog_nonce, "init_constant_function_name"),
            )
    elif command_code == "deleteConstant":
        st.text_input("Name", key=_command_form_key(key_prefix, dialog_nonce, "delete_constant_name"), placeholder="rows")
        delete_context_key = _command_form_key(key_prefix, dialog_nonce, "delete_constant_context")
        st.session_state[delete_context_key] = default_context
    elif command_code == "readApi":
        st.text_input("URL", key=_command_form_key(key_prefix, dialog_nonce, "read_api_url"), placeholder="https://api.example.com/orders")
        st.text_input(
            "Result target (optional)",
            key=_command_form_key(key_prefix, dialog_nonce, "read_api_result_target"),
            placeholder="readApiResult",
        )
    elif command_code == "writeApi":
        method_key = _command_form_key(key_prefix, dialog_nonce, "write_api_method")
        current_method = str(st.session_state.get(method_key) or "").strip().upper()
        if current_method not in HTTP_WRITE_METHOD_OPTIONS:
            st.session_state[method_key] = HTTP_WRITE_METHOD_OPTIONS[0]
        st.selectbox("Method", options=HTTP_WRITE_METHOD_OPTIONS, key=method_key)
        st.text_input("URL", key=_command_form_key(key_prefix, dialog_nonce, "write_api_url"), placeholder="https://api.example.com/orders")
        body_type_key = _command_form_key(key_prefix, dialog_nonce, "write_api_body_type")
        body_type = st.selectbox("Body type", options=HTTP_BODY_TYPE_OPTIONS, key=body_type_key)
        if body_type == "formUrlEncoded":
            render_guided_kv_rows_container(
                editor_state_key=_command_form_key(key_prefix, dialog_nonce, "write_api_form_rows"),
                key_prefix=_command_form_key(key_prefix, dialog_nonce, "write_api_form_rows_row"),
                use_container=True,
                available_constants=_resolve_available_http_form_runtime_constants(
                    draft,
                    item,
                    stop_before_index=stop_before_index,
                ),
                allowed_modes=FORM_URLENCODED_ALLOWED_MODES,
                show_runtime_field_path=True,
            )
        else:
            st.text_area(
                "Body",
                key=_command_form_key(key_prefix, dialog_nonce, "write_api_body"),
                height=180,
                help="Per `json` inserisci JSON valido. Per `text` inserisci testo libero.",
            )
        st.text_input(
            "Result target (optional)",
            key=_command_form_key(key_prefix, dialog_nonce, "write_api_result_target"),
            placeholder="writeApiResult",
        )
    elif command_code == "saveTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "save_table_name"))
        _render_source_constant_select(
            label="Source variable",
            key=_command_form_key(key_prefix, dialog_nonce, "save_table_source"),
            options=_resolve_available_source_constants(
                draft,
                item,
                command_code=command_code,
                stop_before_index=stop_before_index,
            ),
            help_text="Visible and compatible variables at this point.",
        )
        st.text_input("Result variable name", key=_command_form_key(key_prefix, dialog_nonce, "save_table_result_target"))
    elif command_code == "dropTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "drop_table_name"))
    elif command_code == "cleanTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "clean_table_name"))
    elif command_code == "exportDataset":
        connection_ids = [str(item.get("id")) for item in connections if item.get("id")]
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        source_key = _command_form_key(key_prefix, dialog_nonce, "export_dataset_source")
        st.selectbox(
            label="Source variable",
            key=source_key,
            options=_resolve_available_source_constants(
                draft,
                item,
                command_code=command_code,
                stop_before_index=stop_before_index,
            ),
            help_text="Visible and compatible variables at this point.",
        )
        st.selectbox(
            "Connection",
            options=connection_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in connections if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessuna connection disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_connection_id"),
            disabled=not bool(connection_ids),
        )
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_table_name"))
        st.selectbox("Mode", options=EXPORT_DATASET_MODE_OPTIONS, key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_mode"))
        mapping_keys_key = _command_form_key(key_prefix, dialog_nonce, "export_dataset_mapping_keys")
        mapping_key_options, mapping_key_error = _resolve_export_dataset_mapping_key_options(
            draft,
            item,
            source_path=st.session_state.get(source_key),
            stop_before_index=stop_before_index,
            json_arrays=json_arrays,
            datasources=datasources,
        )
        st.session_state[mapping_keys_key] = [
            key
            for key in _normalize_compare_keys_input(st.session_state.get(mapping_keys_key))
            if key in mapping_key_options
        ]
        st.multiselect(
            "Mapping keys (optional)",
            options=mapping_key_options,
            key=mapping_keys_key,
            disabled=not bool(mapping_key_options),
        )
        if mapping_key_error:
            st.info(mapping_key_error)
        st.selectbox(
            "Existing dataset (optional)",
            options=[""] + dataset_ids,
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Create new dataset",
            key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_id"),
        )
        st.text_input("Dataset description (optional)", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_description"))
        st.text_input("Result variable name", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_result_target"))
    elif command_code == "dropDataset":
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Dataset",
            options=dataset_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun dataset disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "drop_dataset_id"),
            disabled=not bool(dataset_ids),
        )
    elif command_code == "cleanDataset":
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Dataset",
            options=dataset_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun dataset disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "clean_dataset_id"),
            disabled=not bool(dataset_ids),
        )
    st.text_input(
        "Comment",
        key=_command_form_key(key_prefix, dialog_nonce, "description"),
    )
    return command_code


def _render_test_command_form(
    dialog_nonce: int,
    command_group: str,
    json_arrays: list[dict],
    datasources: list[dict],
    brokers: list[dict],
    connections: list[dict],
    draft: dict,
    item: dict,
    *,
    stop_before_index: int | None,
    key_prefix: str,
    show_comment: bool = True,
) -> str:
    if command_group == "constant":
        command_options = TEST_CONSTANT_COMMAND_CODES
    elif command_group == "assert":
        command_options = TEST_ASSERT_COMMAND_CODES
    else:
        command_options = [item[0] for item in TEST_ACTION_COMMAND_OPTIONS]

    command_type_key = _command_form_key(key_prefix, dialog_nonce, "command_type")
    current_command_ui_code = str(st.session_state.get(command_type_key) or "").strip()
    if current_command_ui_code not in command_options and command_options:
        st.session_state[command_type_key] = command_options[0]

    if command_group == "constant":
        command_ui_code = command_options[0] if command_options else ""
        st.session_state[command_type_key] = command_ui_code
    else:
        command_ui_code = st.selectbox(
            "Command type",
            options=command_options,
            format_func=lambda code: (
                _command_ui_label(
                    {"configuration_json": {"commandCode": TEST_ACTION_COMMAND_MAPPING.get(str(code), str(code))}}
                )
                if command_group == "action"
                else str(code)
            ),
            key=command_type_key,
        )
    command_code = TEST_ACTION_COMMAND_MAPPING.get(command_ui_code, command_ui_code)

    if command_code == "initConstant":
        st.text_input("Name", key=_command_form_key(key_prefix, dialog_nonce, "init_constant_name"), placeholder="rows")
        context_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_context")
        st.session_state[context_key] = "local"
        source_type_key = _command_form_key(key_prefix, dialog_nonce, "init_constant_source_type")
        current_source_type = str(st.session_state.get(source_type_key) or "").strip()
        if current_source_type not in CONSTANT_SOURCE_OPTIONS:
            st.session_state[source_type_key] = CONSTANT_SOURCE_OPTIONS[0]
        source_type = st.selectbox("Runtime value type", options=CONSTANT_SOURCE_OPTIONS, key=source_type_key)
        if source_type in {"value", "json"}:
            st.text_area("Value", key=_command_form_key(key_prefix, dialog_nonce, "init_constant_value"), height=180, help="Per `value` puoi inserire testo o JSON. Per `json` inserisci JSON valido.")
        elif source_type == "function":
            st.selectbox(
                "Function",
                options=["now", "today"],
                key=_command_form_key(key_prefix, dialog_nonce, "init_constant_function_name"),
            )
    elif command_code == "readApi":
        st.text_input("URL", key=_command_form_key(key_prefix, dialog_nonce, "read_api_url"), placeholder="https://api.example.com/orders")
        st.text_input(
            "Result target (optional)",
            key=_command_form_key(key_prefix, dialog_nonce, "read_api_result_target"),
            placeholder="readApiResult",
        )
    elif command_code == "writeApi":
        method_key = _command_form_key(key_prefix, dialog_nonce, "write_api_method")
        current_method = str(st.session_state.get(method_key) or "").strip().upper()
        if current_method not in HTTP_WRITE_METHOD_OPTIONS:
            st.session_state[method_key] = HTTP_WRITE_METHOD_OPTIONS[0]
        st.selectbox("Method", options=HTTP_WRITE_METHOD_OPTIONS, key=method_key)
        st.text_input("URL", key=_command_form_key(key_prefix, dialog_nonce, "write_api_url"), placeholder="https://api.example.com/orders")
        body_type_key = _command_form_key(key_prefix, dialog_nonce, "write_api_body_type")
        body_type = st.selectbox("Body type", options=HTTP_BODY_TYPE_OPTIONS, key=body_type_key)
        if body_type == "formUrlEncoded":
            render_guided_kv_rows_container(
                editor_state_key=_command_form_key(key_prefix, dialog_nonce, "write_api_form_rows"),
                key_prefix=_command_form_key(key_prefix, dialog_nonce, "write_api_form_rows_row"),
                use_container=True,
                available_constants=_resolve_available_http_form_runtime_constants(
                    draft,
                    item,
                    stop_before_index=stop_before_index,
                ),
                allowed_modes=FORM_URLENCODED_ALLOWED_MODES,
                show_runtime_field_path=True,
            )
        else:
            st.text_area(
                "Body",
                key=_command_form_key(key_prefix, dialog_nonce, "write_api_body"),
                height=180,
                help="Per `json` inserisci JSON valido. Per `text` inserisci testo libero.",
            )
        st.text_input(
            "Result target (optional)",
            key=_command_form_key(key_prefix, dialog_nonce, "write_api_result_target"),
            placeholder="writeApiResult",
        )
    elif command_code == "sendMessageQueue":
        source_options = _resolve_available_source_constants(
            draft,
            item,
            command_code=command_code,
            stop_before_index=stop_before_index,
        )
        _render_source_constant_select(
            label="Source variable",
            key=_command_form_key(key_prefix, dialog_nonce, "send_message_source"),
            options=source_options,
            help_text="Visible and compatible variables at this point.",
        )
        broker_ids = [str(item.get("id")) for item in brokers if item.get("id")]
        broker_key = _command_form_key(key_prefix, dialog_nonce, "send_message_broker_id")
        current_broker_id = str(st.session_state.get(broker_key) or "").strip()
        if current_broker_id not in broker_ids and broker_ids:
            st.session_state[broker_key] = broker_ids[0]
        selected_broker_id = st.selectbox(
            "Broker",
            options=broker_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in brokers if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun broker disponibile",
            key=broker_key,
            disabled=not bool(broker_ids),
        )
        queues = load_test_editor_queues_for_broker(selected_broker_id, force=False) if selected_broker_id else []
        queue_ids = [str(item.get("id")) for item in queues if item.get("id")]
        queue_key = _command_form_key(key_prefix, dialog_nonce, "send_message_queue_id")
        current_queue_id = str(st.session_state.get(queue_key) or "").strip()
        if current_queue_id not in queue_ids and queue_ids:
            st.session_state[queue_key] = queue_ids[0]
        st.selectbox(
            "Queue",
            options=queue_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in queues if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessuna queue disponibile",
            key=queue_key,
            disabled=not bool(queue_ids),
        )
        st.text_input("Result variable name", key=_command_form_key(key_prefix, dialog_nonce, "send_message_result_target"))
        _render_send_message_preview(
            key_prefix=key_prefix,
            dialog_nonce=dialog_nonce,
            source_options=source_options,
            json_arrays=json_arrays,
            datasources=datasources,
        )
        _render_send_message_template_management(
            key_prefix=key_prefix,
            dialog_nonce=dialog_nonce,
            source_options=source_options,
            json_arrays=json_arrays,
            datasources=datasources,
        )
    elif command_code == "saveTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "save_table_name"))
        _render_source_constant_select(
            label="Source variable",
            key=_command_form_key(key_prefix, dialog_nonce, "save_table_source"),
            options=_resolve_available_source_constants(
                draft,
                item,
                command_code=command_code,
                stop_before_index=stop_before_index,
            ),
            help_text="Visible and compatible variables at this point.",
        )
        st.text_input("Result variable name", key=_command_form_key(key_prefix, dialog_nonce, "save_table_result_target"))
    elif command_code == "dropTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "drop_table_name"))
    elif command_code == "cleanTable":
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "clean_table_name"))
    elif command_code == "exportDataset":
        connection_ids = [str(item.get("id")) for item in connections if item.get("id")]
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        source_key = _command_form_key(key_prefix, dialog_nonce, "export_dataset_source")
        _render_source_constant_select(
            label="Source variable",
            key=source_key,
            options=_resolve_available_source_constants(
                draft,
                item,
                command_code=command_code,
                stop_before_index=stop_before_index,
            ),
            help_text="Visible and compatible variables at this point.",
        )
        st.selectbox(
            "Connection",
            options=connection_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in connections if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessuna connection disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_connection_id"),
            disabled=not bool(connection_ids),
        )
        st.text_input("Table name", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_table_name"))
        st.selectbox("Mode", options=EXPORT_DATASET_MODE_OPTIONS, key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_mode"))
        mapping_keys_key = _command_form_key(key_prefix, dialog_nonce, "export_dataset_mapping_keys")
        mapping_key_options, mapping_key_error = _resolve_export_dataset_mapping_key_options(
            draft,
            item,
            source_path=st.session_state.get(source_key),
            stop_before_index=stop_before_index,
            json_arrays=json_arrays,
            datasources=datasources,
        )
        st.session_state[mapping_keys_key] = [
            key
            for key in _normalize_compare_keys_input(st.session_state.get(mapping_keys_key))
            if key in mapping_key_options
        ]
        st.multiselect(
            "Mapping keys (optional)",
            options=mapping_key_options,
            key=mapping_keys_key,
            disabled=not bool(mapping_key_options),
        )
        if mapping_key_error:
            st.info(mapping_key_error)
        st.selectbox(
            "Existing dataset (optional)",
            options=[""] + dataset_ids,
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Create new dataset",
            key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_id"),
        )
        st.text_input("Dataset description (optional)", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_dataset_description"))
        st.text_input("Result variable name", key=_command_form_key(key_prefix, dialog_nonce, "export_dataset_result_target"))
    elif command_code == "dropDataset":
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Dataset",
            options=dataset_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun dataset disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "drop_dataset_id"),
            disabled=not bool(dataset_ids),
        )
    elif command_code == "cleanDataset":
        dataset_ids = [str(item.get("id")) for item in datasources if item.get("id")]
        st.selectbox(
            "Dataset",
            options=dataset_ids or [""],
            format_func=lambda item_id: _format_lookup_label(next((item for item in datasources if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun dataset disponibile",
            key=_command_form_key(key_prefix, dialog_nonce, "clean_dataset_id"),
            disabled=not bool(dataset_ids),
        )
    elif command_code in TEST_ASSERT_COMMAND_CODES:
        actual_options = _resolve_available_assert_constants(
            draft,
            item,
            command_code=command_code,
            stop_before_index=stop_before_index,
            role="actual",
        )
        st.text_input("Error message (optional)", key=_command_form_key(key_prefix, dialog_nonce, "assert_error_message"))
        _render_source_constant_select(
            label="Actual variable",
            key=_command_form_key(key_prefix, dialog_nonce, "assert_actual"),
            options=actual_options,
            help_text="Visible and compatible variables at this point.",
        )
        if command_code in {"jsonEquals", "jsonContains"}:
            expected_mode_key = _command_form_key(key_prefix, dialog_nonce, "assert_expected_mode")
            current_expected_mode = str(st.session_state.get(expected_mode_key) or "").strip().lower()
            if current_expected_mode not in ASSERT_EXPECTED_MODE_OPTIONS:
                st.session_state[expected_mode_key] = ASSERT_EXPECTED_MODE_OPTIONS[0]
            expected_mode = st.segmented_control(
                "Expected source",
                options=ASSERT_EXPECTED_MODE_OPTIONS,
                format_func=_assert_expected_mode_label,
                key=expected_mode_key,
            )
            if expected_mode == "variable":
                expected_options = _resolve_available_assert_constants(
                    draft,
                    item,
                    command_code=command_code,
                    stop_before_index=stop_before_index,
                    role="expected",
                )
                _render_source_constant_select(
                    label="Expected variable",
                    key=_command_form_key(key_prefix, dialog_nonce, "assert_expected_variable"),
                    options=expected_options,
                    help_text="Visible and compatible variables at this point.",
                )
            else:
                st.text_area(
                    "Expected",
                    key=_command_form_key(key_prefix, dialog_nonce, "assert_expected"),
                    height=120,
                    help="Inserisci JSON valido.",
                )
        if command_code == "jsonContains":
            compare_keys_key = _command_form_key(key_prefix, dialog_nonce, "assert_compare_keys")
            compare_key_options: list[str] = []
            compare_key_error: str | None = None
            expected_mode = str(
                st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "assert_expected_mode")) or "manual"
            ).strip().lower()
            if expected_mode == "variable":
                expected_variable = str(
                    st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "assert_expected_variable")) or ""
                ).strip()
                expected_options = _resolve_available_assert_constants(
                    draft,
                    item,
                    command_code=command_code,
                    stop_before_index=stop_before_index,
                    role="expected",
                )
                expected_definition = next(
                    (
                        option
                        for option in expected_options
                        if str(option.get("path") or "").strip() == expected_variable
                    ),
                    {},
                )
                compare_key_options = _json_object_keys(expected_definition.get("preview_value"))
                if expected_variable and not compare_key_options:
                    compare_key_error = "La variabile Expected selezionata non espone campi ispezionabili."
            else:
                expected_value, expected_error = _parse_json_input(
                    st.session_state.get(_command_form_key(key_prefix, dialog_nonce, "assert_expected"))
                )
                if expected_error:
                    compare_key_error = expected_error
                elif expected_value is not None:
                    compare_key_options = _json_object_keys(expected_value)
                    if not compare_key_options:
                        compare_key_error = "Expected deve essere un oggetto JSON."
            selected_compare_keys = [
                key
                for key in _normalize_compare_keys_input(st.session_state.get(compare_keys_key))
                if key in compare_key_options
            ]
            st.session_state[compare_keys_key] = selected_compare_keys
            st.multiselect(
                "Compare keys",
                options=compare_key_options,
                key=compare_keys_key,
                disabled=not bool(compare_key_options),
                help="Top-level keys from the expected JSON object.",
            )
            if compare_key_error:
                st.info(compare_key_error)
        if command_code in {"jsonArrayContains", "jsonArrayEquals"}:
            json_array_ids = [str(item.get("id")) for item in json_arrays if item.get("id")]
            selected_json_array_key = _command_form_key(key_prefix, dialog_nonce, "assert_expected_json_array_id")
            st.selectbox(
                "Expected json-array",
                options=[""] + json_array_ids,
                format_func=lambda item_id: _format_lookup_label(next((item for item in json_arrays if str(item.get("id")) == str(item_id)), {})) if item_id else "Nessun json-array selezionato",
                key=selected_json_array_key,
            )
            compare_keys_key = _command_form_key(key_prefix, dialog_nonce, "assert_compare_keys")
            compare_key_options, compare_key_error = _resolve_expected_json_array_compare_keys(
                json_arrays,
                st.session_state.get(selected_json_array_key),
            )
            selected_compare_keys = [
                key
                for key in _normalize_compare_keys_input(st.session_state.get(compare_keys_key))
                if key in compare_key_options
            ]
            st.session_state[compare_keys_key] = selected_compare_keys
            st.multiselect(
                "Compare keys",
                options=compare_key_options,
                key=compare_keys_key,
                disabled=not bool(compare_key_options),
                help="Top-level keys from the first expected JSON-array item.",
            )
            if compare_key_error and str(st.session_state.get(selected_json_array_key) or "").strip():
                st.info(compare_key_error)

    if show_comment:
        st.text_input(
            "Comment",
            key=_command_form_key(key_prefix, dialog_nonce, "description"),
        )
    return command_ui_code


def _build_hook_command_draft_with_prefix(
    dialog_nonce: int,
    command_code: str,
    *,
    key_prefix: str,
) -> tuple[dict | None, str | None]:
    field_mappings = [
        ("description", f"suite_add_hook_command_description_{dialog_nonce}"),
        ("command_type", f"suite_add_hook_command_type_{dialog_nonce}"),
        ("init_constant_name", f"suite_add_hook_init_constant_name_{dialog_nonce}"),
        ("init_constant_context", f"suite_add_hook_init_constant_context_{dialog_nonce}"),
        ("init_constant_source_type", f"suite_add_hook_init_constant_source_type_{dialog_nonce}"),
        ("init_constant_value", f"suite_add_hook_init_constant_value_{dialog_nonce}"),
        ("init_constant_json_array_id", f"suite_add_hook_init_constant_json_array_id_{dialog_nonce}"),
        ("init_constant_dataset_id", f"suite_add_hook_init_constant_dataset_id_{dialog_nonce}"),
        ("init_constant_queue_id", f"suite_add_hook_init_constant_queue_id_{dialog_nonce}"),
        ("init_constant_retry", f"suite_add_hook_init_constant_retry_{dialog_nonce}"),
        ("init_constant_wait_time_seconds", f"suite_add_hook_init_constant_wait_time_seconds_{dialog_nonce}"),
        ("init_constant_max_messages", f"suite_add_hook_init_constant_max_messages_{dialog_nonce}"),
        ("delete_constant_name", f"suite_add_hook_delete_constant_name_{dialog_nonce}"),
        ("delete_constant_context", f"suite_add_hook_delete_constant_context_{dialog_nonce}"),
        ("read_api_url", f"suite_add_hook_read_api_url_{dialog_nonce}"),
        ("read_api_query_params", f"suite_add_hook_read_api_query_params_{dialog_nonce}"),
        ("read_api_headers", f"suite_add_hook_read_api_headers_{dialog_nonce}"),
        ("read_api_timeout_seconds", f"suite_add_hook_read_api_timeout_seconds_{dialog_nonce}"),
        ("read_api_result_target", f"suite_add_hook_read_api_result_target_{dialog_nonce}"),
        ("write_api_method", f"suite_add_hook_write_api_method_{dialog_nonce}"),
        ("write_api_url", f"suite_add_hook_write_api_url_{dialog_nonce}"),
        ("write_api_query_params", f"suite_add_hook_write_api_query_params_{dialog_nonce}"),
        ("write_api_headers", f"suite_add_hook_write_api_headers_{dialog_nonce}"),
        ("write_api_body_type", f"suite_add_hook_write_api_body_type_{dialog_nonce}"),
        ("write_api_body", f"suite_add_hook_write_api_body_{dialog_nonce}"),
        ("write_api_form_rows", f"suite_add_hook_write_api_form_rows_{dialog_nonce}"),
        ("write_api_timeout_seconds", f"suite_add_hook_write_api_timeout_seconds_{dialog_nonce}"),
        ("write_api_result_target", f"suite_add_hook_write_api_result_target_{dialog_nonce}"),
        ("save_table_name", f"suite_add_hook_save_table_name_{dialog_nonce}"),
        ("save_table_source", f"suite_add_hook_save_table_source_{dialog_nonce}"),
        ("save_table_result_target", f"suite_add_hook_save_table_result_target_{dialog_nonce}"),
        ("drop_table_name", f"suite_add_hook_drop_table_name_{dialog_nonce}"),
        ("clean_table_name", f"suite_add_hook_clean_table_name_{dialog_nonce}"),
        ("export_dataset_connection_id", f"suite_add_hook_export_dataset_connection_id_{dialog_nonce}"),
        ("export_dataset_table_name", f"suite_add_hook_export_dataset_table_name_{dialog_nonce}"),
        ("export_dataset_source", f"suite_add_hook_export_dataset_source_{dialog_nonce}"),
        ("export_dataset_mode", f"suite_add_hook_export_dataset_mode_{dialog_nonce}"),
        ("export_dataset_mapping_keys", f"suite_add_hook_export_dataset_mapping_keys_{dialog_nonce}"),
        ("export_dataset_dataset_id", f"suite_add_hook_export_dataset_dataset_id_{dialog_nonce}"),
        ("export_dataset_dataset_description", f"suite_add_hook_export_dataset_dataset_description_{dialog_nonce}"),
        ("export_dataset_result_target", f"suite_add_hook_export_dataset_result_target_{dialog_nonce}"),
        ("drop_dataset_id", f"suite_add_hook_drop_dataset_id_{dialog_nonce}"),
        ("clean_dataset_id", f"suite_add_hook_clean_dataset_id_{dialog_nonce}"),
    ]
    overlay_state = {
        key: st.session_state.get(key)
        for key in st.session_state.keys()
    }
    for source_suffix, legacy_key in field_mappings:
        value = st.session_state.get(_command_form_key(key_prefix, dialog_nonce, source_suffix))
        if value is None:
            overlay_state.pop(legacy_key, None)
        else:
            overlay_state[legacy_key] = value
    original_session_state = st.session_state
    try:
        st.session_state = overlay_state
        return _build_hook_command_draft(dialog_nonce, command_code)
    finally:
        st.session_state = original_session_state


def _build_test_command_draft_with_prefix(
    dialog_nonce: int,
    command_ui_code: str,
    *,
    key_prefix: str,
) -> tuple[dict | None, str | None]:
    field_mappings = [
        ("description", f"suite_add_test_command_description_{dialog_nonce}"),
        ("command_type", f"suite_add_test_command_type_{dialog_nonce}"),
        ("init_constant_name", f"suite_add_test_init_constant_name_{dialog_nonce}"),
        ("init_constant_context", f"suite_add_test_init_constant_context_{dialog_nonce}"),
        ("init_constant_source_type", f"suite_add_test_init_constant_source_type_{dialog_nonce}"),
        ("init_constant_value", f"suite_add_test_init_constant_value_{dialog_nonce}"),
        ("init_constant_json_array_id", f"suite_add_test_init_constant_json_array_id_{dialog_nonce}"),
        ("init_constant_dataset_id", f"suite_add_test_init_constant_dataset_id_{dialog_nonce}"),
        ("init_constant_broker_id", f"suite_add_test_init_constant_broker_id_{dialog_nonce}"),
        ("init_constant_queue_id", f"suite_add_test_init_constant_queue_id_{dialog_nonce}"),
        ("init_constant_retry", f"suite_add_test_init_constant_retry_{dialog_nonce}"),
        ("init_constant_wait_time_seconds", f"suite_add_test_init_constant_wait_time_seconds_{dialog_nonce}"),
        ("init_constant_max_messages", f"suite_add_test_init_constant_max_messages_{dialog_nonce}"),
        ("read_api_url", f"suite_add_test_read_api_url_{dialog_nonce}"),
        ("read_api_query_params", f"suite_add_test_read_api_query_params_{dialog_nonce}"),
        ("read_api_headers", f"suite_add_test_read_api_headers_{dialog_nonce}"),
        ("read_api_timeout_seconds", f"suite_add_test_read_api_timeout_seconds_{dialog_nonce}"),
        ("read_api_result_target", f"suite_add_test_read_api_result_target_{dialog_nonce}"),
        ("write_api_method", f"suite_add_test_write_api_method_{dialog_nonce}"),
        ("write_api_url", f"suite_add_test_write_api_url_{dialog_nonce}"),
        ("write_api_query_params", f"suite_add_test_write_api_query_params_{dialog_nonce}"),
        ("write_api_headers", f"suite_add_test_write_api_headers_{dialog_nonce}"),
        ("write_api_body_type", f"suite_add_test_write_api_body_type_{dialog_nonce}"),
        ("write_api_body", f"suite_add_test_write_api_body_{dialog_nonce}"),
        ("write_api_form_rows", f"suite_add_test_write_api_form_rows_{dialog_nonce}"),
        ("write_api_timeout_seconds", f"suite_add_test_write_api_timeout_seconds_{dialog_nonce}"),
        ("write_api_result_target", f"suite_add_test_write_api_result_target_{dialog_nonce}"),
        ("send_message_broker_id", f"suite_add_test_send_message_broker_id_{dialog_nonce}"),
        ("send_message_queue_id", f"suite_add_test_send_message_queue_id_{dialog_nonce}"),
        ("send_message_source", f"suite_add_test_send_message_source_{dialog_nonce}"),
        ("send_message_template_enabled", f"suite_add_test_send_message_template_enabled_{dialog_nonce}"),
        ("send_message_template_for_each", f"suite_add_test_send_message_template_for_each_{dialog_nonce}"),
        ("send_message_template_fields", f"suite_add_test_send_message_template_fields_{dialog_nonce}"),
        ("send_message_template_constants_rows", f"suite_add_test_send_message_template_constants_rows_{dialog_nonce}"),
        ("send_message_result_target", f"suite_add_test_send_message_result_target_{dialog_nonce}"),
        ("save_table_name", f"suite_add_test_save_table_name_{dialog_nonce}"),
        ("save_table_source", f"suite_add_test_save_table_source_{dialog_nonce}"),
        ("save_table_result_target", f"suite_add_test_save_table_result_target_{dialog_nonce}"),
        ("drop_table_name", f"suite_add_test_drop_table_name_{dialog_nonce}"),
        ("clean_table_name", f"suite_add_test_clean_table_name_{dialog_nonce}"),
        ("export_dataset_connection_id", f"suite_add_test_export_dataset_connection_id_{dialog_nonce}"),
        ("export_dataset_table_name", f"suite_add_test_export_dataset_table_name_{dialog_nonce}"),
        ("export_dataset_source", f"suite_add_test_export_dataset_source_{dialog_nonce}"),
        ("export_dataset_mode", f"suite_add_test_export_dataset_mode_{dialog_nonce}"),
        ("export_dataset_mapping_keys", f"suite_add_test_export_dataset_mapping_keys_{dialog_nonce}"),
        ("export_dataset_dataset_id", f"suite_add_test_export_dataset_dataset_id_{dialog_nonce}"),
        ("export_dataset_dataset_description", f"suite_add_test_export_dataset_dataset_description_{dialog_nonce}"),
        ("export_dataset_result_target", f"suite_add_test_export_dataset_result_target_{dialog_nonce}"),
        ("drop_dataset_id", f"suite_add_test_drop_dataset_id_{dialog_nonce}"),
        ("clean_dataset_id", f"suite_add_test_clean_dataset_id_{dialog_nonce}"),
        ("assert_error_message", f"suite_add_test_assert_error_message_{dialog_nonce}"),
        ("assert_actual", f"suite_add_test_assert_actual_{dialog_nonce}"),
        ("assert_expected_mode", f"suite_add_test_assert_expected_mode_{dialog_nonce}"),
        ("assert_expected", f"suite_add_test_assert_expected_{dialog_nonce}"),
        ("assert_expected_variable", f"suite_add_test_assert_expected_variable_{dialog_nonce}"),
        ("assert_expected_json_array_id", f"suite_add_test_assert_expected_json_array_id_{dialog_nonce}"),
        ("assert_compare_keys", f"suite_add_test_assert_compare_keys_{dialog_nonce}"),
    ]
    overlay_state = {
        key: st.session_state.get(key)
        for key in st.session_state.keys()
    }
    for source_suffix, legacy_key in field_mappings:
        value = st.session_state.get(_command_form_key(key_prefix, dialog_nonce, source_suffix))
        if value is None:
            overlay_state.pop(legacy_key, None)
        else:
            overlay_state[legacy_key] = value
    original_session_state = st.session_state
    try:
        st.session_state = overlay_state
        return _build_test_command_draft(dialog_nonce, command_ui_code)
    finally:
        st.session_state = original_session_state


def _render_suite_item_operation(
    item: dict,
    operation: dict,
    op_idx: int,
    owner_kind: str,
):
    item_ui_key = str(item.get("_ui_key") or new_ui_key())
    item["_ui_key"] = item_ui_key
    operation_ui_key = str(operation.get("_ui_key") or f"{item_ui_key}_op_{op_idx}")
    operation["_ui_key"] = operation_ui_key
    command_group = (
        _resolve_hook_command_group(operation.get("configuration_json"))
        if owner_kind == "hook"
        else _resolve_test_command_group(operation.get("configuration_json"))
    )
    cfg = _safe_dict(operation.get("configuration_json") or {})
    command_code = _normalize_command_code(cfg)
    operation_index, current_operation = _find_operation_by_ui_key(item, operation_ui_key)
    if not isinstance(current_operation, dict):
        return
    action_label = _command_action_label(current_operation)
    is_first = operation_index <= 0
    is_last = operation_index >= len(_operation_list(item)) - 1

    if command_code in ("readApi", "writeApi"):
        _render_api_command_inline(
            item,
            current_operation,
            op_idx,
            owner_kind,
            item_ui_key,
            operation_ui_key,
            command_group,
            cfg,
            command_code,
            operation_index=operation_index,
            is_first=is_first,
            is_last=is_last,
            action_label=action_label,
        )
        return

    button_results = _render_suite_command_card(
        current_operation,
        key_prefix=f"suite_editor_command_{item_ui_key}_{operation_ui_key}",
        action_specs=[
            {
                "name": "up",
                "key": f"suite_editor_command_up_{item_ui_key}_{operation_ui_key}",
                "icon": ":material/arrow_upward:",
                "help": f"Move {action_label} up",
                "disabled": is_first,
            },
            {
                "name": "down",
                "key": f"suite_editor_command_down_{item_ui_key}_{operation_ui_key}",
                "icon": ":material/arrow_downward:",
                "help": f"Move {action_label} down",
                "disabled": is_last,
            },
            {
                "name": "delete",
                "key": f"suite_editor_delete_command_{item_ui_key}_{operation_ui_key}",
                "icon": ":material/close:",
                "help": f"Delete {action_label}",
            },
        ],
    )
    if button_results.get("up"):
        original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
        if _move_operation_in_item(item, operation_index, operation_index - 1):
            try:
                _persist_current_draft(success_message="Commands reordered.", rerun=False)
            except Exception as exc:
                st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                _render_persist_error(exc)
                return
            st.rerun()
    if button_results.get("down"):
        original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
        if _move_operation_in_item(item, operation_index, operation_index + 1):
            try:
                _persist_current_draft(success_message="Commands reordered.", rerun=False)
            except Exception as exc:
                st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                _render_persist_error(exc)
                return
            st.rerun()
    if button_results.get("delete"):
        if _delete_operation_by_ui_key(item, operation_ui_key):
            st.session_state[SUITE_FEEDBACK_KEY] = "Command removed."
            _persist_changes()


def _render_api_command_inline(
    item: dict,
    operation: dict,
    op_idx: int,
    owner_kind: str,
    item_ui_key: str,
    operation_ui_key: str,
    command_group: str,
    cfg: dict,
    command_code: str,
    *,
    operation_index: int,
    is_first: bool,
    is_last: bool,
    action_label: str,
):
    is_write = command_code == "writeApi"
    description = _command_description_text(operation)
    expander_label = _build_suite_command_summary(operation)
    prefix = f"suite_inline_api_{item_ui_key}_{operation_ui_key}"

    wrapper_cols = st.columns([18, 1, 1, 1], gap="small", vertical_alignment="top")
    with wrapper_cols[0]:
        with st.expander(expander_label, expanded=_consume_inline_api_command_reopen(operation_ui_key)):
            st.text_input(
                "Command type",
                value="http / write-api" if is_write else "http / read-api",
                disabled=True,
                key=f"{prefix}_type_display",
            )

            if is_write:
                method_key = f"{prefix}_method"
                if method_key not in st.session_state:
                    current_method = str(cfg.get("method") or "POST").upper()
                    st.session_state[method_key] = (
                        current_method if current_method in HTTP_WRITE_METHOD_OPTIONS else "POST"
                    )

            url_key = f"{prefix}_url"
            if url_key not in st.session_state:
                st.session_state[url_key] = str(cfg.get("url") or "")

            if is_write:
                conf_cols = st.columns([2, 5], gap="small", vertical_alignment="center")
                with conf_cols[0]:
                    st.selectbox("Method", options=HTTP_WRITE_METHOD_OPTIONS, key=method_key)
                with conf_cols[1]:
                    st.text_input("URL", key=url_key, placeholder="https://api.example.com/orders")
            else:
                st.text_input("URL", key=url_key, placeholder="https://api.example.com/orders")

            params_state_key = f"{prefix}_params_rows"
            auth_state_key = f"{prefix}_auth"
            headers_state_key = f"{prefix}_headers_rows"
            form_body_state_key = f"{prefix}_form_body_rows"
            visible_runtime_constants = _resolve_available_http_form_runtime_constants(
                _safe_dict(st.session_state.get(TEST_SUITE_DRAFT_KEY) or {}),
                item,
                stop_before_index=op_idx,
            )

            ensure_kv_editor_state(params_state_key, cfg.get("queryParams") or {})
            initialize_auth_editor_state(auth_state_key, cfg.get("authorization") or {})
            ensure_kv_editor_state(headers_state_key, cfg.get("headers") or {})
            ensure_guided_kv_state(
                form_body_state_key,
                cfg.get("body") if str(cfg.get("bodyType") or "").strip() == "formUrlEncoded" else {},
            )
            if is_write:
                body_type_key = f"{prefix}_body_type"
                body_key = f"{prefix}_body"
                if body_type_key not in st.session_state:
                    st.session_state[body_type_key] = str(cfg.get("bodyType") or "json")
                if body_key not in st.session_state:
                    body_val = cfg.get("body")
                    if isinstance(body_val, (dict, list)):
                        st.session_state[body_key] = json.dumps(body_val, indent=2, ensure_ascii=True)
                    else:
                        st.session_state[body_key] = str(body_val or "")
            timeout_key = f"{prefix}_timeout"
            result_target_key = f"{prefix}_result_target"
            if timeout_key not in st.session_state:
                st.session_state[timeout_key] = max(_safe_int(cfg.get("timeoutSeconds"), 30), 1)
            if result_target_key not in st.session_state:
                st.session_state[result_target_key] = _api_result_target_label(cfg)

            tab_options = ["Params", "Auth", "Headers"]
            if is_write:
                tab_options.append("Body")
            tab_options.append("Response")
            selected_tab = _select_persisted_tab(
                tab_options,
                f"{prefix}_selected_tab",
                default="Params",
            )

            if selected_tab == "Params":
                render_kv_rows_container(
                    editor_state_key=params_state_key,
                    key_prefix=f"{params_state_key}_row",
                    use_container=False,
                )
            elif selected_tab == "Auth":
                render_auth_editor(auth_state_key)
            elif selected_tab == "Headers":
                render_kv_rows_container(
                    editor_state_key=headers_state_key,
                    key_prefix=f"{headers_state_key}_row",
                    use_container=False,
                )

            if selected_tab == "Body" and is_write:
                st.selectbox("Body type", options=HTTP_BODY_TYPE_OPTIONS, key=body_type_key)
                current_body_type = str(st.session_state.get(body_type_key) or "json").strip()
                if current_body_type == "formUrlEncoded":
                    render_guided_kv_rows_container(
                        editor_state_key=form_body_state_key,
                        key_prefix=f"{form_body_state_key}_row",
                        use_container=False,
                        available_constants=visible_runtime_constants,
                        allowed_modes=FORM_URLENCODED_ALLOWED_MODES,
                        show_runtime_field_path=True,
                    )
                else:
                    st.text_area("Body", key=body_key, height=180)

            if selected_tab == "Response":
                st.number_input("Timeout seconds", min_value=1, key=timeout_key)
                st.text_input(
                    "Result target",
                    key=result_target_key,
                    placeholder="apiResult",
                )

            save_cols = st.columns([4, 2, 2], gap="small", vertical_alignment="center")
            with save_cols[1]:
                if st.button(
                    "Save",
                    key=f"{prefix}_save",
                    icon=":material/save:",
                    use_container_width=True,
                ):
                    _mark_inline_api_command_for_reopen(operation_ui_key)
                    url = str(st.session_state.get(url_key) or "").strip()
                    if not url:
                        st.error("Il campo URL e' obbligatorio.")
                        return

                    query_params, params_error = rows_to_dict(
                        st.session_state.get(params_state_key, []),
                        "Params",
                    )
                    if params_error:
                        st.error(params_error)
                        return
                    authorization, auth_error = collect_auth_editor_value(auth_state_key)
                    if auth_error:
                        st.error(auth_error)
                        return
                    headers, headers_error = rows_to_dict(
                        st.session_state.get(headers_state_key, []),
                        "Headers",
                    )
                    if headers_error:
                        st.error(headers_error)
                        return

                    timeout_seconds = _safe_int(st.session_state.get(timeout_key), 30)
                    result_target = _normalize_api_result_target_input(
                        st.session_state.get(result_target_key),
                    )

                    if is_write:
                        method = str(
                            st.session_state.get(f"{prefix}_method") or "POST"
                        ).strip().upper()
                        body_type = str(
                            st.session_state.get(f"{prefix}_body_type") or "json"
                        ).strip()
                        body_raw = st.session_state.get(f"{prefix}_body")
                        if body_type == "json":
                            body_payload, body_error = _parse_json_input(body_raw)
                            if body_error:
                                st.error(body_error)
                                return
                        elif body_type == "formUrlEncoded":
                            body_payload, body_error = collect_guided_kv_rows(
                                st.session_state.get(form_body_state_key) or [],
                                f"{form_body_state_key}_row",
                                "Body",
                                allowed_modes=FORM_URLENCODED_ALLOWED_MODES,
                                scalar_only=True,
                            )
                            if body_error:
                                st.error(body_error)
                                return
                        else:
                            body_payload = str(body_raw or "")
                        updated_cfg = {
                            "commandCode": "writeApi",
                            "commandType": "action",
                            "method": method,
                            "url": url,
                            "bodyType": body_type,
                            "timeoutSeconds": timeout_seconds or 30,
                        }
                        if body_payload is not None and body_payload != "":
                            updated_cfg["body"] = body_payload
                    else:
                        updated_cfg = {
                            "commandCode": "readApi",
                            "commandType": "action",
                            "url": url,
                            "timeoutSeconds": timeout_seconds or 30,
                        }

                    if query_params:
                        updated_cfg["queryParams"] = query_params
                    updated_cfg["authorization"] = authorization
                    if headers:
                        updated_cfg["headers"] = headers
                    if result_target:
                        updated_cfg["result_target"] = result_target

                    original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
                    operation["configuration_json"] = updated_cfg
                    st.session_state[SUITE_FEEDBACK_KEY] = "Command updated."
                    try:
                        _persist_current_draft(success_message="Command updated.", rerun=False)
                    except Exception as exc:
                        st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                        _render_persist_error(exc)
                        return
                    st.rerun()
            with save_cols[2]:
                if st.button(
                    "Delete",
                    key=f"{prefix}_delete",
                    icon=":material/delete:",
                    type="secondary",
                    use_container_width=True,
                ):
                    if _delete_operation_by_ui_key(item, operation_ui_key):
                        st.session_state[SUITE_FEEDBACK_KEY] = "Command removed."
                        _persist_changes()

    with wrapper_cols[1]:
        if st.button(
            "",
            key=f"suite_editor_command_up_{item_ui_key}_{operation_ui_key}",
            icon=":material/arrow_upward:",
            help=f"Move {action_label} up",
            type="tertiary",
            use_container_width=True,
            disabled=is_first,
        ):
            original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
            if _move_operation_in_item(item, operation_index, operation_index - 1):
                try:
                    _persist_current_draft(success_message="Commands reordered.", rerun=False)
                except Exception as exc:
                    st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                    _render_persist_error(exc)
                    return
                st.rerun()
    with wrapper_cols[2]:
        if st.button(
            "",
            key=f"suite_editor_command_down_{item_ui_key}_{operation_ui_key}",
            icon=":material/arrow_downward:",
            help=f"Move {action_label} down",
            type="tertiary",
            use_container_width=True,
            disabled=is_last,
        ):
            original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
            if _move_operation_in_item(item, operation_index, operation_index + 1):
                try:
                    _persist_current_draft(success_message="Commands reordered.", rerun=False)
                except Exception as exc:
                    st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                    _render_persist_error(exc)
                    return
                st.rerun()


def _render_section(section_title: str, summary: str):
    st.markdown(f"### {section_title}")
    if summary:
        st.caption(summary)


def _render_section_summary(summary: str):
    if summary:
        st.caption(summary)


def _render_source_card(
    source: dict,
    item: dict,
    *,
    perimeter_return_page: str,
    perimeter_return_label: str,
):
    source_code = str(source.get("sourceCode") or "-").strip() or "-"
    source_type = str(source.get("sourceType") or "").strip()
    preview_visible = _is_source_preview_visible(item, source)
    details = (
        _resolve_dataset_source_details(source)
        if source_type == "dataset"
        else _resolve_json_array_source_details(source)
    )
    resource_label = str(details.get("description") or "").strip()
    expander_label = (
        f"{source_code} - {resource_label} [{_source_type_label(source_type)}]"
        if resource_label and resource_label != source_code
        else f"{source_code} [{_source_type_label(source_type)}]"
    )

    with st.expander(expander_label, expanded=preview_visible):
        if source_type == "dataset":
            st.write(f"**Database:** {details.get('connection_label') or '-'}")
            st.write(f"**Schema:** {details.get('schema') or '-'}")
            st.write(f"**Table/View:** {details.get('object_label') or '-'}")
            action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
            with action_cols[0]:
                if st.button(
                    "Hide preview" if preview_visible else "Preview",
                    key=f"suite_editor_source_preview_btn_{_source_state_suffix(item.get('_ui_key'), source_code)}",
                    icon=":material/visibility_off:" if preview_visible else ":material/visibility:",
                    type="secondary",
                    use_container_width=True,
                ):
                    _toggle_source_preview(item, source)
                    st.rerun()
            with action_cols[1]:
                if st.button(
                    "Perimeter",
                    key=f"suite_editor_source_perimeter_btn_{_source_state_suffix(item.get('_ui_key'), source_code)}",
                    icon=":material/filter_alt:",
                    type="secondary",
                    use_container_width=True,
                ):
                    open_test_source_perimeter_editor(
                        item_ui_key=str(item.get("_ui_key") or ""),
                        source_code=source_code,
                        return_page=perimeter_return_page,
                        return_label=perimeter_return_label,
                    )
                    st.switch_page(DATASET_PERIMETER_EDITOR_PAGE_PATH)
                    st.rerun()
            with action_cols[2]:
                if st.button(
                    "Delete",
                    key=f"suite_editor_source_delete_btn_{_source_state_suffix(item.get('_ui_key'), source_code)}",
                    icon=":material/delete:",
                    type="secondary",
                    use_container_width=True,
                ):
                    original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
                    if _delete_source_by_code(item, source_code):
                        try:
                            _persist_current_draft(success_message="Source removed.", rerun=False)
                        except Exception as exc:
                            st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                            _render_persist_error(exc)
                            return
                        st.rerun()
            if preview_visible:
                _render_source_preview_content(source)
            return

        st.write(f"**Json Array:** {details.get('description') or '-'}")
        if str(details.get("code") or "").strip():
            st.write(f"**Code:** {details.get('code')}")
        st.write(f"**Items:** {details.get('items_count') or 0}")
        action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
        with action_cols[0]:
            if st.button(
                "Hide preview" if preview_visible else "Preview",
                key=f"suite_editor_json_array_preview_btn_{_source_state_suffix(item.get('_ui_key'), source_code)}",
                icon=":material/visibility_off:" if preview_visible else ":material/visibility:",
                type="secondary",
                use_container_width=True,
            ):
                _toggle_source_preview(item, source)
                st.rerun()
        with action_cols[1]:
            if st.button(
                "Delete",
                key=f"suite_editor_json_array_delete_btn_{_source_state_suffix(item.get('_ui_key'), source_code)}",
                icon=":material/delete:",
                type="secondary",
                use_container_width=True,
            ):
                original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
                if _delete_source_by_code(item, source_code):
                    try:
                        _persist_current_draft(success_message="Source removed.", rerun=False)
                    except Exception as exc:
                        st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                        _render_persist_error(exc)
                        return
                    st.rerun()
        if preview_visible:
            _render_source_preview_content(source)


def _render_item_sources_summary(
    item: dict | None,
    *,
    perimeter_return_page: str,
    perimeter_return_label: str,
):
    sources = _source_list(item)
    if not sources:
        st.caption("No data source configured.")
        return
    for source in sources:
        _render_source_card(
            source,
            item or {},
            perimeter_return_page=perimeter_return_page,
            perimeter_return_label=perimeter_return_label,
        )


def _render_item_sources_compact_summary(item: dict | None):
    st.markdown("**Data Sources**")
    sources = _source_list(item)
    if not sources:
        st.caption("No data source configured.")
        return
    for source in sources:
        source_type = str(source.get("sourceType") or "").strip()
        details = (
            _resolve_dataset_source_details(source)
            if source_type == "dataset"
            else _resolve_json_array_source_details(source)
        )
        resource_label = str(details.get("description") or "").strip() or "-"
        st.caption(f"{_source_type_label(source_type)}: {resource_label}")


def _render_advanced_hook_datasources_section(hook: dict | None, hook_phase: str) -> None:
    _render_item_sources_summary(
        hook,
        perimeter_return_page=ADVANCED_SUITE_EDITOR_PAGE_PATH,
        perimeter_return_label="Back to advanced settings",
    )

    st.divider()

    add_cols = st.columns([3, 1, 3], gap="small", vertical_alignment="center")
    with add_cols[1]:
        if st.button(
            "+ Source",
            key=f"suite_editor_add_source_{hook_phase}_{str((hook or {}).get('_ui_key') or hook_phase)}",
            icon=":material/add:",
            use_container_width=True,
        ):
            _open_add_source_dialog_for_item(str((hook or {}).get("_ui_key") or ""))
            st.rerun()


def _render_advanced_hook_add_command_popover(draft: dict, hook_phase: str, hook: dict | None) -> None:
    hook_ui_key = str((hook or {}).get("_ui_key") or "").strip()
    if not hook_ui_key:
        return

    popover = getattr(st, "popover", None)
    if callable(popover):
        container = popover("+ Add command")
    else:
        expander = getattr(st, "expander", None)
        if callable(expander):
            container = expander("+ Add command")
        else:
            container = st.container(border=True)
            st.caption("Add command")

    with container:
        if st.button(
            "+ Variable",
            key=f"suite_editor_add_context_command_{hook_phase}_{hook_ui_key}",
            icon=":material/add:",
            type="tertiary",
            use_container_width=True,
        ):
            _open_hook_command_dialog_for_hook(draft, hook_phase, "context")
            st.rerun()
        if st.button(
            "+ Action",
            key=f"suite_editor_add_action_command_{hook_phase}_{hook_ui_key}",
            icon=":material/add:",
            type="tertiary",
            use_container_width=True,
        ):
            _open_hook_command_dialog_for_hook(draft, hook_phase, "action")
            st.rerun()


def _render_advanced_hook_command_list_card(
    hook: dict,
    operation: dict,
    operation_ui_key: str,
    *,
    hook_phase: str,
    is_selected: bool,
) -> None:
    select_label = _strip_command_markdown(_build_advanced_hook_command_list_label(operation)) or "Command"

    with st.container():
        row_cols = st.columns([7, 1], gap="small", vertical_alignment="center")
        with row_cols[0]:
            if st.button(
                select_label,
                key=f"advanced_hook_select_command_{hook_phase}_{operation_ui_key}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
            ):
                _set_advanced_hook_selected_command(hook_phase, operation_ui_key)
                st.rerun()
        with row_cols[1]:
            if st.button(
                "",
                key=f"advanced_hook_reorder_command_{hook_phase}_{operation_ui_key}",
                icon=":material/unfold_more:",
                help="Reorder commands",
                type="tertiary",
                use_container_width=True,
            ):
                _open_reorder_command_dialog_for_item(hook)
                st.rerun()


def _render_advanced_hook_generic_command_editor(
    current_operation: dict,
    operation_index: int,
    hook_phase: str,
) -> dict[str, object]:
    key_prefix = f"advanced_hook_generic_command_{str(hook_phase or '').replace('-', '_')}"
    description_key = _command_form_key(key_prefix, operation_index, "description")
    cfg_key = _command_form_key(key_prefix, operation_index, "cfg")
    if description_key not in st.session_state:
        st.session_state[description_key] = str(current_operation.get("description") or "")
    if cfg_key not in st.session_state:
        st.session_state[cfg_key] = json.dumps(
            _safe_dict(current_operation.get("configuration_json") or {}),
            ensure_ascii=True,
            indent=2,
        )

    st.text_area(
        "Configuration JSON",
        key=cfg_key,
        height=240,
        help="Modifica i parametri del command come oggetto JSON.",
    )
    return {
        "editor_kind": "generic",
        "key_prefix": key_prefix,
        "form_nonce": operation_index,
        "description_key": description_key,
        "cfg_key": cfg_key,
    }


def _render_advanced_hook_typed_command_editor(
    draft: dict,
    item: dict,
    current_operation: dict,
    operation_index: int,
    command_group: str,
    hook_phase: str,
) -> dict[str, object]:
    load_test_editor_context(force=False)
    load_database_connections(force=False)
    json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = _safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))
    key_prefix = f"advanced_hook_command_{str(hook_phase or '').replace('-', '_')}"
    default_context = _default_context_for_item(item)

    _initialize_hook_command_form(
        operation_index,
        current_operation,
        brokers,
        default_context=default_context,
        key_prefix=key_prefix,
    )
    command_code = _render_hook_command_form(
        operation_index,
        command_group,
        json_arrays,
        datasources,
        brokers,
        connections,
        draft,
        item,
        stop_before_index=operation_index,
        default_context=default_context,
        key_prefix=key_prefix,
    )
    return {
        "editor_kind": "typed",
        "key_prefix": key_prefix,
        "form_nonce": operation_index,
        "command_group": command_group,
        "command_code": command_code,
    }


def _render_advanced_hook_api_command_editor(
    item: dict,
    current_operation: dict,
    operation_ui_key: str,
) -> dict[str, object]:
    cfg = _safe_dict(current_operation.get("configuration_json") or {})
    is_write = _normalize_command_code(cfg) == "writeApi"
    prefix = f"advanced_hook_api_command_{operation_ui_key}"

    method_key = f"{prefix}_method"
    url_key = f"{prefix}_url"
    params_state_key = f"{prefix}_params_rows"
    auth_state_key = f"{prefix}_auth"
    headers_state_key = f"{prefix}_headers_rows"
    form_body_state_key = f"{prefix}_form_body_rows"
    body_type_key = f"{prefix}_body_type"
    body_key = f"{prefix}_body"
    timeout_key = f"{prefix}_timeout"
    result_target_key = f"{prefix}_result_target"

    if is_write and method_key not in st.session_state:
        current_method = str(cfg.get("method") or "POST").upper()
        st.session_state[method_key] = (
            current_method if current_method in HTTP_WRITE_METHOD_OPTIONS else "POST"
        )
    if url_key not in st.session_state:
        st.session_state[url_key] = str(cfg.get("url") or "")
    ensure_kv_editor_state(params_state_key, cfg.get("queryParams") or {})
    initialize_auth_editor_state(auth_state_key, cfg.get("authorization") or {})
    ensure_kv_editor_state(headers_state_key, cfg.get("headers") or {})
    visible_runtime_constants = _resolve_available_http_form_runtime_constants(
        _safe_dict(st.session_state.get(TEST_SUITE_DRAFT_KEY) or {}),
        item,
        stop_before_index=_find_operation_index_by_ui_key(item, operation_ui_key),
    )
    ensure_guided_kv_state(
        form_body_state_key,
        cfg.get("body") if str(cfg.get("bodyType") or "").strip() == "formUrlEncoded" else {},
    )
    if body_type_key not in st.session_state:
        st.session_state[body_type_key] = str(cfg.get("bodyType") or "json")
    if body_key not in st.session_state:
        body_val = cfg.get("body")
        if isinstance(body_val, (dict, list)):
            st.session_state[body_key] = json.dumps(body_val, indent=2, ensure_ascii=True)
        else:
            st.session_state[body_key] = str(body_val or "")
    if timeout_key not in st.session_state:
        st.session_state[timeout_key] = max(_safe_int(cfg.get("timeoutSeconds"), 30), 1)
    if result_target_key not in st.session_state:
        st.session_state[result_target_key] = _api_result_target_label(cfg)

    tab_options = ["Params", "Auth", "Headers"]
    if is_write:
        tab_options.append("Body")
    tab_options.append("Response")
    selected_tab = _select_persisted_tab(
        tab_options,
        _advanced_hook_api_tab_state_key(operation_ui_key),
        default="Params",
    )

    if is_write:
        conf_cols = st.columns([2, 5], gap="small", vertical_alignment="center")
        with conf_cols[0]:
            st.selectbox("Method", options=HTTP_WRITE_METHOD_OPTIONS, key=method_key)
        with conf_cols[1]:
            st.text_input("URL", key=url_key, placeholder="https://api.example.com/orders")
    else:
        st.text_input("URL", key=url_key, placeholder="https://api.example.com/orders")

    if selected_tab == "Params":
        render_kv_rows_container(
            editor_state_key=params_state_key,
            key_prefix=f"{params_state_key}_row",
            use_container=False,
        )
    elif selected_tab == "Auth":
        render_auth_editor(auth_state_key)
    elif selected_tab == "Headers":
        render_kv_rows_container(
            editor_state_key=headers_state_key,
            key_prefix=f"{headers_state_key}_row",
            use_container=False,
        )
    elif selected_tab == "Body" and is_write:
        st.selectbox("Body type", options=HTTP_BODY_TYPE_OPTIONS, key=body_type_key)
        current_body_type = str(st.session_state.get(body_type_key) or "json").strip()
        if current_body_type == "formUrlEncoded":
            render_guided_kv_rows_container(
                editor_state_key=form_body_state_key,
                key_prefix=f"{form_body_state_key}_row",
                use_container=False,
                available_constants=visible_runtime_constants,
                allowed_modes=FORM_URLENCODED_ALLOWED_MODES,
                show_runtime_field_path=True,
            )
        else:
            st.text_area("Body", key=body_key, height=180)
    elif selected_tab == "Response":
        st.number_input("Timeout seconds", min_value=1, key=timeout_key)
        st.text_input(
            "Result target",
            key=result_target_key,
            placeholder="apiResult",
        )

    return {
        "editor_kind": "api",
        "prefix": prefix,
        "is_write": is_write,
        "url_key": url_key,
        "params_state_key": params_state_key,
        "auth_state_key": auth_state_key,
        "headers_state_key": headers_state_key,
        "form_body_state_key": form_body_state_key,
        "body_type_key": body_type_key,
        "body_key": body_key,
        "timeout_key": timeout_key,
        "result_target_key": result_target_key,
        "method_key": method_key,
    }


def _save_advanced_hook_command(
    item: dict,
    current_operation: dict,
    operation_index: int,
    operation_ui_key: str,
    editor_state: dict[str, object],
) -> bool:
    editor_kind = str(editor_state.get("editor_kind") or "").strip()

    if editor_kind == "typed":
        form_nonce = int(editor_state.get("form_nonce") or 0)
        key_prefix = str(editor_state.get("key_prefix") or "")
        command_group = str(editor_state.get("command_group") or "").strip()
        command_code = str(editor_state.get("command_code") or "").strip()
        updated_operation, validation_error = _build_hook_command_draft_with_prefix(
            form_nonce,
            command_code,
            key_prefix=key_prefix,
        )
        if validation_error:
            st.error(validation_error)
            return False
        original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
        _update_operation_in_item(item, operation_index, updated_operation or {})
        try:
            _persist_current_draft(
                success_message=_command_group_updated_feedback(command_group),
                rerun=False,
            )
        except Exception as exc:
            st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
            _render_persist_error(exc)
            return False
        _clear_command_form_state(key_prefix, form_nonce)
        return True

    if editor_kind == "generic":
        cfg_key = str(editor_state.get("cfg_key") or "")
        description_key = str(editor_state.get("description_key") or "")
        form_nonce = int(editor_state.get("form_nonce") or 0)
        key_prefix = str(editor_state.get("key_prefix") or "")
        try:
            configuration_json = json.loads(str(st.session_state.get(cfg_key) or "").strip() or "{}")
        except json.JSONDecodeError as exc:
            st.error(f"Configuration JSON non valido: {str(exc)}")
            return False
        if not isinstance(configuration_json, dict):
            st.error("Configuration JSON deve essere un oggetto JSON.")
            return False
        original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
        _update_operation_in_item(
            item,
            operation_index,
            {
                "description": str(st.session_state.get(description_key) or "").strip(),
                "operation_type": _normalize_command_code(configuration_json)
                or str(current_operation.get("operation_type") or ""),
                "configuration_json": configuration_json,
            },
        )
        try:
            _persist_current_draft(success_message="Command updated.", rerun=False)
        except Exception as exc:
            st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
            _render_persist_error(exc)
            return False
        _clear_command_form_state(key_prefix, form_nonce)
        return True

    if editor_kind == "api":
        prefix = str(editor_state.get("prefix") or "")
        url_key = str(editor_state.get("url_key") or "")
        params_rows = st.session_state.get(str(editor_state.get("params_state_key") or ""), [])
        auth_state_key = str(editor_state.get("auth_state_key") or "")
        headers_rows = st.session_state.get(str(editor_state.get("headers_state_key") or ""), [])
        form_body_rows = st.session_state.get(str(editor_state.get("form_body_state_key") or ""), [])
        is_write = bool(editor_state.get("is_write"))
        timeout_key = str(editor_state.get("timeout_key") or "")
        result_target_key = str(editor_state.get("result_target_key") or "")
        url = str(st.session_state.get(url_key) or "").strip()
        if not url:
            st.error("Il campo URL e' obbligatorio.")
            return False

        query_params, params_error = rows_to_dict(params_rows, "Params")
        if params_error:
            st.error(params_error)
            return False
        authorization, auth_error = collect_auth_editor_value(auth_state_key)
        if auth_error:
            st.error(auth_error)
            return False
        headers, headers_error = rows_to_dict(headers_rows, "Headers")
        if headers_error:
            st.error(headers_error)
            return False

        timeout_seconds = _safe_int(st.session_state.get(timeout_key), 30)
        result_target = _normalize_api_result_target_input(st.session_state.get(result_target_key))

        if is_write:
            method = str(st.session_state.get(str(editor_state.get("method_key") or "")) or "POST").strip().upper()
            body_type = str(st.session_state.get(str(editor_state.get("body_type_key") or "")) or "json").strip()
            body_raw = st.session_state.get(str(editor_state.get("body_key") or ""))
            if body_type == "json":
                body_payload, body_error = _parse_json_input(body_raw)
                if body_error:
                    st.error(body_error)
                    return False
            elif body_type == "formUrlEncoded":
                body_payload, body_error = collect_guided_kv_rows(
                    form_body_rows if isinstance(form_body_rows, list) else [],
                    f"{str(editor_state.get('form_body_state_key') or '')}_row",
                    "Body",
                    allowed_modes=FORM_URLENCODED_ALLOWED_MODES,
                    scalar_only=True,
                )
                if body_error:
                    st.error(body_error)
                    return False
            else:
                body_payload = str(body_raw or "")
            updated_cfg = {
                "commandCode": "writeApi",
                "commandType": "action",
                "method": method,
                "url": url,
                "bodyType": body_type,
                "timeoutSeconds": timeout_seconds or 30,
            }
            if body_payload is not None and body_payload != "":
                updated_cfg["body"] = body_payload
        else:
            updated_cfg = {
                "commandCode": "readApi",
                "commandType": "action",
                "url": url,
                "timeoutSeconds": timeout_seconds or 30,
            }

        if query_params:
            updated_cfg["queryParams"] = query_params
        updated_cfg["authorization"] = authorization
        if headers:
            updated_cfg["headers"] = headers
        if result_target:
            updated_cfg["result_target"] = result_target

        original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
        _update_operation_in_item(
            item,
            operation_index,
            {
                "description": str(current_operation.get("description") or "").strip(),
                "operation_type": str(current_operation.get("operation_type") or updated_cfg["commandCode"]),
                "configuration_json": updated_cfg,
            },
        )
        _mark_inline_api_command_for_reopen(operation_ui_key)
        try:
            _persist_current_draft(success_message="Command updated.", rerun=False)
        except Exception as exc:
            st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
            _render_persist_error(exc)
            return False
        _clear_state_prefix(prefix)
        return True

    st.error("Unsupported command editor.")
    return False


def _reset_advanced_hook_command(editor_state: dict[str, object]) -> None:
    editor_kind = str(editor_state.get("editor_kind") or "").strip()
    if editor_kind == "api":
        _clear_state_prefix(str(editor_state.get("prefix") or ""))
        return
    _clear_command_form_state(
        str(editor_state.get("key_prefix") or ""),
        int(editor_state.get("form_nonce") or 0),
    )


def _render_selected_advanced_hook_command(
    hook: dict,
    draft: dict,
    hook_phase: str,
    operation_ui_key: str,
) -> None:
    operation_index, current_operation = _find_operation_by_ui_key(hook, operation_ui_key)
    if not isinstance(current_operation, dict):
        _set_advanced_hook_selected_command(hook_phase, "")
        st.info("Select a command from the list.")
        return

    command_group = _resolve_hook_command_group(current_operation.get("configuration_json"))
    command_code = _normalize_command_code(current_operation.get("configuration_json"))

    with st.container(border=True):
        st.markdown(_build_suite_command_markdown(current_operation))
        st.divider()

        if command_code in {"readApi", "writeApi"}:
            editor_state = _render_advanced_hook_api_command_editor(
                hook,
                current_operation,
                operation_ui_key,
            )
        elif command_group and command_group != "fallback-json":
            editor_state = _render_advanced_hook_typed_command_editor(
                draft,
                hook,
                current_operation,
                operation_index,
                command_group,
                hook_phase,
            )
        else:
            editor_state = _render_advanced_hook_generic_command_editor(
                current_operation,
                operation_index,
                hook_phase,
            )

        st.divider()
        action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
        with action_cols[0]:
            if st.button(
                "Save",
                key=f"advanced_hook_command_save_{hook_phase}_{operation_ui_key}",
                icon=":material/save:",
                use_container_width=True,
            ):
                if _save_advanced_hook_command(
                    hook,
                    current_operation,
                    operation_index,
                    operation_ui_key,
                    editor_state,
                ):
                    st.rerun()
        with action_cols[1]:
            if st.button(
                "Reset",
                key=f"advanced_hook_command_reset_{hook_phase}_{operation_ui_key}",
                icon=":material/refresh:",
                use_container_width=True,
            ):
                _reset_advanced_hook_command(editor_state)
                st.rerun()
        with action_cols[2]:
            if st.button(
                "Delete",
                key=f"advanced_hook_command_delete_{hook_phase}_{operation_ui_key}",
                icon=":material/delete:",
                type="secondary",
                use_container_width=True,
            ):
                original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
                _reassign_advanced_hook_selected_command_after_delete(hook, hook_phase, operation_ui_key)
                try:
                    _persist_current_draft(success_message="Command removed.", rerun=False)
                except Exception as exc:
                    st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                    _render_persist_error(exc)
                    return
                st.rerun()


def _render_advanced_hook_commands_section(draft: dict, hook: dict, hook_phase: str) -> None:
    selected_command_ui_key = _resolve_advanced_hook_selected_command(hook, hook_phase)
    operation_entries = _advanced_hook_operation_entries(hook)
    list_col, detail_col = st.columns([3, 8], gap="medium", vertical_alignment="top")

    with list_col:
        with st.container(border=True):
            if operation_entries:
                for _, operation, operation_ui_key in operation_entries:
                    _render_advanced_hook_command_list_card(
                        hook,
                        operation,
                        operation_ui_key,
                        hook_phase=hook_phase,
                        is_selected=selected_command_ui_key == operation_ui_key,
                    )
            else:
                st.caption("Nessuna operation configurata.")

        _render_advanced_hook_add_command_popover(draft, hook_phase, hook)

    with detail_col:
        if not selected_command_ui_key:
            st.info("Select a command from the list.")
            return
        _render_selected_advanced_hook_command(hook, draft, hook_phase, selected_command_ui_key)


def _render_advanced_hook_heading(hook_label: str) -> None:
    if callable(getattr(st, "subheader", None)):
        st.subheader(hook_label)
        return
    if callable(getattr(st, "write", None)):
        st.write(hook_label)


def _render_hook_section(draft: dict, hook_phase: str, hook_label: str, execution_state: dict):
    hook = _ensure_hook_item(draft, hook_phase)
    _render_advanced_hook_heading(hook_label)
    hook_description = ADVANCED_HOOK_DESCRIPTION_BY_PHASE.get(str(hook_phase or "").strip().lower())
    if hook_description:
        st.caption(hook_description)
    selected_section = _select_persisted_tab(
        [ADVANCED_HOOK_SECTION_COMMANDS_TAB, ADVANCED_HOOK_SECTION_DATASOURCES_TAB],
        _advanced_hook_section_state_key(hook_phase),
        default=ADVANCED_HOOK_SECTION_COMMANDS_TAB,
    )
    if selected_section == ADVANCED_HOOK_SECTION_DATASOURCES_TAB:
        _render_advanced_hook_datasources_section(hook, hook_phase)
        return
    _render_advanced_hook_commands_section(draft, hook or {}, hook_phase)


def _ensure_test_item(test: dict, index: int) -> dict:
    test["_ui_key"] = str(test.get("_ui_key") or new_ui_key())
    if not isinstance(test.get("operations"), list):
        test["operations"] = []
    if not str(test.get("kind") or "").strip():
        test["kind"] = "test"
    return test


def _find_test_index_by_ui_key(draft: dict, test_ui_key: str) -> int:
    tests = draft.get("tests") or []
    if not isinstance(tests, list):
        return -1
    for index, test in enumerate(tests):
        if isinstance(test, dict) and str(test.get("_ui_key") or "") == str(test_ui_key or ""):
            return index
    return -1


def _find_test_by_ui_key(draft: dict, test_ui_key: str) -> dict | None:
    test_index = _find_test_index_by_ui_key(draft, test_ui_key)
    tests = draft.get("tests") or []
    if test_index < 0 or not isinstance(tests, list):
        return None
    test_item = tests[test_index]
    return test_item if isinstance(test_item, dict) else None


def _delete_test_by_ui_key(draft: dict, test_ui_key: str):
    test_index = _find_test_index_by_ui_key(draft, test_ui_key)
    tests = draft.get("tests") or []
    if not isinstance(tests, list) or test_index < 0 or test_index >= len(tests):
        st.session_state[SUITE_FEEDBACK_KEY] = "Test non trovato."
        st.rerun()
        return
    tests.pop(test_index)
    st.session_state[SUITE_FEEDBACK_KEY] = "Test rimosso."
    _persist_changes()


def _item_command_section_label(item: dict | None) -> str:
    if not isinstance(item, dict):
        return "Commands"
    if str(item.get("kind") or "").strip().lower() != "hook":
        description = str(item.get("description") or "").strip()
        return description or "Test commands"
    hook_phase = str(item.get("hook_phase") or "").strip().lower()
    hook_labels = {
        "before-all": "Before suite",
        "before-each": "Before each test",
        "after-each": "After each test",
        "after-all": "After suite",
    }
    return hook_labels.get(hook_phase, "Hook commands")


def _test_label(test: dict, index: int) -> str:
    description = str(test.get("description") or "").strip()
    test_id = str(test.get("id") or "").strip()
    return description or test_id or f"Test {index}"


def _render_test_command_summaries(test: dict):
    commands = test.get("operations") or []
    if commands:
        for op_idx, operation in enumerate(commands, start=1):
            markdowm_label = f"**{op_idx}. {_command_action_label(operation)}**"
            description = _command_description_text(operation)
            if description:
                markdowm_label += f" // {description}"
            st.markdown(markdowm_label)
    else:
        st.caption("Nessun command configurato.")


def _render_inline_generic_test_command_editor(item: dict, operation: dict, operation_index: int, form_nonce: int):
    description_key = _command_form_key("test_editor_inline_generic_command", form_nonce, "description")
    cfg_key = _command_form_key("test_editor_inline_generic_command", form_nonce, "cfg")
    if description_key not in st.session_state:
        st.session_state[description_key] = str(operation.get("description") or "")
    if cfg_key not in st.session_state:
        st.session_state[cfg_key] = json.dumps(
            _safe_dict(operation.get("configuration_json") or {}),
            ensure_ascii=True,
            indent=2,
        )

    st.text_area(
        "Configuration JSON",
        key=cfg_key,
        height=240,
        help="Modifica i parametri del command come oggetto JSON.",
    )
    st.text_input("Comment", key=description_key)

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"test_editor_inline_generic_command_save_{operation.get('_ui_key')}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
            description = str(st.session_state.get(description_key) or "").strip()
            try:
                configuration_json = json.loads(str(st.session_state.get(cfg_key) or "").strip() or "{}")
            except json.JSONDecodeError as exc:
                st.error(f"Configuration JSON non valido: {str(exc)}")
                return
            if not isinstance(configuration_json, dict):
                st.error("Configuration JSON deve essere un oggetto JSON.")
                return
            _update_operation_in_item(
                item,
                operation_index,
                {
                    "description": description,
                    "operation_type": _normalize_command_code(configuration_json)
                    or str(operation.get("operation_type") or ""),
                    "configuration_json": configuration_json,
                },
            )
            try:
                _persist_current_draft(success_message="Command updated.", rerun=False)
            except Exception as exc:
                st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                _render_persist_error(exc)
                return
            _close_inline_test_command_editor()
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"test_editor_inline_generic_command_cancel_{operation.get('_ui_key')}",
            use_container_width=True,
        ):
            _close_inline_test_command_editor()
            st.rerun()


def _render_inline_typed_test_command_editor(
    draft: dict,
    item: dict,
    operation: dict,
    operation_index: int,
    command_group: str,
    form_nonce: int,
):
    load_test_editor_context(force=False)
    load_database_connections(force=False)
    json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = _safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))

    st.markdown(f"**{_command_group_intro_label(command_group, mode='edit')}**")
    _initialize_test_command_form(
        form_nonce,
        operation,
        json_arrays,
        brokers,
        key_prefix="test_editor_inline_test_command",
    )
    command_code = _render_test_command_form(
        form_nonce,
        command_group,
        json_arrays,
        datasources,
        brokers,
        connections,
        draft,
        item,
        stop_before_index=operation_index,
        key_prefix="test_editor_inline_test_command",
    )

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"test_editor_inline_test_command_save_{operation.get('_ui_key')}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
            updated_operation, validation_error = _build_test_command_draft_with_prefix(
                form_nonce,
                command_code,
                key_prefix="test_editor_inline_test_command",
            )
            if validation_error:
                st.error(validation_error)
                return
            _update_operation_in_item(item, operation_index, updated_operation or {})
            try:
                _persist_current_draft(
                    success_message=_command_group_updated_feedback(command_group),
                    rerun=False,
                )
            except Exception as exc:
                st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                _render_persist_error(exc)
                return
            _close_inline_test_command_editor()
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"test_editor_inline_test_command_cancel_{operation.get('_ui_key')}",
            use_container_width=True,
        ):
            _close_inline_test_command_editor()
            st.rerun()


def _render_test_item(test: dict, index: int, execution_state: dict):
    current_test = _ensure_test_item(test, index)
    selected_test_position = _coerce_test_position(st.session_state.get(SELECTED_TEST_POSITION_KEY))
    is_selected_test = _test_position(current_test, index) == selected_test_position and selected_test_position > 0
    with st.expander(_test_label(current_test, index), expanded=is_selected_test):
        _render_item_sources_compact_summary(current_test)
        st.markdown("**Commands**")
        _render_test_command_summaries(current_test)
        action_cols = st.columns([20, 1, 1], gap="small", vertical_alignment="center")
        with action_cols[1]:
            if st.button(
                "",
                key=f"test_suite_open_test_editor_{current_test.get('_ui_key')}",
                icon=":material/edit:",
                type="tertiary",
                use_container_width=True,
            ):
                st.session_state[SELECTED_TEST_POSITION_KEY] = _test_position(current_test, index)
                st.switch_page(TEST_EDITOR_PAGE_PATH)
        with action_cols[2]:
            if st.button(
                "",
                key=f"test_suite_delete_test_{current_test.get('_ui_key')}",
                icon=":material/delete:",
                type="tertiary",
                use_container_width=True,
            ):
                draft = st.session_state.get(TEST_SUITE_DRAFT_KEY, {})
                if isinstance(draft, dict):
                    _delete_test_by_ui_key(draft, str(current_test.get("_ui_key") or ""))

def _render_generic_command_edit_dialog(item: dict, operation: dict, operation_index: int, dialog_nonce: int):
    description_key = _command_form_key("suite_generic_command_edit", dialog_nonce, "description")
    cfg_key = _command_form_key("suite_generic_command_edit", dialog_nonce, "cfg")
    if description_key not in st.session_state:
        st.session_state[description_key] = str(operation.get("description") or "")
    if cfg_key not in st.session_state:
        st.session_state[cfg_key] = json.dumps(_safe_dict(operation.get("configuration_json") or {}), ensure_ascii=True, indent=2)

    st.text_area("Configuration JSON", key=cfg_key, height=240, help="Modifica i parametri del command come oggetto JSON.")
    st.text_input("Comment", key=description_key)

    action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button("Save", key=f"suite_generic_command_edit_save_{dialog_nonce}", icon=":material/save:", type="secondary", use_container_width=True):
            original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
            description = str(st.session_state.get(description_key) or "").strip()
            try:
                configuration_json = json.loads(str(st.session_state.get(cfg_key) or "").strip() or "{}")
            except json.JSONDecodeError as exc:
                st.error(f"Configuration JSON non valido: {str(exc)}")
                return
            if not isinstance(configuration_json, dict):
                st.error("Configuration JSON deve essere un oggetto JSON.")
                return
            _update_operation_in_item(
                item,
                operation_index,
                {
                    "description": description,
                    "operation_type": _normalize_command_code(configuration_json) or str(operation.get("operation_type") or ""),
                    "configuration_json": configuration_json,
                },
            )
            try:
                _persist_current_draft(success_message="Command updated.", rerun=False)
            except Exception as exc:
                st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                _render_persist_error(exc)
                return
            _close_edit_command_dialog()
            st.rerun()
    with action_cols[1]:
        if st.button("Delete", key=f"suite_generic_command_edit_delete_{dialog_nonce}", icon=":material/delete:", type="secondary", use_container_width=True):
            operations = item.get("operations") or []
            if isinstance(operations, list) and 0 <= operation_index < len(operations):
                operations.pop(operation_index)
            _close_edit_command_dialog()
            st.session_state[SUITE_FEEDBACK_KEY] = "Command rimosso."
            _persist_changes()
    with action_cols[2]:
        if st.button("Cancel", key=f"suite_generic_command_edit_cancel_{dialog_nonce}", use_container_width=True):
            _close_edit_command_dialog()
            st.rerun()


@st.dialog("Reorder commands", width="large")
def _render_reorder_command_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(COMMAND_REORDER_DIALOG_NONCE_KEY, 0))
    item_ui_key = str(st.session_state.get(COMMAND_REORDER_DIALOG_TARGET_ITEM_UI_KEY) or "").strip()
    item = find_draft_test_by_ui_key(draft, item_ui_key)

    if not isinstance(item, dict):
        st.error("Target section not found.")
        if st.button(
            "Cancel",
            key=f"suite_reorder_command_missing_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_reorder_command_dialog()
            st.rerun()
        return

    if COMMAND_REORDER_DIALOG_OPERATIONS_KEY not in st.session_state:
        st.session_state[COMMAND_REORDER_DIALOG_OPERATIONS_KEY] = deepcopy(_operation_list(item))

    operations = _reorder_dialog_operations()
    st.caption(f"Section: {_item_command_section_label(item)}")

    if not operations:
        st.info("No commands available in this section.")
    else:
        for index, operation in enumerate(operations):
            action_label = _command_action_label(operation)
            row_cols = st.columns([14, 1, 1], gap="small", vertical_alignment="center")
            with row_cols[0]:
                _render_suite_command_card(
                    operation,
                    key_prefix=f"suite_reorder_preview_{dialog_nonce}_{index}",
                )
            with row_cols[1]:
                if st.button(
                    "",
                    key=f"suite_reorder_command_up_{dialog_nonce}_{index}",
                    icon=":material/arrow_drop_up:",
                    help=f"Move {action_label} up",
                    type="tertiary",
                    use_container_width=True,
                    disabled=index == 0,
                ):
                    _move_reorder_operation(index, index - 1)
                    st.rerun()
            with row_cols[2]:
                if st.button(
                    "",
                    key=f"suite_reorder_command_down_{dialog_nonce}_{index}",
                    icon=":material/arrow_drop_down:",
                    help=f"Move {action_label} down",
                    type="tertiary",
                    use_container_width=True,
                    disabled=index >= len(operations) - 1,
                ):
                    _move_reorder_operation(index, index + 1)
                    st.rerun()

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"suite_reorder_command_save_{dialog_nonce}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
            current_item = find_draft_test_by_ui_key(draft, item_ui_key)
            if not isinstance(current_item, dict):
                st.error("Target section not found.")
                return
            current_item["operations"] = _resequence_operations(_reorder_dialog_operations())
            try:
                _persist_current_draft(success_message="Commands reordered.", rerun=False)
            except Exception as exc:
                st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                st.error(_friendly_suite_validation_message(_extract_api_error_detail(exc)))
                return
            _close_reorder_command_dialog()
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"suite_reorder_command_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_reorder_command_dialog()
            st.rerun()


@st.dialog("Modify command", width="large")
def _render_edit_command_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(COMMAND_EDIT_DIALOG_NONCE_KEY, 0))
    item_ui_key = str(st.session_state.get(COMMAND_EDIT_DIALOG_TARGET_ITEM_UI_KEY) or "").strip()
    command_ui_key = str(st.session_state.get(COMMAND_EDIT_DIALOG_TARGET_COMMAND_UI_KEY) or "").strip()
    owner_kind = str(st.session_state.get(COMMAND_EDIT_DIALOG_OWNER_KIND_KEY) or "").strip().lower()
    command_group = str(st.session_state.get(COMMAND_EDIT_DIALOG_GROUP_KEY) or "").strip().lower()
    item = find_draft_test_by_ui_key(draft, item_ui_key)
    command_intro_label = _command_group_intro_label(command_group, mode="edit")
    primary_action_label = _command_group_primary_action_label(command_group, mode="edit")

    if not isinstance(item, dict):
        st.error("Elemento di destinazione non trovato.")
        if st.button("Cancel", key=f"suite_edit_command_missing_cancel_{dialog_nonce}", use_container_width=True):
            _close_edit_command_dialog()
            st.rerun()
        return

    operation_index, operation = _find_operation_by_ui_key(item, command_ui_key)
    if not isinstance(operation, dict):
        st.error(f"{_command_group_title(command_group)} not found.")
        if st.button("Cancel", key=f"suite_edit_command_missing_operation_cancel_{dialog_nonce}", use_container_width=True):
            _close_edit_command_dialog()
            st.rerun()
        return

    if owner_kind not in {"hook", "test"} or command_group == "fallback-json":
        _render_generic_command_edit_dialog(item, operation, operation_index, dialog_nonce)
        return

    load_test_editor_context(force=False)
    load_database_connections(force=False)
    json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = _safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))
    st.markdown(f"**{command_intro_label}**")

    if owner_kind == "hook":
        default_context = _default_context_for_item(item)
        _initialize_hook_command_form(
            dialog_nonce,
            operation,
            brokers,
            default_context=default_context,
            key_prefix="suite_edit_hook_command",
        )
        command_code = _render_hook_command_form(
            dialog_nonce,
            command_group,
            json_arrays,
            datasources,
            brokers,
            connections,
            draft,
            item,
            stop_before_index=operation_index,
            default_context=default_context,
            key_prefix="suite_edit_hook_command",
        )
    else:
        _initialize_test_command_form(
            dialog_nonce,
            operation,
            json_arrays,
            brokers,
            key_prefix="suite_edit_test_command",
        )
        command_code = _render_test_command_form(
            dialog_nonce,
            command_group,
            json_arrays,
            datasources,
            brokers,
            connections,
            draft,
            item,
            stop_before_index=operation_index,
            key_prefix="suite_edit_test_command",
        )

    action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(primary_action_label, key=f"suite_edit_command_save_{dialog_nonce}", icon=":material/save:", type="secondary", use_container_width=True):
            original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
            if owner_kind == "hook":
                updated_operation, validation_error = _build_hook_command_draft_with_prefix(
                    dialog_nonce,
                    command_code,
                    key_prefix="suite_edit_hook_command",
                )
            else:
                updated_operation, validation_error = _build_test_command_draft_with_prefix(
                    dialog_nonce,
                    command_code,
                    key_prefix="suite_edit_test_command",
                )
            if validation_error:
                st.error(validation_error)
                return
            _update_operation_in_item(item, operation_index, updated_operation or {})
            try:
                _persist_current_draft(
                    success_message=_command_group_updated_feedback(command_group),
                    rerun=False,
                )
            except Exception as exc:
                st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                _render_persist_error(exc)
                return
            _close_edit_command_dialog()
            st.rerun()
    with action_cols[1]:
        if st.button("Delete", key=f"suite_edit_command_delete_{dialog_nonce}", icon=":material/delete:", type="secondary", use_container_width=True):
            operations = item.get("operations") or []
            if isinstance(operations, list) and 0 <= operation_index < len(operations):
                operations.pop(operation_index)
            _close_edit_command_dialog()
            st.session_state[SUITE_FEEDBACK_KEY] = "Command rimosso."
            _persist_changes()
    with action_cols[2]:
        if st.button("Cancel", key=f"suite_edit_command_cancel_{dialog_nonce}", use_container_width=True):
            _close_edit_command_dialog()
            st.rerun()
