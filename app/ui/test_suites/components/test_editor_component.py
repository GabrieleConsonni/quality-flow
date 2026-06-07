import json
import re
from copy import deepcopy
from urllib.parse import urlsplit

import streamlit as st

from database_connections.services.data_loader_service import (
    DATABASE_CONNECTIONS_KEY,
    load_database_connections,
)
from elaborations_shared.services.data_loader_service import load_test_editor_context
from elaborations_shared.services.state_keys import (
    SUITE_FEEDBACK_KEY,
    TEST_EDITOR_BROKERS_KEY,
    TEST_EDITOR_DATABASE_DATASOURCES_KEY,
    TEST_EDITOR_JSON_ARRAYS_KEY,
)
from test_suites.components import suite_editor_component as shared
from test_suites.services.api_service import execute_test_by_id
from test_suites.services.execution_stream_service import register_execution_listener
from test_suites.services.state_keys import (
    SELECTED_TEST_SUITE_ID_KEY,
    TEST_SUITE_DRAFT_KEY,
    TEST_SUITE_LAST_EXECUTION_ID_KEY,
)

TEST_EDITOR_COMMAND_FORM_FIELDS = (
    "description",
    "command_type",
    "init_constant_name",
    "init_constant_context",
    "init_constant_source_type",
    "init_constant_value",
    "init_constant_json_array_id",
    "init_constant_dataset_id",
    "init_constant_broker_id",
    "init_constant_queue_id",
    "init_constant_retry",
    "init_constant_wait_time_seconds",
    "init_constant_max_messages",
    "read_api_url",
    "read_api_query_params",
    "read_api_headers",
    "read_api_timeout_seconds",
    "read_api_result_target",
    "write_api_method",
    "write_api_url",
    "write_api_query_params",
    "write_api_headers",
    "write_api_body_type",
    "write_api_body",
    "write_api_timeout_seconds",
    "write_api_result_target",
    "send_message_broker_id",
    "send_message_queue_id",
    "send_message_source",
    "send_message_template_enabled",
    "send_message_template_for_each",
    "send_message_template_fields",
    "send_message_template_constants_rows",
    "send_message_result_target",
    "save_table_name",
    "save_table_source",
    "save_table_result_target",
    "drop_table_name",
    "clean_table_name",
    "export_dataset_connection_id",
    "export_dataset_table_name",
    "export_dataset_source",
    "export_dataset_mode",
    "export_dataset_mapping_keys",
    "export_dataset_dataset_id",
    "export_dataset_dataset_description",
    "export_dataset_result_target",
    "drop_dataset_id",
    "clean_dataset_id",
    "assert_error_message",
    "assert_actual",
    "assert_expected_mode",
    "assert_expected",
    "assert_expected_variable",
    "assert_expected_json_array_id",
    "assert_compare_keys",
)
TEST_EDITOR_REOPEN_COMMAND_UI_KEY = "test_editor_reopen_command_ui_key"
TEST_EDITOR_SELECTED_COMMAND_UI_KEY = "test_editor_selected_command_ui_key"
TEST_EDITOR_SELECTED_COMMAND_ORDER_KEY = "test_editor_selected_command_order_key"
TEST_EDITOR_COMMENT_DIALOG_OPEN_KEY = "test_editor_comment_dialog_open_key"
TEST_EDITOR_COMMENT_DIALOG_NONCE_KEY = "test_editor_comment_dialog_nonce_key"
TEST_EDITOR_COMMENT_DIALOG_TARGET_ITEM_UI_KEY = "test_editor_comment_dialog_target_item_ui_key"
TEST_EDITOR_COMMENT_DIALOG_TARGET_COMMAND_UI_KEY = "test_editor_comment_dialog_target_command_ui_key"
TEST_EDITOR_API_VALUE_DIALOG_OPEN_KEY = "test_editor_api_value_dialog_open_key"
TEST_EDITOR_API_VALUE_DIALOG_NONCE_KEY = "test_editor_api_value_dialog_nonce_key"
TEST_EDITOR_API_VALUE_DIALOG_TARGET_ITEM_UI_KEY = "test_editor_api_value_dialog_target_item_ui_key"
TEST_EDITOR_API_VALUE_DIALOG_TARGET_COMMAND_UI_KEY = "test_editor_api_value_dialog_target_command_ui_key"
TEST_EDITOR_API_VALUE_DIALOG_TARGET_KIND_KEY = "test_editor_api_value_dialog_target_kind_key"
TEST_EDITOR_API_VALUE_DIALOG_TARGET_SECTION_KEY = "test_editor_api_value_dialog_target_section_key"
TEST_EDITOR_API_VALUE_DIALOG_TARGET_ROW_ID_KEY = "test_editor_api_value_dialog_target_row_id_key"
TEST_EDITOR_API_VALUE_DIALOG_TARGET_AUTH_FIELD_KEY = "test_editor_api_value_dialog_target_auth_field_key"

TEST_EDITOR_API_VALUE_MODE_LITERAL = "literal"
TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE = "runtimeValue"
TEST_EDITOR_API_VALUE_MODE_BUILT_IN = "builtIn"
TEST_EDITOR_API_VALUE_MODE_SOURCE_JSON_ARRAY = "sourceJsonArray"
TEST_EDITOR_API_VALUE_MODE_SOURCE_DATASET = "sourceDataset"
TEST_EDITOR_API_FIELD_PATH_SEGMENT_RE = re.compile(r"^(?:[A-Za-z0-9_-]+)?(?:\[\d+\])+$|^[A-Za-z0-9_-]+(?:\[\d+\])*$")

TEST_EDITOR_API_BUILT_IN_OPTIONS = ["now", "today"]
TEST_EDITOR_API_BUILT_IN_LABELS = {
    "now": "now - current datetime",
    "today": "today - current date",
}
TEST_EDITOR_API_VALUE_MODE_LABELS = {
    TEST_EDITOR_API_VALUE_MODE_LITERAL: "Literal inline",
    TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE: "Runtime value",
    TEST_EDITOR_API_VALUE_MODE_BUILT_IN: "Built-in runtime function",
    TEST_EDITOR_API_VALUE_MODE_SOURCE_JSON_ARRAY: "JsonArray datasource",
    TEST_EDITOR_API_VALUE_MODE_SOURCE_DATASET: "Dataset datasource",
}
TEST_EDITOR_API_AUTH_TYPE_OPTIONS = ["none", "basic", "bearer", "apiKey", "oauth2"]
TEST_EDITOR_API_AUTH_TYPE_LABELS = {
    "none": "No auth",
    "basic": "Basic auth",
    "bearer": "Bearer token",
    "apiKey": "API key",
    "oauth2": "OAuth 2",
}
TEST_EDITOR_API_AUTH_FIELDS = {
    "basic": ["username", "password"],
    "bearer": ["token"],
    "apiKey": ["username", "apiKey", "authEndpoint"],
    "oauth2": ["tokenUrl", "clientId", "clientSecret"],
}
TEST_EDITOR_API_AUTH_FIELD_LABELS = {
    "username": "Username",
    "password": "Password",
    "token": "Token",
    "apiKey": "API key",
    "authEndpoint": "Auth endpoint",
    "tokenUrl": "Token URL",
    "clientId": "Client ID",
    "clientSecret": "Client secret",
}
TEST_EDITOR_SECTION_TAB_KEY = "test_editor_section_tab"
TEST_EDITOR_SECTION_COMMANDS_TAB = ":material/deployed_code: Commands"
TEST_EDITOR_SECTION_DATASOURCES_TAB = ":material/data_array: Datasources"


def _consume_test_command_dialog_request() -> bool:
    is_open_requested = bool(st.session_state.get(shared.TEST_ADD_COMMAND_DIALOG_OPEN_KEY, False))
    if is_open_requested:
        st.session_state[shared.TEST_ADD_COMMAND_DIALOG_OPEN_KEY] = False
    return is_open_requested


def _operation_changed(current_operation: dict, updated_operation: dict) -> bool:
    current_cfg = current_operation.get("configuration_json") or {}
    updated_cfg = updated_operation.get("configuration_json") or {}
    current_desc = str(current_operation.get("description") or "").strip()
    updated_desc = str(updated_operation.get("description") or "").strip()
    if current_desc != updated_desc:
        return True
    try:
        return json.dumps(current_cfg, sort_keys=True) != json.dumps(updated_cfg, sort_keys=True)
    except (TypeError, ValueError):
        return current_cfg != updated_cfg


def _clear_state_prefix(prefix: str) -> None:
    for state_key in list(st.session_state.keys()):
        if str(state_key).startswith(prefix):
            st.session_state.pop(state_key, None)


def _clear_command_form_state(key_prefix: str, form_nonce: int) -> None:
    for field_name in TEST_EDITOR_COMMAND_FORM_FIELDS:
        st.session_state.pop(shared._command_form_key(key_prefix, form_nonce, field_name), None)
    st.session_state.pop(shared._command_form_key(key_prefix, form_nonce, "cfg"), None)


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


def _persist_test_editor_operation_update(
    item: dict,
    operation_index: int,
    current_operation: dict,
    updated_operation: dict,
    *,
    success_message: str,
    force_persist: bool = False,
) -> bool:
    if not force_persist and not _operation_changed(current_operation, updated_operation):
        return False

    original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
    shared._update_operation_in_item(item, operation_index, updated_operation)
    try:
        shared._persist_current_draft(
            success_message=success_message,
            rerun=False,
        )
    except Exception as exc:
        st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
        shared._render_persist_error(exc)
        return False
    return True


def _api_expander_url_label(raw_url: object) -> str:
    url = str(raw_url or "").strip()
    if not url:
        return "-"
    parsed = urlsplit(url)
    if not parsed.scheme and not parsed.netloc:
        return url
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return path


def _api_result_target_label(result_target: object) -> str:
    if isinstance(result_target, dict):
        cfg = shared._safe_dict(result_target)
        explicit_target = cfg.get("result_target") or cfg.get("resultTarget")
        if not explicit_target:
            result_constant = shared._safe_dict(
                cfg.get("resultConstant") or cfg.get("result_constant")
            )
            result_name = str(result_constant.get("name") or "").strip()
            if result_name:
                explicit_target = f"$.result.constants.{result_name}"
        result_target = explicit_target

    normalized_target = shared._normalize_context_path(result_target)
    if not normalized_target:
        return ""
    return str(normalized_target.rsplit(".", 1)[-1] or normalized_target).strip()


def _normalize_api_result_target_input(value: object) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    if raw_value.startswith("$"):
        return shared._normalize_context_path(raw_value)
    if "." in raw_value:
        return shared._normalize_context_path(raw_value)
    return f"$.result.constants.{raw_value}"


def _mark_command_for_reopen(operation_ui_key: str) -> None:
    st.session_state[TEST_EDITOR_REOPEN_COMMAND_UI_KEY] = str(operation_ui_key or "")


def _consume_reopen_command(operation_ui_key: str) -> bool:
    reopen_ui_key = str(st.session_state.get(TEST_EDITOR_REOPEN_COMMAND_UI_KEY) or "")
    if reopen_ui_key and reopen_ui_key == str(operation_ui_key or ""):
        st.session_state.pop(TEST_EDITOR_REOPEN_COMMAND_UI_KEY, None)
        return True
    return False


def _build_test_editor_command_label(operation: dict) -> str:
    cfg = shared._safe_dict(operation.get("configuration_json") or {})
    command_code = shared._normalize_command_code(cfg)
    if command_code == "readApi":
        url_label = _api_expander_url_label(cfg.get("url"))
        result_target_label = _api_result_target_label(cfg)
        if result_target_label:
            return (
                f"**Fetch data from a REST API** {_italicize(url_label)} "
                f"**response stored in variable** {_italicize(result_target_label)}"
            )
        return f"**Fetch data from a REST API** {_italicize(url_label)}"
    if command_code == "writeApi":
        method = str(cfg.get("method") or "POST").strip().upper() or "POST"
        url_label = _api_expander_url_label(cfg.get("url"))
        result_target_label = _api_result_target_label(cfg)
        if result_target_label:
            return (
                f"**Send data to a REST API {method}** {_italicize(url_label)} "
                f"**response stored in variable** {_italicize(result_target_label)}"
            )
        return f"**Send data to a REST API {method}** {_italicize(url_label)}"
    return shared._build_suite_command_markdown(operation)


def _build_test_editor_command_list_label(operation: dict) -> str:
    cfg = shared._safe_dict(operation.get("configuration_json") or {})
    command_code = shared._normalize_command_code(cfg)
    result_target_label = _api_result_target_label(cfg)
    if command_code == "readApi":
        if result_target_label:
            return (
                f"**Fetch data from a REST API** "
                f"**response stored in variable** {_italicize(result_target_label)}"
            )
        return "**Fetch data from a REST API**"
    if command_code == "writeApi":
        method = str(cfg.get("method") or "POST").strip().upper() or "POST"
        if result_target_label:
            return (
                f"**Send data to a REST API {method}** "
                f"**response stored in variable** {_italicize(result_target_label)}"
            )
        return f"**Send data to a REST API {method}**"
    return _build_test_editor_command_label(operation)


def _italicize(value: object) -> str:
    text = str(value or "").strip() or "-"
    return f"*{text}*"


def _clear_selected_test_editor_command() -> None:
    st.session_state.pop(TEST_EDITOR_SELECTED_COMMAND_UI_KEY, None)
    st.session_state.pop(TEST_EDITOR_SELECTED_COMMAND_ORDER_KEY, None)


def _selected_test_editor_command_ui_key() -> str:
    return str(st.session_state.get(TEST_EDITOR_SELECTED_COMMAND_UI_KEY) or "").strip()


def _selected_test_editor_command_order() -> int | None:
    raw_value = st.session_state.get(TEST_EDITOR_SELECTED_COMMAND_ORDER_KEY)
    try:
        return int(raw_value) if raw_value is not None else None
    except (TypeError, ValueError):
        return None


def _set_selected_test_editor_command(operation_ui_key: str, *, order: int | None = None) -> None:
    normalized_ui_key = str(operation_ui_key or "").strip()
    if normalized_ui_key:
        st.session_state[TEST_EDITOR_SELECTED_COMMAND_UI_KEY] = normalized_ui_key
        if order is not None:
            st.session_state[TEST_EDITOR_SELECTED_COMMAND_ORDER_KEY] = int(order)
        return
    _clear_selected_test_editor_command()


def _strip_command_markdown(label: object) -> str:
    return str(label or "").replace("**", "").replace("*", "").strip()


def _ensure_test_editor_operation_ui_key(item: dict, operation: dict, op_idx: int) -> str:
    item_ui_key = str(item.get("_ui_key") or shared.new_ui_key())
    item["_ui_key"] = item_ui_key
    operation_ui_key = str(operation.get("_ui_key") or f"{item_ui_key}_op_{op_idx}")
    operation["_ui_key"] = operation_ui_key
    return operation_ui_key


def _test_editor_operation_entries(item: dict | None) -> list[tuple[int, dict, str]]:
    operation_entries: list[tuple[int, dict, str]] = []
    current_item = item or {}
    for op_idx, operation in enumerate(shared._operation_list(item)):
        if not isinstance(operation, dict):
            continue
        operation_entries.append(
            (
                op_idx,
                operation,
                _ensure_test_editor_operation_ui_key(current_item, operation, op_idx),
            )
        )
    return operation_entries


def _resolve_selected_test_editor_command(item: dict | None) -> str:
    selected_ui_key = _selected_test_editor_command_ui_key()
    selected_order = _selected_test_editor_command_order()
    if not selected_ui_key:
        if selected_order is None:
            return ""
    operation_entries = _test_editor_operation_entries(item)
    valid_ui_keys = {operation_ui_key for _, _, operation_ui_key in operation_entries}
    if selected_ui_key in valid_ui_keys:
        return selected_ui_key
    if selected_order is not None:
        for op_idx, operation, operation_ui_key in operation_entries:
            operation_order = shared._safe_int(operation.get("order"), op_idx + 1)
            if operation_order == selected_order:
                _set_selected_test_editor_command(operation_ui_key, order=operation_order)
                return operation_ui_key
    _clear_selected_test_editor_command()
    return ""


def _clear_editor_state_for_operation(operation_ui_key: str, operation_index: int) -> None:
    _clear_command_form_state("test_editor_command", operation_index)
    _clear_command_form_state("test_editor_generic_command", operation_index)
    _clear_state_prefix(f"test_editor_api_command_{operation_ui_key}")


def _delete_test_editor_operation(item: dict, operation_ui_key: str) -> None:
    operation_index, _ = shared._find_operation_by_ui_key(item, operation_ui_key)
    if operation_index < 0:
        return

    _clear_editor_state_for_operation(operation_ui_key, operation_index)
    if shared._delete_operation_by_ui_key(item, operation_ui_key):
        if _selected_test_editor_command_ui_key() == str(operation_ui_key or "").strip():
            _clear_selected_test_editor_command()
        st.session_state[SUITE_FEEDBACK_KEY] = "Command removed."
        shared._persist_changes()


def _remember_selected_command_by_operation(operation: dict, operation_index: int) -> None:
    _set_selected_test_editor_command(
        str(operation.get("_ui_key") or ""),
        order=shared._safe_int(operation.get("order"), operation_index + 1),
    )


def _open_test_editor_comment_dialog(item_ui_key: str, operation_ui_key: str) -> None:
    st.session_state[TEST_EDITOR_COMMENT_DIALOG_OPEN_KEY] = True
    st.session_state[TEST_EDITOR_COMMENT_DIALOG_TARGET_ITEM_UI_KEY] = str(item_ui_key or "")
    st.session_state[TEST_EDITOR_COMMENT_DIALOG_TARGET_COMMAND_UI_KEY] = str(operation_ui_key or "")
    st.session_state[TEST_EDITOR_COMMENT_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(TEST_EDITOR_COMMENT_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_test_editor_comment_dialog() -> None:
    st.session_state[TEST_EDITOR_COMMENT_DIALOG_OPEN_KEY] = False
    st.session_state.pop(TEST_EDITOR_COMMENT_DIALOG_TARGET_ITEM_UI_KEY, None)
    st.session_state.pop(TEST_EDITOR_COMMENT_DIALOG_TARGET_COMMAND_UI_KEY, None)


@st.dialog("Modify comment", width="medium")
def _render_test_editor_comment_dialog(draft: dict) -> None:
    dialog_nonce = int(st.session_state.get(TEST_EDITOR_COMMENT_DIALOG_NONCE_KEY, 0))
    item_ui_key = str(st.session_state.get(TEST_EDITOR_COMMENT_DIALOG_TARGET_ITEM_UI_KEY) or "").strip()
    operation_ui_key = str(st.session_state.get(TEST_EDITOR_COMMENT_DIALOG_TARGET_COMMAND_UI_KEY) or "").strip()
    comment_key = f"test_editor_comment_dialog_value_{dialog_nonce}"
    item = shared._find_test_by_ui_key(draft, item_ui_key)

    if not isinstance(item, dict):
        st.error("Test di destinazione non trovato.")
        if st.button("Cancel", key=f"test_editor_comment_missing_item_cancel_{dialog_nonce}", use_container_width=True):
            _close_test_editor_comment_dialog()
            st.rerun()
        return

    operation_index, operation = shared._find_operation_by_ui_key(item, operation_ui_key)
    if not isinstance(operation, dict):
        st.error("Command non trovato.")
        if st.button("Cancel", key=f"test_editor_comment_missing_command_cancel_{dialog_nonce}", use_container_width=True):
            _close_test_editor_comment_dialog()
            st.rerun()
        return

    if comment_key not in st.session_state:
        st.session_state[comment_key] = str(operation.get("description") or "")

    st.text_area("Comment", key=comment_key, height=140)

    action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Cancel",
            key=f"test_editor_comment_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_test_editor_comment_dialog()
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Save",
            key=f"test_editor_comment_save_{dialog_nonce}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            _remember_selected_command_by_operation(operation, operation_index)
            updated_operation = deepcopy(operation)
            updated_operation["description"] = str(st.session_state.get(comment_key) or "").strip()
            if not _operation_changed(operation, updated_operation):
                _clear_editor_state_for_operation(operation_ui_key, operation_index)
                _close_test_editor_comment_dialog()
                st.rerun()
            if _persist_test_editor_operation_update(
                item,
                operation_index,
                operation,
                updated_operation,
                success_message="Comment updated.",
            ):
                _clear_editor_state_for_operation(operation_ui_key, operation_index)
                _close_test_editor_comment_dialog()
                st.rerun()
    with action_cols[2]:
        if st.button(
            "Delete command",
            key=f"test_editor_comment_delete_{dialog_nonce}",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            _close_test_editor_comment_dialog()
            _delete_test_editor_operation(item, operation_ui_key)


def _api_value_dialog_key(dialog_nonce: int, field: str) -> str:
    return f"test_editor_api_value_dialog_{dialog_nonce}_{field}"


def _api_editor_prefix(operation_ui_key: str) -> str:
    return f"test_editor_api_command_{operation_ui_key}"


def _api_editor_tab_state_key(operation_ui_key: str) -> str:
    return f"test_editor_api_tab_{str(operation_ui_key or '').strip()}"


def _api_kv_rows_from_source(source: object) -> list[dict]:
    if not isinstance(source, dict):
        return []
    rows: list[dict] = []
    for key, node in source.items():
        rows.append(
            {
                "row_id": shared.new_ui_key(),
                "key": str(key or "").strip(),
                "node": _coerce_api_value_node(node),
            }
        )
    return rows


def _ensure_api_kv_state(editor_state_key: str, source: object) -> None:
    if isinstance(st.session_state.get(editor_state_key), list):
        return
    st.session_state[editor_state_key] = _api_kv_rows_from_source(source)


def _normalize_api_literal_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=True, indent=2 if isinstance(value, (dict, list)) else None)


def _coerce_api_value_node(node: object) -> dict | None:
    if node is None:
        return None
    if isinstance(node, dict):
        kind = str(node.get("kind") or "").strip()
        if kind == TEST_EDITOR_API_VALUE_MODE_LITERAL:
            return {"kind": TEST_EDITOR_API_VALUE_MODE_LITERAL, "value": node.get("value")}
        if kind == TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE:
            return {
                "kind": TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE,
                "definitionId": str(node.get("definitionId") or "").strip(),
                "fieldPath": str(node.get("fieldPath") or node.get("field_path") or "").strip(),
            }
        if kind == TEST_EDITOR_API_VALUE_MODE_BUILT_IN:
            return {
                "kind": TEST_EDITOR_API_VALUE_MODE_BUILT_IN,
                "resolver": str(node.get("resolver") or "").strip(),
            }
        if kind == "source":
            return {
                "kind": "source",
                "sourceCode": str(node.get("sourceCode") or "").strip(),
            }
    return {"kind": TEST_EDITOR_API_VALUE_MODE_LITERAL, "value": node}


def _api_value_is_meaningful(node: dict | None) -> bool:
    if not isinstance(node, dict):
        return False
    kind = str(node.get("kind") or "").strip()
    if kind == TEST_EDITOR_API_VALUE_MODE_LITERAL:
        value = node.get("value")
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True
    if kind == TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE:
        return bool(str(node.get("definitionId") or "").strip())
    if kind == TEST_EDITOR_API_VALUE_MODE_BUILT_IN:
        return bool(str(node.get("resolver") or "").strip())
    if kind == "source":
        return bool(str(node.get("sourceCode") or "").strip())
    return False


def _validate_api_value_node(
    node: dict | None,
    *,
    allow_source: bool,
    field_label: str,
    scalar_only: bool = False,
) -> str | None:
    if not isinstance(node, dict):
        return f"{field_label} is required."

    kind = str(node.get("kind") or "").strip()
    if kind == TEST_EDITOR_API_VALUE_MODE_LITERAL:
        if scalar_only and isinstance(node.get("value"), (dict, list)):
            return f"{field_label}: only scalar literal values are supported."
        return None
    if kind == TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE:
        if not str(node.get("definitionId") or "").strip():
            return f"{field_label}: runtime value is required."
        field_path_error = _validate_api_field_path(node.get("fieldPath"))
        if field_path_error:
            return f"{field_label}: {field_path_error}"
        return None
    if kind == TEST_EDITOR_API_VALUE_MODE_BUILT_IN:
        resolver = str(node.get("resolver") or "").strip()
        if resolver not in TEST_EDITOR_API_BUILT_IN_OPTIONS:
            return f"{field_label}: built-in runtime function is required."
        return None
    if kind == "source":
        if not allow_source:
            return f"{field_label}: datasource is not supported here."
        if not str(node.get("sourceCode") or "").strip():
            return f"{field_label}: datasource is required."
        return None
    return f"{field_label}: unsupported value type."


def _api_runtime_definition_id(definition: dict) -> str:
    return str(definition.get("definitionId") or definition.get("path") or "").strip()


def _api_runtime_definition_label(definition: dict) -> str:
    name = str(definition.get("name") or _api_runtime_definition_id(definition) or "-").strip()
    context = str(definition.get("context") or definition.get("context_scope") or "").strip()
    value_type = str(definition.get("value_type") or "").strip()
    suffix = ", ".join(item for item in [context, value_type] if item)
    return f"{name} ({suffix})" if suffix else name


def _api_runtime_definition_by_id(definition_id: object, runtime_values: list[dict]) -> dict | None:
    normalized_definition_id = str(definition_id or "").strip()
    if not normalized_definition_id:
        return None
    return next(
        (
            item
            for item in runtime_values
            if _api_runtime_definition_id(item) == normalized_definition_id
        ),
        None,
    )


def _api_runtime_definition_supports_field_path(definition: dict | None) -> bool:
    if not isinstance(definition, dict):
        return False
    return str(definition.get("value_type") or "").strip() in {"json", "jsonArray"}


def _normalize_api_field_path(value: object) -> str:
    return str(value or "").strip()


def _validate_api_field_path(field_path: object) -> str | None:
    normalized = _normalize_api_field_path(field_path)
    if not normalized:
        return None
    if normalized.startswith("$"):
        return "Path must be relative and must not start with '$'."
    segments = normalized.split(".")
    if not segments or any(not segment.strip() for segment in segments):
        return "Path syntax is invalid."
    for segment in segments:
        if not TEST_EDITOR_API_FIELD_PATH_SEGMENT_RE.match(segment):
            return "Path syntax is invalid. Use payload.access_token, items[0].id or [0].id."
    return None


def _apply_visible_api_runtime_effect(active_definitions: list[dict], operation: dict) -> None:
    configuration_json = shared._safe_dict(operation.get("configuration_json") or {})
    command_code = shared._normalize_command_code(configuration_json)

    if command_code == "deleteConstant":
        target_definition_id = str(
            configuration_json.get("definitionId") or configuration_json.get("definition_id") or ""
        ).strip()
        target_name = str(configuration_json.get("name") or "").strip()
        target_context = str(configuration_json.get("context") or configuration_json.get("scope") or "").strip()
        for index in range(len(active_definitions) - 1, -1, -1):
            definition = active_definitions[index]
            if target_definition_id and _api_runtime_definition_id(definition) == target_definition_id:
                active_definitions.pop(index)
                break
            if (
                target_name
                and target_context
                and str(definition.get("name") or "").strip() == target_name
                and str(definition.get("context") or "").strip() == target_context
            ):
                active_definitions.pop(index)
                break
        return

    if command_code == "initConstant":
        name = str(configuration_json.get("name") or "").strip()
        context = str(configuration_json.get("context") or configuration_json.get("scope") or "").strip()
        value_type = shared._normalized_value_type(configuration_json)
        if name and context and value_type:
            definition_id = str(
                configuration_json.get("definitionId") or configuration_json.get("definition_id") or ""
            ).strip()
            path = f"$.{context}.constants.{name}"
            preview_value = configuration_json.get("value") if value_type in {"json", "raw", "value"} else None
            active_definitions.append(
                {
                    "definitionId": definition_id or path,
                    "name": name,
                    "context": context,
                    "value_type": value_type,
                    "path": path,
                    "preview_value": deepcopy(preview_value),
                }
            )

    result_constant = shared._safe_dict(
        configuration_json.get("resultConstant") or configuration_json.get("result_constant")
    )
    result_name, result_type = shared._command_result_constant(configuration_json) or (None, None)
    if result_name and result_type:
        path = f"$.result.constants.{result_name}"
        result_definition_id = str(
            result_constant.get("definitionId") or result_constant.get("definition_id") or ""
        ).strip()
        active_definitions.append(
            {
                "definitionId": result_definition_id or path,
                "name": result_name,
                "context": "result",
                "value_type": result_type,
                "path": path,
                "preview_value": None,
            }
        )


def _collect_visible_api_runtime_values(
    draft: dict,
    item: dict,
    *,
    stop_before_index: int | None,
) -> list[dict]:
    active_definitions: list[dict] = []
    section_type = shared._section_type_for_item(item)

    before_all_hook = shared._find_hook_by_phase(draft, "before-all")
    before_each_hook = shared._find_hook_by_phase(draft, "before-each")

    def _append_from_item(source_item: dict | None, *, limit: int | None = None) -> None:
        operations = shared._operation_list(source_item)
        for op_index, operation in enumerate(operations):
            if limit is not None and op_index >= limit:
                break
            _apply_visible_api_runtime_effect(active_definitions, operation)

    if section_type in {"beforeEach", "test", "afterEach", "afterAll"}:
        _append_from_item(before_all_hook)
    if section_type in {"beforeEach", "test", "afterEach"}:
        _append_from_item(before_each_hook)
    if section_type in {"beforeAll", "beforeEach", "afterEach", "afterAll", "test"}:
        _append_from_item(item, limit=stop_before_index)

    filtered_definitions = [
        definition
        for definition in active_definitions
        if str(definition.get("context") or "").strip()
        in shared.READABLE_SCOPES_BY_SECTION.get(section_type, set())
    ]

    deduped_by_id: dict[str, dict] = {}
    for definition in filtered_definitions:
        definition_id = _api_runtime_definition_id(definition)
        if definition_id:
            deduped_by_id[definition_id] = definition

    options = list(deduped_by_id.values())
    options.sort(
        key=lambda item: (
            str(item.get("context") or ""),
            str(item.get("name") or ""),
            str(item.get("value_type") or ""),
        )
    )
    return options


def _collect_visible_api_body_sources(draft: dict, item: dict) -> list[dict]:
    return [
        source
        for source in shared._collect_visible_source_options(draft, item)
        if str(source.get("value_type") or "").strip() in {"dataset", "jsonArray"}
    ]


def _collect_visible_api_form_runtime_values(
    draft: dict,
    item: dict,
    *,
    stop_before_index: int | None,
) -> list[dict]:
    return [
        definition
        for definition in _collect_visible_api_runtime_values(
            draft,
            item,
            stop_before_index=stop_before_index,
        )
        if str(definition.get("value_type") or "").strip() not in {"dataset", "jsonArray"}
    ]


def _resolve_api_source_type(source_code: object, available_sources: list[dict]) -> str:
    normalized_source_code = str(source_code or "").strip()
    source_definition = next(
        (
            source
            for source in available_sources
            if str(source.get("source_code") or source.get("code") or "").strip() == normalized_source_code
        ),
        None,
    )
    return str(source_definition.get("value_type") or "").strip() if isinstance(source_definition, dict) else ""


def _api_source_label(source: dict) -> str:
    source_code = str(source.get("source_code") or source.get("code") or "-").strip() or "-"
    source_type = str(source.get("value_type") or "").strip()
    return f"{source_code} ({shared._source_type_label(source_type)})" if source_type else source_code


def _api_preview_text(value: object) -> str:
    if isinstance(value, str):
        return value if len(value) <= 120 else f"{value[:117]}..."
    if value is None:
        return "(empty)"
    try:
        rendered = json.dumps(value, ensure_ascii=True)
    except (TypeError, ValueError):
        rendered = str(value)
    return rendered if len(rendered) <= 120 else f"{rendered[:117]}..."


def _format_api_value_summary(
    node: object,
    *,
    runtime_values: list[dict],
    sources: list[dict] | None = None,
) -> str:
    normalized_node = _coerce_api_value_node(node)
    if not isinstance(normalized_node, dict):
        return "No value configured."

    kind = str(normalized_node.get("kind") or "").strip()
    if kind == TEST_EDITOR_API_VALUE_MODE_LITERAL:
        return f"Literal: {_api_preview_text(normalized_node.get('value'))}"
    if kind == TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE:
        definition_id = str(normalized_node.get("definitionId") or "").strip()
        field_path = _normalize_api_field_path(normalized_node.get("fieldPath"))
        definition = _api_runtime_definition_by_id(definition_id, runtime_values)
        if isinstance(definition, dict):
            base_label = f"Runtime value: {_api_runtime_definition_label(definition)}"
        else:
            base_label = f"Runtime value: {definition_id or '-'}"
        return f"{base_label} -> {field_path}" if field_path else base_label
    if kind == TEST_EDITOR_API_VALUE_MODE_BUILT_IN:
        resolver = str(normalized_node.get("resolver") or "").strip()
        return f"Built-in: {TEST_EDITOR_API_BUILT_IN_LABELS.get(resolver, resolver or '-')}"
    if kind == "source":
        source_code = str(normalized_node.get("sourceCode") or "").strip()
        source_definition = next(
            (
                item
                for item in (sources or [])
                if str(item.get("source_code") or item.get("code") or "").strip() == source_code
            ),
            None,
        )
        if isinstance(source_definition, dict):
            source_type = str(source_definition.get("value_type") or "").strip()
            return f"{shared._source_type_label(source_type)} datasource: {source_code}"
        return f"Datasource: {source_code or '-'}"
    return "Unsupported value."


def _open_test_editor_api_value_dialog(
    *,
    item_ui_key: str,
    operation_ui_key: str,
    target_kind: str,
    section: str = "",
    row_id: str = "",
    auth_field: str = "",
) -> None:
    st.session_state[TEST_EDITOR_API_VALUE_DIALOG_OPEN_KEY] = True
    st.session_state[TEST_EDITOR_API_VALUE_DIALOG_TARGET_ITEM_UI_KEY] = str(item_ui_key or "")
    st.session_state[TEST_EDITOR_API_VALUE_DIALOG_TARGET_COMMAND_UI_KEY] = str(operation_ui_key or "")
    st.session_state[TEST_EDITOR_API_VALUE_DIALOG_TARGET_KIND_KEY] = str(target_kind or "")
    st.session_state[TEST_EDITOR_API_VALUE_DIALOG_TARGET_SECTION_KEY] = str(section or "")
    st.session_state[TEST_EDITOR_API_VALUE_DIALOG_TARGET_ROW_ID_KEY] = str(row_id or "")
    st.session_state[TEST_EDITOR_API_VALUE_DIALOG_TARGET_AUTH_FIELD_KEY] = str(auth_field or "")
    st.session_state[TEST_EDITOR_API_VALUE_DIALOG_NONCE_KEY] = (
        int(st.session_state.get(TEST_EDITOR_API_VALUE_DIALOG_NONCE_KEY, 0)) + 1
    )


def _close_test_editor_api_value_dialog() -> None:
    st.session_state[TEST_EDITOR_API_VALUE_DIALOG_OPEN_KEY] = False
    st.session_state.pop(TEST_EDITOR_API_VALUE_DIALOG_TARGET_ITEM_UI_KEY, None)
    st.session_state.pop(TEST_EDITOR_API_VALUE_DIALOG_TARGET_COMMAND_UI_KEY, None)
    st.session_state.pop(TEST_EDITOR_API_VALUE_DIALOG_TARGET_KIND_KEY, None)
    st.session_state.pop(TEST_EDITOR_API_VALUE_DIALOG_TARGET_SECTION_KEY, None)
    st.session_state.pop(TEST_EDITOR_API_VALUE_DIALOG_TARGET_ROW_ID_KEY, None)
    st.session_state.pop(TEST_EDITOR_API_VALUE_DIALOG_TARGET_AUTH_FIELD_KEY, None)


def _initialize_test_editor_api_value_dialog_state(
    *,
    dialog_nonce: int,
    node: object,
    key_value: str,
    target_kind: str,
    available_sources: list[dict],
) -> None:
    init_key = _api_value_dialog_key(dialog_nonce, "initialized")
    if st.session_state.get(init_key):
        return

    normalized_node = _coerce_api_value_node(node)
    mode_key = _api_value_dialog_key(dialog_nonce, "mode")
    key_input_key = _api_value_dialog_key(dialog_nonce, "key")
    literal_key = _api_value_dialog_key(dialog_nonce, "literal")
    runtime_key = _api_value_dialog_key(dialog_nonce, "runtime_value")
    field_path_key = _api_value_dialog_key(dialog_nonce, "field_path")
    built_in_key = _api_value_dialog_key(dialog_nonce, "built_in")
    source_key = _api_value_dialog_key(dialog_nonce, "source")

    st.session_state[key_input_key] = str(key_value or "").strip()
    st.session_state[literal_key] = _normalize_api_literal_text(
        normalized_node.get("value") if isinstance(normalized_node, dict) else ""
    )
    st.session_state[runtime_key] = ""
    st.session_state[field_path_key] = ""
    st.session_state[built_in_key] = TEST_EDITOR_API_BUILT_IN_OPTIONS[0]
    st.session_state[source_key] = ""

    if not isinstance(normalized_node, dict):
        st.session_state[mode_key] = TEST_EDITOR_API_VALUE_MODE_LITERAL
        st.session_state[init_key] = True
        return

    kind = str(normalized_node.get("kind") or "").strip()
    if kind == TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE:
        st.session_state[mode_key] = TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE
        st.session_state[runtime_key] = str(normalized_node.get("definitionId") or "").strip()
        st.session_state[field_path_key] = _normalize_api_field_path(normalized_node.get("fieldPath"))
    elif kind == TEST_EDITOR_API_VALUE_MODE_BUILT_IN:
        st.session_state[mode_key] = TEST_EDITOR_API_VALUE_MODE_BUILT_IN
        resolver = str(normalized_node.get("resolver") or "").strip()
        st.session_state[built_in_key] = resolver if resolver in TEST_EDITOR_API_BUILT_IN_OPTIONS else "now"
    elif kind == "source" and target_kind == "body":
        source_type = _resolve_api_source_type(normalized_node.get("sourceCode"), available_sources)
        st.session_state[mode_key] = (
            TEST_EDITOR_API_VALUE_MODE_SOURCE_DATASET
            if source_type == "dataset"
            else TEST_EDITOR_API_VALUE_MODE_SOURCE_JSON_ARRAY
        )
        st.session_state[source_key] = str(normalized_node.get("sourceCode") or "").strip()
    else:
        st.session_state[mode_key] = TEST_EDITOR_API_VALUE_MODE_LITERAL

    st.session_state[init_key] = True


def _render_test_editor_api_value_dialog_fields(
    *,
    dialog_nonce: int,
    target_kind: str,
    runtime_values: list[dict],
    available_sources: list[dict],
) -> None:
    mode_key = _api_value_dialog_key(dialog_nonce, "mode")
    key_input_key = _api_value_dialog_key(dialog_nonce, "key")
    literal_key = _api_value_dialog_key(dialog_nonce, "literal")
    runtime_key = _api_value_dialog_key(dialog_nonce, "runtime_value")
    field_path_key = _api_value_dialog_key(dialog_nonce, "field_path")
    built_in_key = _api_value_dialog_key(dialog_nonce, "built_in")
    source_key = _api_value_dialog_key(dialog_nonce, "source")

    mode_options = [
        TEST_EDITOR_API_VALUE_MODE_LITERAL,
        TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE,
        TEST_EDITOR_API_VALUE_MODE_BUILT_IN,
    ]
    if target_kind == "body":
        mode_options.extend(
            [
                TEST_EDITOR_API_VALUE_MODE_SOURCE_JSON_ARRAY,
                TEST_EDITOR_API_VALUE_MODE_SOURCE_DATASET,
            ]
        )

    current_mode = str(st.session_state.get(mode_key) or TEST_EDITOR_API_VALUE_MODE_LITERAL).strip()
    if current_mode not in mode_options:
        current_mode = TEST_EDITOR_API_VALUE_MODE_LITERAL
        st.session_state[mode_key] = current_mode

    if target_kind in {"kv", "formBody"}:
        st.text_input("Key", key=key_input_key, placeholder="name")

    st.selectbox(
        "Value type",
        options=mode_options,
        key=mode_key,
        format_func=lambda item: TEST_EDITOR_API_VALUE_MODE_LABELS.get(item, item),
    )

    current_mode = str(st.session_state.get(mode_key) or TEST_EDITOR_API_VALUE_MODE_LITERAL).strip()
    if current_mode == TEST_EDITOR_API_VALUE_MODE_LITERAL:
        if target_kind == "body":
            st.text_area(
                "Value",
                key=literal_key,
                height=180,
                placeholder='Examples: "abc", 1, true, {"id": 1}, [1,2,3]',
            )
        else:
            st.text_input("Value", key=literal_key, placeholder='Examples: "abc", 1, true')
        return

    if current_mode == TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE:
        options = [_api_runtime_definition_id(item) for item in runtime_values if _api_runtime_definition_id(item)]
        current_value = str(st.session_state.get(runtime_key) or "").strip()
        if current_value and current_value not in options:
            options = [current_value] + options
        st.selectbox(
            "Runtime value",
            options=options or [""],
            key=runtime_key,
            format_func=lambda item: _api_runtime_definition_label(
                next(
                    (
                        definition
                        for definition in runtime_values
                        if _api_runtime_definition_id(definition) == str(item)
                    ),
                    {"name": str(item or "-")},
                )
            ),
            disabled=not bool(options),
        )
        selected_definition = _api_runtime_definition_by_id(
            st.session_state.get(runtime_key),
            runtime_values,
        )
        if _api_runtime_definition_supports_field_path(selected_definition):
            st.text_input(
                "Path",
                key=field_path_key,
                placeholder="payload.access_token, items[0].id or [0].id",
                help="Relative path inside the selected runtime value.",
            )
        else:
            st.session_state[field_path_key] = ""
        return

    if current_mode == TEST_EDITOR_API_VALUE_MODE_BUILT_IN:
        st.selectbox(
            "Built-in runtime function",
            options=TEST_EDITOR_API_BUILT_IN_OPTIONS,
            key=built_in_key,
            format_func=lambda item: TEST_EDITOR_API_BUILT_IN_LABELS.get(item, item),
        )
        return

    source_type = "jsonArray" if current_mode == TEST_EDITOR_API_VALUE_MODE_SOURCE_JSON_ARRAY else "dataset"
    filtered_sources = [
        source
        for source in available_sources
        if str(source.get("value_type") or "").strip() == source_type
    ]
    options = [
        str(source.get("source_code") or source.get("code") or "").strip()
        for source in filtered_sources
        if str(source.get("source_code") or source.get("code") or "").strip()
    ]
    current_value = str(st.session_state.get(source_key) or "").strip()
    if current_value and current_value not in options:
        options = [current_value] + options
    st.selectbox(
        "Datasource",
        options=options or [""],
        key=source_key,
        format_func=lambda item: _api_source_label(
            next(
                (
                    source
                    for source in filtered_sources
                    if str(source.get("source_code") or source.get("code") or "").strip() == str(item)
                ),
                {"source_code": str(item or "-"), "value_type": source_type},
            )
        ),
        disabled=not bool(options),
    )


def _collect_test_editor_api_value_dialog_node(
    *,
    dialog_nonce: int,
    target_kind: str,
    runtime_values: list[dict],
) -> tuple[dict | None, str | None]:
    mode = str(
        st.session_state.get(_api_value_dialog_key(dialog_nonce, "mode"))
        or TEST_EDITOR_API_VALUE_MODE_LITERAL
    ).strip()
    if mode == TEST_EDITOR_API_VALUE_MODE_LITERAL:
        literal_text = str(st.session_state.get(_api_value_dialog_key(dialog_nonce, "literal")) or "").strip()
        try:
            parsed = json.loads(literal_text)
            return {"kind": TEST_EDITOR_API_VALUE_MODE_LITERAL, "value": parsed}, None
        except (json.JSONDecodeError, ValueError):
            return {"kind": TEST_EDITOR_API_VALUE_MODE_LITERAL, "value": literal_text}, None

    if mode == TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE:
        definition_id = str(st.session_state.get(_api_value_dialog_key(dialog_nonce, "runtime_value")) or "").strip()
        if not definition_id:
            return None, "Runtime value is required."
        selected_definition = _api_runtime_definition_by_id(definition_id, runtime_values)
        field_path = _normalize_api_field_path(
            st.session_state.get(_api_value_dialog_key(dialog_nonce, "field_path"))
        )
        if field_path and not _api_runtime_definition_supports_field_path(selected_definition):
            return None, "Path is supported only for json and jsonArray runtime values."
        field_path_error = _validate_api_field_path(field_path)
        if field_path_error:
            return None, field_path_error
        node = {"kind": TEST_EDITOR_API_VALUE_MODE_RUNTIME_VALUE, "definitionId": definition_id}
        if field_path:
            node["fieldPath"] = field_path
        return node, None

    if mode == TEST_EDITOR_API_VALUE_MODE_BUILT_IN:
        resolver = str(st.session_state.get(_api_value_dialog_key(dialog_nonce, "built_in")) or "").strip()
        if resolver not in TEST_EDITOR_API_BUILT_IN_OPTIONS:
            return None, "Built-in runtime function is required."
        return {"kind": TEST_EDITOR_API_VALUE_MODE_BUILT_IN, "resolver": resolver}, None

    if target_kind == "body" and mode in {
        TEST_EDITOR_API_VALUE_MODE_SOURCE_JSON_ARRAY,
        TEST_EDITOR_API_VALUE_MODE_SOURCE_DATASET,
    }:
        source_code = str(st.session_state.get(_api_value_dialog_key(dialog_nonce, "source")) or "").strip()
        if not source_code:
            return None, "Datasource is required."
        return {"kind": "source", "sourceCode": source_code}, None

    return None, "Unsupported value type."


def _collect_api_kv_payload(rows: object, field_label: str) -> tuple[dict, str | None]:
    if not isinstance(rows, list) or not rows:
        return {}, None

    payload: dict[str, dict] = {}
    seen_keys: set[str] = set()
    for index, row in enumerate(rows, start=1):
        key = str((row or {}).get("key") or "").strip()
        if not key:
            return {}, f"{field_label}: key is required at row {index}."
        if key in seen_keys:
            return {}, f"{field_label}: duplicate key '{key}' at row {index}."
        node = _coerce_api_value_node((row or {}).get("node"))
        node_error = _validate_api_value_node(node, allow_source=False, field_label=f"{field_label} row {index}")
        if node_error:
            return {}, node_error
        payload[key] = node or {"kind": TEST_EDITOR_API_VALUE_MODE_LITERAL, "value": ""}
        seen_keys.add(key)
    return payload, None


def _collect_api_form_body_payload(rows: object, field_label: str) -> tuple[dict, str | None]:
    if not isinstance(rows, list) or not rows:
        return {}, None

    payload: dict[str, dict] = {}
    seen_keys: set[str] = set()
    for index, row in enumerate(rows, start=1):
        key = str((row or {}).get("key") or "").strip()
        if not key:
            return {}, f"{field_label}: key is required at row {index}."
        if key in seen_keys:
            return {}, f"{field_label}: duplicate key '{key}' at row {index}."
        node = _coerce_api_value_node((row or {}).get("node"))
        node_error = _validate_api_value_node(
            node,
            allow_source=False,
            field_label=f"{field_label} row {index}",
            scalar_only=True,
        )
        if node_error:
            return {}, node_error
        payload[key] = node or {"kind": TEST_EDITOR_API_VALUE_MODE_LITERAL, "value": ""}
        seen_keys.add(key)
    return payload, None


def _collect_api_auth_payload(prefix: str) -> tuple[dict, str | None]:
    auth_type = str(st.session_state.get(f"{prefix}_auth_type") or "none").strip()
    if auth_type not in TEST_EDITOR_API_AUTH_TYPE_OPTIONS or auth_type == "none":
        return {}, None

    fields = TEST_EDITOR_API_AUTH_FIELDS.get(auth_type, [])
    payload = {"type": auth_type}
    for field_name in fields:
        node = _coerce_api_value_node(st.session_state.get(f"{prefix}_auth_{field_name}"))
        payload[field_name] = node or {"kind": TEST_EDITOR_API_VALUE_MODE_LITERAL, "value": ""}
        if not _api_value_is_meaningful(node):
            label = TEST_EDITOR_API_AUTH_FIELD_LABELS.get(field_name, field_name)
            return {}, f"Auth {label} is required."
        node_error = _validate_api_value_node(
            node,
            allow_source=False,
            field_label=f"Auth {TEST_EDITOR_API_AUTH_FIELD_LABELS.get(field_name, field_name)}",
        )
        if node_error:
            return {}, node_error
    return payload, None


def _render_api_kv_section(
    item: dict,
    operation_ui_key: str,
    section: str,
    rows: list[dict],
    runtime_values: list[dict],
) -> None:
    labels = {
        "params": ("No query parameter configured.", "+ Query parameter"),
        "path": ("No path parameter configured.", "+ Path parameter"),
        "headers": ("No header configured.", "+ Header"),
    }
    empty_label, add_label = labels.get(section, ("No item configured.", "+ Item"))

    with st.container():
        if rows:
            for row in rows:
                row_id = str(row.get("row_id") or "")
                key_value = str(row.get("key") or "").strip() or "-"
                summary = _format_api_value_summary(row.get("node"), runtime_values=runtime_values)
                row_cols = st.columns([3, 7, 1, 1], gap="small", vertical_alignment="center")
                with row_cols[0]:
                    st.markdown(f"**{key_value}**")
                with row_cols[1]:
                    st.caption(summary)
                with row_cols[2]:
                    if st.button(
                        "",
                        key=f"{operation_ui_key}_{section}_{row_id}_edit",
                        icon=":material/edit:",
                        help="Edit",
                        type="tertiary",
                        use_container_width=True,
                    ):
                        _open_test_editor_api_value_dialog(
                            item_ui_key=str(item.get("_ui_key") or ""),
                            operation_ui_key=operation_ui_key,
                            target_kind="kv",
                            section=section,
                            row_id=row_id,
                        )
                        st.rerun()
                with row_cols[3]:
                    if st.button(
                        "",
                        key=f"{operation_ui_key}_{section}_{row_id}_delete",
                        icon=":material/delete:",
                        help="Delete",
                        type="tertiary",
                        use_container_width=True,
                    ):
                        st.session_state[f"{_api_editor_prefix(operation_ui_key)}_{section}_rows"] = [
                            candidate
                            for candidate in rows
                            if str(candidate.get("row_id") or "") != row_id
                        ]
                        st.rerun()
        else:
            st.caption(empty_label)

        if st.button(
            add_label,
            key=f"{operation_ui_key}_{section}_add",
            icon=":material/add:",
            type="tertiary",
            use_container_width=True,
        ):
            _open_test_editor_api_value_dialog(
                item_ui_key=str(item.get("_ui_key") or ""),
                operation_ui_key=operation_ui_key,
                target_kind="kv",
                section=section,
            )
            st.rerun()


def _render_api_form_body_section(
    item: dict,
    operation_ui_key: str,
    rows: list[dict],
    runtime_values: list[dict],
) -> None:
    with st.container():
        if rows:
            for row in rows:
                row_id = str(row.get("row_id") or "")
                key_value = str(row.get("key") or "").strip() or "-"
                summary = _format_api_value_summary(row.get("node"), runtime_values=runtime_values)
                row_cols = st.columns([3, 7, 1, 1], gap="small", vertical_alignment="center")
                with row_cols[0]:
                    st.markdown(f"**{key_value}**")
                with row_cols[1]:
                    st.caption(summary)
                with row_cols[2]:
                    if st.button(
                        "",
                        key=f"{operation_ui_key}_form_body_{row_id}_edit",
                        icon=":material/edit:",
                        help="Edit",
                        type="tertiary",
                        use_container_width=True,
                    ):
                        _open_test_editor_api_value_dialog(
                            item_ui_key=str(item.get("_ui_key") or ""),
                            operation_ui_key=operation_ui_key,
                            target_kind="formBody",
                            row_id=row_id,
                        )
                        st.rerun()
                with row_cols[3]:
                    if st.button(
                        "",
                        key=f"{operation_ui_key}_form_body_{row_id}_delete",
                        icon=":material/delete:",
                        help="Delete",
                        type="tertiary",
                        use_container_width=True,
                    ):
                        st.session_state[f"{_api_editor_prefix(operation_ui_key)}_form_body_rows"] = [
                            candidate
                            for candidate in rows
                            if str(candidate.get("row_id") or "") != row_id
                        ]
                        st.rerun()
        else:
            st.caption("No form field configured.")

        if st.button(
            "+ Form field",
            key=f"{operation_ui_key}_form_body_add",
            icon=":material/add:",
            type="tertiary",
            use_container_width=True,
        ):
            _open_test_editor_api_value_dialog(
                item_ui_key=str(item.get("_ui_key") or ""),
                operation_ui_key=operation_ui_key,
                target_kind="formBody",
            )
            st.rerun()


def _render_api_auth_section(
    item: dict,
    operation_ui_key: str,
    prefix: str,
    runtime_values: list[dict],
) -> None:
    auth_type = st.selectbox(
        "Auth type",
        options=TEST_EDITOR_API_AUTH_TYPE_OPTIONS,
        key=f"{prefix}_auth_type",
        format_func=lambda item: TEST_EDITOR_API_AUTH_TYPE_LABELS.get(item, item),
    )

    fields = TEST_EDITOR_API_AUTH_FIELDS.get(auth_type, [])
    with st.container(border=True):
        if not fields:
            st.caption("No authentication configured.")
            return
        for field_name in fields:
            field_key = f"{prefix}_auth_{field_name}"
            if field_key not in st.session_state:
                st.session_state[field_key] = {"kind": TEST_EDITOR_API_VALUE_MODE_LITERAL, "value": ""}
            summary = _format_api_value_summary(st.session_state.get(field_key), runtime_values=runtime_values)
            row_cols = st.columns([3, 8, 1], gap="small", vertical_alignment="center")
            with row_cols[0]:
                st.markdown(f"**{TEST_EDITOR_API_AUTH_FIELD_LABELS.get(field_name, field_name)}**")
            with row_cols[1]:
                st.caption(summary)
            with row_cols[2]:
                if st.button(
                    "",
                    key=f"{operation_ui_key}_auth_{field_name}_edit",
                    icon=":material/edit:",
                    help="Edit",
                    type="tertiary",
                    use_container_width=True,
                ):
                    _open_test_editor_api_value_dialog(
                        item_ui_key=str(item.get("_ui_key") or ""),
                        operation_ui_key=operation_ui_key,
                        target_kind="auth",
                        auth_field=field_name,
                    )
                    st.rerun()


def _render_api_body_preview(
    node: dict | None,
    *,
    body_type: str,
    runtime_values: list[dict],
    sources: list[dict],
) -> None:
    if not isinstance(node, dict):
        st.caption("No body configured.")
        return

    st.caption(_format_api_value_summary(node, runtime_values=runtime_values, sources=sources))
    if str(node.get("kind") or "").strip() != TEST_EDITOR_API_VALUE_MODE_LITERAL:
        return

    literal_value = node.get("value")
    if isinstance(literal_value, (dict, list)):
        st.code(json.dumps(literal_value, ensure_ascii=True, indent=2), language="json")
        return
    if body_type == "json":
        preview_text = str(literal_value or "").strip()
        if preview_text:
            st.code(preview_text, language="json")
        else:
            st.caption("(empty JSON body)")
        return
    st.code(str(literal_value or ""), language="text")


def _render_api_body_section(
    item: dict,
    operation_ui_key: str,
    prefix: str,
    runtime_values: list[dict],
    sources: list[dict],
) -> None:
    st.selectbox("Body type", options=shared.HTTP_BODY_TYPE_OPTIONS, key=f"{prefix}_body_type")
    with st.container(border=True):
        _render_api_body_preview(
            _coerce_api_value_node(st.session_state.get(f"{prefix}_body_node")),
            body_type=str(st.session_state.get(f"{prefix}_body_type") or "json").strip(),
            runtime_values=runtime_values,
            sources=sources,
        )
    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Edit body",
            key=f"{operation_ui_key}_body_edit",
            icon=":material/edit:",
            type="tertiary",
            use_container_width=True,
        ):
            _open_test_editor_api_value_dialog(
                item_ui_key=str(item.get("_ui_key") or ""),
                operation_ui_key=operation_ui_key,
                target_kind="body",
            )
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Clear body",
            key=f"{operation_ui_key}_body_clear",
            icon=":material/delete:",
            type="tertiary",
            disabled=st.session_state.get(f"{prefix}_body_node") is None,
            use_container_width=True,
        ):
            st.session_state[f"{prefix}_body_node"] = None
            st.rerun()


@st.dialog("Edit API value", width="large")
def _render_test_editor_api_value_dialog(draft: dict) -> None:
    dialog_nonce = int(st.session_state.get(TEST_EDITOR_API_VALUE_DIALOG_NONCE_KEY, 0))
    item_ui_key = str(st.session_state.get(TEST_EDITOR_API_VALUE_DIALOG_TARGET_ITEM_UI_KEY) or "").strip()
    operation_ui_key = str(st.session_state.get(TEST_EDITOR_API_VALUE_DIALOG_TARGET_COMMAND_UI_KEY) or "").strip()
    target_kind = str(st.session_state.get(TEST_EDITOR_API_VALUE_DIALOG_TARGET_KIND_KEY) or "").strip()
    section = str(st.session_state.get(TEST_EDITOR_API_VALUE_DIALOG_TARGET_SECTION_KEY) or "").strip()
    row_id = str(st.session_state.get(TEST_EDITOR_API_VALUE_DIALOG_TARGET_ROW_ID_KEY) or "").strip()
    auth_field = str(st.session_state.get(TEST_EDITOR_API_VALUE_DIALOG_TARGET_AUTH_FIELD_KEY) or "").strip()

    item = shared._find_test_by_ui_key(draft, item_ui_key)
    if not isinstance(item, dict):
        st.error("Test di destinazione non trovato.")
        if st.button("Cancel", key=f"test_editor_api_value_missing_item_cancel_{dialog_nonce}", use_container_width=True):
            _close_test_editor_api_value_dialog()
            st.rerun()
        return

    operation_index, operation = shared._find_operation_by_ui_key(item, operation_ui_key)
    if not isinstance(operation, dict):
        st.error("Command non trovato.")
        if st.button(
            "Cancel",
            key=f"test_editor_api_value_missing_command_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_test_editor_api_value_dialog()
            st.rerun()
        return

    prefix = _api_editor_prefix(operation_ui_key)
    runtime_values = _collect_visible_api_runtime_values(
        draft,
        item,
        stop_before_index=operation_index,
    )
    form_runtime_values = _collect_visible_api_form_runtime_values(
        draft,
        item,
        stop_before_index=operation_index,
    )
    body_sources = _collect_visible_api_body_sources(draft, item)

    current_key = ""
    current_node = None
    if target_kind == "kv":
        rows_key = f"{prefix}_{section}_rows"
        rows = st.session_state.get(rows_key)
        if not isinstance(rows, list):
            rows = []
            st.session_state[rows_key] = rows
        current_row = next(
            (row for row in rows if str(row.get("row_id") or "").strip() == row_id),
            None,
        )
        if isinstance(current_row, dict):
            current_key = str(current_row.get("key") or "").strip()
            current_node = current_row.get("node")
        st.caption(
            {
                "params": "Query parameter",
                "path": "Path parameter",
                "headers": "Header",
            }.get(section, "Item")
        )
    elif target_kind == "formBody":
        rows_key = f"{prefix}_form_body_rows"
        rows = st.session_state.get(rows_key)
        if not isinstance(rows, list):
            rows = []
            st.session_state[rows_key] = rows
        current_row = next(
            (row for row in rows if str(row.get("row_id") or "").strip() == row_id),
            None,
        )
        if isinstance(current_row, dict):
            current_key = str(current_row.get("key") or "").strip()
            current_node = current_row.get("node")
        st.caption("Form field")
    elif target_kind == "auth":
        current_node = st.session_state.get(f"{prefix}_auth_{auth_field}")
        st.caption(TEST_EDITOR_API_AUTH_FIELD_LABELS.get(auth_field, "Auth field"))
    elif target_kind == "body":
        current_node = st.session_state.get(f"{prefix}_body_node")
        st.caption("Request body")

    _initialize_test_editor_api_value_dialog_state(
        dialog_nonce=dialog_nonce,
        node=current_node,
        key_value=current_key,
        target_kind=target_kind,
        available_sources=body_sources,
    )

    _render_test_editor_api_value_dialog_fields(
        dialog_nonce=dialog_nonce,
        target_kind=target_kind,
        runtime_values=form_runtime_values if target_kind == "formBody" else runtime_values,
        available_sources=body_sources,
    )

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Cancel",
            key=f"test_editor_api_value_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            _close_test_editor_api_value_dialog()
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Save",
            key=f"test_editor_api_value_save_{dialog_nonce}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            node, node_error = _collect_test_editor_api_value_dialog_node(
                dialog_nonce=dialog_nonce,
                target_kind=target_kind,
                runtime_values=runtime_values,
            )
            if node_error:
                st.error(node_error)
                return

            if target_kind == "kv":
                key_value = str(st.session_state.get(_api_value_dialog_key(dialog_nonce, "key")) or "").strip()
                if not key_value:
                    st.error("Key is required.")
                    return
                rows_key = f"{prefix}_{section}_rows"
                rows = st.session_state.get(rows_key)
                if not isinstance(rows, list):
                    rows = []
                duplicate = next(
                    (
                        row
                        for row in rows
                        if str(row.get("key") or "").strip() == key_value
                        and str(row.get("row_id") or "").strip() != row_id
                    ),
                    None,
                )
                if isinstance(duplicate, dict):
                    st.error(f"Duplicate key '{key_value}'.")
                    return
                if row_id:
                    updated = False
                    for row in rows:
                        if str(row.get("row_id") or "").strip() == row_id:
                            row["key"] = key_value
                            row["node"] = node
                            updated = True
                            break
                    if not updated:
                        rows.append({"row_id": row_id, "key": key_value, "node": node})
                else:
                    rows.append({"row_id": shared.new_ui_key(), "key": key_value, "node": node})
                st.session_state[rows_key] = rows
            elif target_kind == "formBody":
                key_value = str(st.session_state.get(_api_value_dialog_key(dialog_nonce, "key")) or "").strip()
                if not key_value:
                    st.error("Key is required.")
                    return
                node_error = _validate_api_value_node(
                    node,
                    allow_source=False,
                    field_label="Form field",
                    scalar_only=True,
                )
                if node_error:
                    st.error(node_error)
                    return
                rows_key = f"{prefix}_form_body_rows"
                rows = st.session_state.get(rows_key)
                if not isinstance(rows, list):
                    rows = []
                duplicate = next(
                    (
                        row
                        for row in rows
                        if str(row.get("key") or "").strip() == key_value
                        and str(row.get("row_id") or "").strip() != row_id
                    ),
                    None,
                )
                if isinstance(duplicate, dict):
                    st.error(f"Duplicate key '{key_value}'.")
                    return
                if row_id:
                    updated = False
                    for row in rows:
                        if str(row.get("row_id") or "").strip() == row_id:
                            row["key"] = key_value
                            row["node"] = node
                            updated = True
                            break
                    if not updated:
                        rows.append({"row_id": row_id, "key": key_value, "node": node})
                else:
                    rows.append({"row_id": shared.new_ui_key(), "key": key_value, "node": node})
                st.session_state[rows_key] = rows
            elif target_kind == "auth":
                st.session_state[f"{prefix}_auth_{auth_field}"] = node
            elif target_kind == "body":
                st.session_state[f"{prefix}_body_node"] = node

            _close_test_editor_api_value_dialog()
            st.rerun()


def _render_typed_command_editor(
    draft: dict,
    item: dict,
    current_operation: dict,
    operation_index: int,
    command_group: str,
    form_nonce: int,
    operation_ui_key: str,
) -> dict[str, object]:
    load_test_editor_context(force=False)
    load_database_connections(force=False)
    json_arrays = shared._safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    datasources = shared._safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = shared._safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    connections = shared._safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))

    key_prefix = "test_editor_command"
    shared._initialize_test_command_form(
        form_nonce,
        current_operation,
        json_arrays,
        brokers,
        key_prefix=key_prefix,
    )
    command_code = shared._render_test_command_form(
        form_nonce,
        command_group,
        json_arrays,
        datasources,
        brokers,
        connections,
        draft,
        item,
        stop_before_index=operation_index,
        key_prefix=key_prefix,
        show_comment=False,
    )
    return {
        "editor_kind": "typed",
        "key_prefix": key_prefix,
        "form_nonce": form_nonce,
        "command_group": command_group,
        "command_code": command_code,
    }


def _render_generic_command_editor(
    item: dict,
    current_operation: dict,
    operation_index: int,
    form_nonce: int,
    operation_ui_key: str,
) -> dict[str, object]:
    key_prefix = "test_editor_generic_command"
    description_key = shared._command_form_key(key_prefix, form_nonce, "description")
    cfg_key = shared._command_form_key(key_prefix, form_nonce, "cfg")
    if description_key not in st.session_state:
        st.session_state[description_key] = str(current_operation.get("description") or "")
    if cfg_key not in st.session_state:
        st.session_state[cfg_key] = json.dumps(
            shared._safe_dict(current_operation.get("configuration_json") or {}),
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
        "form_nonce": form_nonce,
        "description_key": description_key,
        "cfg_key": cfg_key,
    }


def _render_api_command_editor(
    item: dict,
    draft: dict,
    current_operation: dict,
    operation_index: int,
    operation_ui_key: str,
) -> dict[str, object]:
    cfg = shared._safe_dict(current_operation.get("configuration_json") or {})
    is_write = shared._normalize_command_code(cfg) == "writeApi"
    prefix = _api_editor_prefix(operation_ui_key)

    description_key = f"{prefix}_description"
    method_key = f"{prefix}_method"
    url_key = f"{prefix}_url"
    params_state_key = f"{prefix}_params_rows"
    path_state_key = f"{prefix}_path_rows"
    auth_state_key = f"{prefix}_auth"
    headers_state_key = f"{prefix}_headers_rows"
    body_type_key = f"{prefix}_body_type"
    body_node_key = f"{prefix}_body_node"
    form_body_rows_key = f"{prefix}_form_body_rows"
    timeout_key = f"{prefix}_timeout"
    result_target_key = f"{prefix}_result_target"

    if description_key not in st.session_state:
        st.session_state[description_key] = str(current_operation.get("description") or "")
    if method_key not in st.session_state:
        current_method = str(cfg.get("method") or "POST").upper()
        st.session_state[method_key] = (
            current_method if current_method in shared.HTTP_WRITE_METHOD_OPTIONS else "POST"
        )
    if url_key not in st.session_state:
        st.session_state[url_key] = str(cfg.get("url") or "")
    _ensure_api_kv_state(params_state_key, cfg.get("queryParams") or {})
    _ensure_api_kv_state(path_state_key, cfg.get("pathParams") or {})
    _ensure_api_kv_state(headers_state_key, cfg.get("headers") or {})
    _ensure_api_kv_state(
        form_body_rows_key,
        cfg.get("body") if str(cfg.get("bodyType") or "").strip() == "formUrlEncoded" else {},
    )
    if f"{prefix}_auth_type" not in st.session_state:
        auth_type = str(shared._safe_dict(cfg.get("authorization") or {}).get("type") or "none").strip()
        st.session_state[f"{prefix}_auth_type"] = (
            auth_type if auth_type in TEST_EDITOR_API_AUTH_TYPE_OPTIONS else "none"
        )
    for field_name in TEST_EDITOR_API_AUTH_FIELD_LABELS:
        auth_field_key = f"{prefix}_auth_{field_name}"
        if auth_field_key not in st.session_state:
            auth_node = shared._safe_dict(cfg.get("authorization") or {}).get(field_name)
            st.session_state[auth_field_key] = _coerce_api_value_node(auth_node) or {
                "kind": TEST_EDITOR_API_VALUE_MODE_LITERAL,
                "value": "",
            }
    if body_type_key not in st.session_state:
        st.session_state[body_type_key] = str(cfg.get("bodyType") or "json")
    if body_node_key not in st.session_state:
        st.session_state[body_node_key] = _coerce_api_value_node(cfg.get("body"))
    if timeout_key not in st.session_state:
        st.session_state[timeout_key] = max(shared._safe_int(cfg.get("timeoutSeconds"), 30), 1)
    if result_target_key not in st.session_state:
        st.session_state[result_target_key] = _api_result_target_label(cfg)

    runtime_values = _collect_visible_api_runtime_values(
        draft,
        item,
        stop_before_index=operation_index,
    )
    form_runtime_values = _collect_visible_api_form_runtime_values(
        draft,
        item,
        stop_before_index=operation_index,
    )
    body_sources = _collect_visible_api_body_sources(draft, item)
    api_tab_key = _api_editor_tab_state_key(operation_ui_key)
    tab_options = ["Params", "Path", "Auth", "Headers"]
    if is_write:
        tab_options.append("Body")
    tab_options.append("Response")

    if is_write:
        conf_cols = st.columns([2, 5], gap="small", vertical_alignment="center")
        with conf_cols[0]:
            st.selectbox("Method", options=shared.HTTP_WRITE_METHOD_OPTIONS, key=method_key)
        with conf_cols[1]:
            st.text_input("URL", key=url_key, placeholder="https://api.example.com/orders/{id}")
    else:
        st.text_input("URL", key=url_key, placeholder="https://api.example.com/orders/{id}")
    selected_api_tab = _select_persisted_tab(tab_options, api_tab_key, default="Params")

    if selected_api_tab == "Params":
        params_rows = st.session_state.get(params_state_key) or []
        _render_api_kv_section(item, operation_ui_key, "params", params_rows, runtime_values)
    elif selected_api_tab == "Path":
        path_rows = st.session_state.get(path_state_key) or []
        _render_api_kv_section(item, operation_ui_key, "path", path_rows, runtime_values)
    elif selected_api_tab == "Auth":
        _render_api_auth_section(item, operation_ui_key, prefix, runtime_values)
    elif selected_api_tab == "Headers":
        headers_rows = st.session_state.get(headers_state_key) or []
        _render_api_kv_section(item, operation_ui_key, "headers", headers_rows, runtime_values)
    elif selected_api_tab == "Body" and is_write:
        current_body_type = str(st.session_state.get(body_type_key) or "json").strip()
        if current_body_type == "formUrlEncoded":
            st.selectbox("Body type", options=shared.HTTP_BODY_TYPE_OPTIONS, key=body_type_key)
            form_body_rows = st.session_state.get(form_body_rows_key) or []
            _render_api_form_body_section(item, operation_ui_key, form_body_rows, form_runtime_values)
        else:
            _render_api_body_section(item, operation_ui_key, prefix, runtime_values, body_sources)
    elif selected_api_tab == "Response":
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
        "description_key": description_key,
        "method_key": method_key,
        "url_key": url_key,
        "params_state_key": params_state_key,
        "path_state_key": path_state_key,
        "auth_state_key": auth_state_key,
        "headers_state_key": headers_state_key,
        "body_type_key": body_type_key,
        "body_node_key": body_node_key,
        "form_body_rows_key": form_body_rows_key,
        "timeout_key": timeout_key,
        "result_target_key": result_target_key,
    }


def _save_test_editor_command(
    draft: dict,
    item: dict,
    current_operation: dict,
    operation_index: int,
    operation_ui_key: str,
    editor_state: dict[str, object],
) -> bool:
    _remember_selected_command_by_operation(current_operation, operation_index)
    editor_kind = str(editor_state.get("editor_kind") or "").strip()
    if editor_kind == "typed":
        form_nonce = int(editor_state.get("form_nonce") or 0)
        key_prefix = str(editor_state.get("key_prefix") or "test_editor_command")
        command_group = str(editor_state.get("command_group") or "").strip()
        command_code = editor_state.get("command_code")
        updated_operation, validation_error = shared._build_test_command_draft_with_prefix(
            form_nonce,
            command_code,
            key_prefix=key_prefix,
        )
        if validation_error:
            st.error(validation_error)
            return False
        if _persist_test_editor_operation_update(
            item,
            operation_index,
            current_operation,
            updated_operation or {},
            success_message=shared._command_group_updated_feedback(command_group),
        ):
            _clear_command_form_state(key_prefix, form_nonce)
            return True
        return False

    if editor_kind == "generic":
        cfg_key = str(editor_state.get("cfg_key") or "")
        description_key = str(editor_state.get("description_key") or "")
        form_nonce = int(editor_state.get("form_nonce") or 0)
        key_prefix = str(editor_state.get("key_prefix") or "test_editor_generic_command")
        try:
            configuration_json = json.loads(str(st.session_state.get(cfg_key) or "").strip() or "{}")
        except json.JSONDecodeError as exc:
            st.error(f"Configuration JSON non valido: {str(exc)}")
            return False
        if not isinstance(configuration_json, dict):
            st.error("Configuration JSON deve essere un oggetto JSON.")
            return False
        updated_operation = {
            "description": str(st.session_state.get(description_key) or "").strip(),
            "operation_type": shared._normalize_command_code(configuration_json)
            or str(current_operation.get("operation_type") or ""),
            "configuration_json": configuration_json,
        }
        if _persist_test_editor_operation_update(
            item,
            operation_index,
            current_operation,
            updated_operation,
            success_message="Command updated.",
        ):
            _clear_command_form_state(key_prefix, form_nonce)
            return True
        return False

    if editor_kind == "api":
        url_key = str(editor_state.get("url_key") or "")
        params_rows = st.session_state.get(str(editor_state.get("params_state_key") or ""), [])
        path_rows = st.session_state.get(str(editor_state.get("path_state_key") or ""), [])
        is_write = bool(editor_state.get("is_write"))
        body_type_key = str(editor_state.get("body_type_key") or "")
        body_node_key = str(editor_state.get("body_node_key") or "")
        form_body_rows_key = str(editor_state.get("form_body_rows_key") or "")
        method_key = str(editor_state.get("method_key") or "")
        timeout_key = str(editor_state.get("timeout_key") or "")
        result_target_key = str(editor_state.get("result_target_key") or "")
        description_key = str(editor_state.get("description_key") or "")
        prefix = str(editor_state.get("prefix") or "")
        headers_rows = st.session_state.get(str(editor_state.get("headers_state_key") or ""), [])

        url = str(st.session_state.get(url_key) or "").strip()
        if not url:
            st.error("Il campo URL e' obbligatorio.")
            return False

        query_params, params_error = _collect_api_kv_payload(params_rows, "Params")
        if params_error:
            st.error(params_error)
            return False
        path_params, path_error = _collect_api_kv_payload(path_rows, "Path")
        if path_error:
            st.error(path_error)
            return False
        authorization, auth_error = _collect_api_auth_payload(prefix)
        if auth_error:
            st.error(auth_error)
            return False
        headers, headers_error = _collect_api_kv_payload(headers_rows, "Headers")
        if headers_error:
            st.error(headers_error)
            return False

        updated_cfg: dict[str, object]
        if is_write:
            body_type = str(st.session_state.get(body_type_key) or "json").strip()
            body_payload = None
            if body_type == "formUrlEncoded":
                form_body_rows = st.session_state.get(form_body_rows_key, [])
                body_payload, body_error = _collect_api_form_body_payload(form_body_rows, "Body")
                if body_error:
                    st.error(body_error)
                    return False
            else:
                body_payload = _coerce_api_value_node(st.session_state.get(body_node_key))
                if body_payload is not None:
                    body_error = _validate_api_value_node(
                        body_payload,
                        allow_source=True,
                        field_label="Body",
                    )
                    if body_error:
                        st.error(body_error)
                        return False
            updated_cfg = {
                "commandCode": "writeApi",
                "commandType": "action",
                "method": str(st.session_state.get(method_key) or "POST").strip().upper(),
                "url": url,
                "bodyType": body_type,
                "timeoutSeconds": max(shared._safe_int(st.session_state.get(timeout_key), 30), 1),
            }
            if body_payload is not None:
                updated_cfg["body"] = body_payload
        else:
            updated_cfg = {
                "commandCode": "readApi",
                "commandType": "action",
                "url": url,
                "timeoutSeconds": max(shared._safe_int(st.session_state.get(timeout_key), 30), 1),
            }

        result_target = _normalize_api_result_target_input(st.session_state.get(result_target_key))
        if query_params:
            updated_cfg["queryParams"] = query_params
        if path_params:
            updated_cfg["pathParams"] = path_params
        updated_cfg["authorization"] = authorization
        if headers:
            updated_cfg["headers"] = headers
        if result_target:
            updated_cfg["result_target"] = result_target

        updated_operation = {
            "description": str(st.session_state.get(description_key) or "").strip(),
            "operation_type": str(current_operation.get("operation_type") or updated_cfg["commandCode"]),
            "configuration_json": updated_cfg,
        }
        if _persist_test_editor_operation_update(
            item,
            operation_index,
            current_operation,
            updated_operation,
            success_message="Command updated.",
            force_persist=True,
        ):
            _clear_state_prefix(prefix)
            return True
        return False

    st.error("Unsupported command editor.")
    return False


def _reset_test_editor_command(editor_state: dict[str, object]) -> None:
    editor_kind = str(editor_state.get("editor_kind") or "").strip()
    if editor_kind == "api":
        _clear_state_prefix(str(editor_state.get("prefix") or ""))
        return
    _clear_command_form_state(
        str(editor_state.get("key_prefix") or ""),
        int(editor_state.get("form_nonce") or 0),
    )


def _render_test_editor_command_list_card(
    item: dict,
    operation: dict,
    operation_ui_key: str,
    *,
    is_selected: bool,
) -> None:
    select_label = _strip_command_markdown(_build_test_editor_command_list_label(operation)) or "Command"

    with st.container():
        row_cols = st.columns([7, 1], gap="small", vertical_alignment="center")
        with row_cols[0]:
            if st.button(
                select_label,
                key=f"test_editor_select_command_{operation_ui_key}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
            ):
                _set_selected_test_editor_command(
                    operation_ui_key,
                    order=shared._safe_int(operation.get("order"), 0) or None,
                )
                st.rerun()
        with row_cols[1]:
            if st.button(
                "",
                key=f"test_editor_reorder_action_{operation_ui_key}",
                icon=":material/unfold_more:",
                help="Reorder commands",
                type="tertiary",
                use_container_width=True,
            ):
                shared._open_reorder_command_dialog_for_item(item)
                st.rerun()


def _render_selected_test_editor_command(
    item: dict,
    draft: dict,
    operation_ui_key: str,
) -> None:
    operation_index, current_operation = shared._find_operation_by_ui_key(item, operation_ui_key)
    if not isinstance(current_operation, dict):
        _clear_selected_test_editor_command()
        st.info("Select a command from the list.")
        return

    command_group = shared._resolve_test_command_group(current_operation.get("configuration_json"))
    command_code = shared._normalize_command_code(current_operation.get("configuration_json"))
    form_nonce = operation_index

    with st.container(border=True):
        st.markdown(_build_test_editor_command_label(current_operation))
        st.divider()

        if command_code in {"readApi", "writeApi"}:
            editor_state = _render_api_command_editor(
                item,
                draft,
                current_operation,
                operation_index,
                operation_ui_key,
            )
        elif command_group and command_group != "fallback-json":
            editor_state = _render_typed_command_editor(
                draft,
                item,
                current_operation,
                operation_index,
                command_group,
                form_nonce,
                operation_ui_key,
            )
        else:
            editor_state = _render_generic_command_editor(
                item,
                current_operation,
                operation_index,
                form_nonce,
                operation_ui_key,
            )

    action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"test_editor_command_detail_save_{operation_ui_key}",
            icon=":material/save:",
            use_container_width=True,
        ):
            if _save_test_editor_command(
                draft,
                item,
                current_operation,
                operation_index,
                operation_ui_key,
                editor_state,
            ):
                st.rerun()
    with action_cols[1]:
        if st.button(
            "Reset",
            key=f"test_editor_command_detail_reset_{operation_ui_key}",
            icon=":material/refresh:",
            use_container_width=True,
        ):
            _reset_test_editor_command(editor_state)
            st.rerun()
    with action_cols[2]:
        if st.button(
            "Delete",
            key=f"test_editor_command_detail_delete_{operation_ui_key}",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            _delete_test_editor_operation(item, operation_ui_key)


def _render_test_editor_source_card(
    source: dict,
    item: dict,
    *,
    perimeter_return_page: str,
    perimeter_return_label: str,
) -> None:
    source_code = str(source.get("sourceCode") or "-").strip() or "-"
    source_type = str(source.get("sourceType") or "").strip()
    preview_visible = shared._is_source_preview_visible(item, source)
    details = (
        shared._resolve_dataset_source_details(source)
        if source_type == "dataset"
        else shared._resolve_json_array_source_details(source)
    )
    card_label = (
        f"{source_code} - {str(details.get('description') or '').strip()} [{shared._source_type_label(source_type)}]"
        if str(details.get("description") or "").strip() and str(details.get("description") or "").strip() != source_code
        else f"{source_code} [{shared._source_type_label(source_type)}]"
    )

    with st.container(border=True):
        st.markdown(f"**{card_label}**")

        if source_type == "dataset":
            st.write(f"**Database:** {details.get('connection_label') or '-'}")
            st.write(f"**Schema:** {details.get('schema') or '-'}")
            st.write(f"**Table/View:** {details.get('object_label') or '-'}")
            action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
            with action_cols[0]:
                if st.button(
                    "Hide preview" if preview_visible else "Preview",
                    key=f"suite_editor_source_preview_btn_{shared._source_state_suffix(item.get('_ui_key'), source_code)}",
                    icon=":material/visibility_off:" if preview_visible else ":material/visibility:",
                    type="secondary",
                    use_container_width=True,
                ):
                    shared._toggle_source_preview(item, source)
                    st.rerun()
            with action_cols[1]:
                if st.button(
                    "Perimeter",
                    key=f"suite_editor_source_perimeter_btn_{shared._source_state_suffix(item.get('_ui_key'), source_code)}",
                    icon=":material/filter_alt:",
                    type="secondary",
                    use_container_width=True,
                ):
                    shared.open_test_source_perimeter_editor(
                        item_ui_key=str(item.get("_ui_key") or ""),
                        source_code=source_code,
                        return_page=perimeter_return_page,
                        return_label=perimeter_return_label,
                    )
                    st.switch_page(shared.DATASET_PERIMETER_EDITOR_PAGE_PATH)
                    st.rerun()
            with action_cols[2]:
                if st.button(
                    "Delete",
                    key=f"suite_editor_source_delete_btn_{shared._source_state_suffix(item.get('_ui_key'), source_code)}",
                    icon=":material/delete:",
                    type="secondary",
                    use_container_width=True,
                ):
                    original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
                    if shared._delete_source_by_code(item, source_code):
                        try:
                            shared._persist_current_draft(success_message="Source removed.", rerun=False)
                        except Exception as exc:
                            st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                            shared._render_persist_error(exc)
                            return
                        st.rerun()
            if preview_visible:
                shared._render_source_preview_content(source)
            return

        st.write(f"**Json Array:** {details.get('description') or '-'}")
        if str(details.get("code") or "").strip():
            st.write(f"**Code:** {details.get('code')}")
        st.write(f"**Items:** {details.get('items_count') or 0}")
        action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
        with action_cols[0]:
            if st.button(
                "Hide preview" if preview_visible else "Preview",
                key=f"suite_editor_json_array_preview_btn_{shared._source_state_suffix(item.get('_ui_key'), source_code)}",
                icon=":material/visibility_off:" if preview_visible else ":material/visibility:",
                type="secondary",
                use_container_width=True,
            ):
                shared._toggle_source_preview(item, source)
                st.rerun()
        with action_cols[1]:
            if st.button(
                "Delete",
                key=f"suite_editor_json_array_delete_btn_{shared._source_state_suffix(item.get('_ui_key'), source_code)}",
                icon=":material/delete:",
                type="secondary",
                use_container_width=True,
            ):
                original_draft = deepcopy(st.session_state.get(TEST_SUITE_DRAFT_KEY, {}))
                if shared._delete_source_by_code(item, source_code):
                    try:
                        shared._persist_current_draft(success_message="Source removed.", rerun=False)
                    except Exception as exc:
                        st.session_state[TEST_SUITE_DRAFT_KEY] = original_draft
                        shared._render_persist_error(exc)
                        return
                    st.rerun()
        if preview_visible:
            shared._render_source_preview_content(source)


def _render_test_editor_sources_summary(
    item: dict | None,
    *,
    perimeter_return_page: str,
    perimeter_return_label: str,
) -> None:
    sources = shared._source_list(item)
    if not sources:
        st.caption("No data source configured.")
        return
    for source in sources:
        _render_test_editor_source_card(
            source,
            item or {},
            perimeter_return_page=perimeter_return_page,
            perimeter_return_label=perimeter_return_label,
        )


def _render_test_editor_datasources_section(current_test: dict) -> None:
    _render_test_editor_sources_summary(
        current_test,
        perimeter_return_page=shared.TEST_EDITOR_PAGE_PATH,
        perimeter_return_label="Back to test",
    )

    st.divider()

    add_cols = st.columns([3, 1, 3], gap="small", vertical_alignment="center")
    with add_cols[1]:
        if st.button(
            "+ Source",
            key=f"suite_editor_add_test_source_{current_test.get('_ui_key')}",
            icon=":material/add:",
            use_container_width=True,
        ):
            shared._open_add_source_dialog_for_item(str(current_test.get("_ui_key") or ""))
            st.rerun()


def _render_test_editor_add_command_popover(current_test: dict) -> None:
    current_test_ui_key = str(current_test.get("_ui_key") or "").strip()
    if not current_test_ui_key:
        return

    popover = getattr(st, "popover", None)
    if callable(popover):
        container = popover("+ Add command")
    else:
        expander = getattr(st, "expander", None)
        if callable(expander):
            container = expander("+ Add command")
        else:
            container = st.container()
            st.caption("+ Add command")

    with container:
        if st.button(
            "Action",
            key=f"suite_editor_add_test_action_{current_test_ui_key}",
            type="tertiary",
            icon=":material/terminal:",
            use_container_width=True,
        ):
            shared._open_test_command_dialog_for_item(current_test_ui_key, "action")
            st.rerun()
        if st.button(
            "Variable",
            key=f"suite_editor_add_test_constant_{current_test_ui_key}",
            type="tertiary",
            icon=":material/function:",
            use_container_width=True,
        ):
            shared._open_test_command_dialog_for_item(current_test_ui_key, "constant")
            st.rerun()
        if st.button(
            "Assert",
            key=f"suite_editor_add_test_assert_{current_test_ui_key}",
            type="tertiary",
            icon=":material/verified:",
            use_container_width=True,
        ):
            shared._open_test_command_dialog_for_item(current_test_ui_key, "assert")
            st.rerun()


def _render_test_editor_commands_section(
    current_test: dict,
    draft: dict,
) -> None:
    selected_command_ui_key = _resolve_selected_test_editor_command(current_test)
    operation_entries = _test_editor_operation_entries(current_test)
    list_col, detail_col = st.columns([3, 8], gap="medium", vertical_alignment="top")

    with list_col:
        with st.container(border=True):
            if operation_entries:
                for _, operation, operation_ui_key in operation_entries:
                    _render_test_editor_command_list_card(
                        current_test,
                        operation,
                        operation_ui_key,
                        is_selected=selected_command_ui_key == operation_ui_key,
                    )
            else:
                st.caption("Nessun command configurato.")

        _render_test_editor_add_command_popover(current_test)

    with detail_col:
        if not selected_command_ui_key:
            st.info("Select a command from the list.")
            return
        _render_selected_test_editor_command(current_test, draft, selected_command_ui_key)


def _render_test_editor_item(test: dict, index: int, draft: dict, execution_state: dict):
    current_test = shared._ensure_test_item(test, index)
    current_test_id = str(current_test.get("id") or "").strip()
    current_test_ui_key = str(current_test.get("_ui_key") or "").strip()
    selected_suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "").strip()
    can_run_single_test = bool(current_test_id and selected_suite_id)

    header_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
    with header_cols[1]:
        if st.button(
            "Execute test",
            key=f"suite_editor_run_test_{current_test.get('_ui_key')}",
            icon=":material/play_arrow:",
            help="Run this test"
            if can_run_single_test
            else "Save suite before running this test",
            type="primary",
            disabled=not can_run_single_test,
            use_container_width=True,
        ):
            response = execute_test_by_id(selected_suite_id, current_test_id)
            execution_id = str(response.get("execution_id") or "").strip()
            if execution_id:
                st.session_state[TEST_SUITE_LAST_EXECUTION_ID_KEY] = execution_id
                st.session_state[shared.PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY] = execution_id
                register_execution_listener(execution_id, selected_suite_id)
                st.rerun()

    selected_section_tab = _select_persisted_tab(
        [TEST_EDITOR_SECTION_COMMANDS_TAB, TEST_EDITOR_SECTION_DATASOURCES_TAB],
        f"{TEST_EDITOR_SECTION_TAB_KEY}_{current_test_ui_key}",
        default=TEST_EDITOR_SECTION_COMMANDS_TAB,
    )
    if selected_section_tab == TEST_EDITOR_SECTION_COMMANDS_TAB:
        _render_test_editor_commands_section(current_test, draft)
    elif selected_section_tab == TEST_EDITOR_SECTION_DATASOURCES_TAB:
        _render_test_editor_datasources_section(current_test)


@st.dialog("Add test command", width="large")
def _render_add_test_command_dialog(draft: dict):
    dialog_nonce = int(st.session_state.get(shared.TEST_ADD_COMMAND_DIALOG_NONCE_KEY, 0))
    test_ui_key = str(st.session_state.get(shared.TEST_ADD_COMMAND_DIALOG_TARGET_UI_KEY) or "").strip()
    command_group = str(st.session_state.get(shared.TEST_ADD_COMMAND_DIALOG_GROUP_KEY) or "constant").strip().lower()
    test_item = shared._find_test_by_ui_key(draft, test_ui_key)
    command_intro_label = shared._command_group_intro_label(command_group, mode="add")
    primary_action_label = shared._command_group_primary_action_label(command_group, mode="add")

    if not isinstance(test_item, dict):
        st.error("Test di destinazione non trovato.")
        if st.button("Cancel", key=f"suite_test_add_command_missing_cancel_{dialog_nonce}", use_container_width=True):
            shared._close_test_command_dialog()
            st.rerun()
        return

    load_test_editor_context(force=False)
    load_database_connections(force=False)

    json_arrays = shared._safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
    datasources = shared._safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
    brokers = shared._safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
    connections = shared._safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))

    st.markdown(f"**{command_intro_label}**")
    command_ui_code = shared._render_test_command_form(
        dialog_nonce,
        command_group,
        json_arrays,
        datasources,
        brokers,
        connections,
        draft,
        test_item,
        stop_before_index=len(shared._operation_list(test_item)),
        key_prefix="suite_test_command",
    )

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            primary_action_label,
            key=f"suite_add_test_command_save_{dialog_nonce}",
            icon=":material/add_circle:",
            type="secondary",
            use_container_width=True,
        ):
            operation_item, validation_error = shared._build_test_command_draft_with_prefix(
                dialog_nonce,
                command_ui_code,
                key_prefix="suite_test_command",
            )
            if validation_error:
                st.error(validation_error)
                return
            shared.append_operation_to_test(test_item, operation_item or {})
            shared._close_test_command_dialog()
            st.session_state[SUITE_FEEDBACK_KEY] = shared._command_group_added_feedback(command_group)
            shared._persist_changes()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"suite_add_test_command_cancel_{dialog_nonce}",
            use_container_width=True,
        ):
            shared._close_test_command_dialog()
            st.rerun()
