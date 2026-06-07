import json
from decimal import Decimal
from uuid import uuid4

import streamlit as st

from database_connections.services.data_loader_service import (
    DATABASE_CONNECTIONS_KEY,
    load_database_connections,
)
from elaborations_shared.components.auth_editor import (
    collect_auth_editor_value,
    initialize_auth_editor_state,
    render_auth_editor,
)
from elaborations_shared.services.data_loader_service import (
    load_test_editor_context,
    load_test_editor_queues_for_broker,
)
from elaborations_shared.components.kv_editor import (
    ensure_kv_editor_state,
    render_kv_rows_container,
    rows_to_dict,
)
from elaborations_shared.services.state_keys import (
    ADD_TEST_OPERATION_DIALOG_NONCE_KEY,
    ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY,
    SUITE_FEEDBACK_KEY,
    TEST_EDITOR_BROKERS_KEY,
    TEST_EDITOR_DATABASE_DATASOURCES_KEY,
    TEST_EDITOR_JSON_ARRAYS_KEY,
)

OPERATION_TYPE_DATA = "data"
OPERATION_TYPE_DATA_FROM_JSON_ARRAY = "data-from-json-array"
OPERATION_TYPE_DATA_FROM_DB = "data-from-db"
OPERATION_TYPE_DATA_FROM_QUEUE = "data-from-queue"
OPERATION_TYPE_SLEEP = "sleep"
OPERATION_TYPE_PUBLISH = "publish"
OPERATION_TYPE_SAVE_INTERNAL_DB = "save-internal-db"
OPERATION_TYPE_SAVE_EXTERNAL_DB = "save-external-db"
OPERATION_TYPE_ASSERT = "assert"
OPERATION_TYPE_RUN_SUITE = "run-suite"
OPERATION_TYPE_SET_VAR = "set-var"
OPERATION_TYPE_READ_API = "read-api"
OPERATION_TYPE_WRITE_API = "write-api"
OPERATION_TYPE_SET_RESPONSE_STATUS = "set-response-status"
OPERATION_TYPE_SET_RESPONSE_HEADER = "set-response-header"
OPERATION_TYPE_SET_RESPONSE_BODY = "set-response-body"
OPERATION_TYPE_BUILD_RESPONSE_FROM_TEMPLATE = "build-response-from-template"
OPERATION_TYPE_OPTIONS = [
    OPERATION_TYPE_DATA,
    OPERATION_TYPE_DATA_FROM_JSON_ARRAY,
    OPERATION_TYPE_DATA_FROM_DB,
    OPERATION_TYPE_DATA_FROM_QUEUE,
    OPERATION_TYPE_SLEEP,
    OPERATION_TYPE_PUBLISH,
    OPERATION_TYPE_SAVE_INTERNAL_DB,
    OPERATION_TYPE_SAVE_EXTERNAL_DB,
    OPERATION_TYPE_ASSERT,
    OPERATION_TYPE_RUN_SUITE,
    OPERATION_TYPE_SET_VAR,
    OPERATION_TYPE_READ_API,
    OPERATION_TYPE_WRITE_API,
    OPERATION_TYPE_SET_RESPONSE_STATUS,
    OPERATION_TYPE_SET_RESPONSE_HEADER,
    OPERATION_TYPE_SET_RESPONSE_BODY,
    OPERATION_TYPE_BUILD_RESPONSE_FROM_TEMPLATE,
]
ASSERT_OBJECT_TYPE_JSON_DATA = "json-data"
ASSERT_OBJECT_TYPE_OPTIONS = [ASSERT_OBJECT_TYPE_JSON_DATA]
ASSERT_TYPE_NOT_EMPTY = "not-empty"
ASSERT_TYPE_EMPTY = "empty"
ASSERT_TYPE_SCHEMA_VALIDATION = "schema-validation"
ASSERT_TYPE_CONTAINS = "contains"
ASSERT_TYPE_JSON_ARRAY_EQUALS = "json-array-equals"
ASSERT_TYPE_EQUALS = "equals"
ASSERT_TYPE_OPTIONS = [
    ASSERT_TYPE_NOT_EMPTY,
    ASSERT_TYPE_EMPTY,
    ASSERT_TYPE_SCHEMA_VALIDATION,
    ASSERT_TYPE_CONTAINS,
    ASSERT_TYPE_JSON_ARRAY_EQUALS,
    ASSERT_TYPE_EQUALS,
]
OPERATION_STATUS_SUCCESS = "success"
OPERATION_STATUS_ERROR = "error"
OPERATION_STATUS_RUNNING = "running"
OPERATION_STATUS_IDLE = "idle"


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return int(float(stripped))
        except ValueError:
            return default
    return default


def _new_ui_key() -> str:
    return uuid4().hex[:10]


def _operation_type_label(operation_type: str) -> str:
    labels = {
        OPERATION_TYPE_DATA: "input / data",
        OPERATION_TYPE_DATA_FROM_JSON_ARRAY: "input / data-from-json-array",
        OPERATION_TYPE_DATA_FROM_DB: "input / data-from-db",
        OPERATION_TYPE_DATA_FROM_QUEUE: "input / data-from-queue",
        OPERATION_TYPE_SLEEP: "utility / sleep",
        OPERATION_TYPE_PUBLISH: "publish",
        OPERATION_TYPE_SAVE_INTERNAL_DB: "save-internal-db",
        OPERATION_TYPE_SAVE_EXTERNAL_DB: "save-external-db",
        OPERATION_TYPE_ASSERT: "assert",
        OPERATION_TYPE_RUN_SUITE: "run-suite",
        OPERATION_TYPE_SET_VAR: "set-var",
        OPERATION_TYPE_READ_API: "http / read-api",
        OPERATION_TYPE_WRITE_API: "http / write-api",
        OPERATION_TYPE_SET_RESPONSE_STATUS: "mock-response / set-status",
        OPERATION_TYPE_SET_RESPONSE_HEADER: "mock-response / set-header",
        OPERATION_TYPE_SET_RESPONSE_BODY: "mock-response / set-body",
        OPERATION_TYPE_BUILD_RESPONSE_FROM_TEMPLATE: "mock-response / build-from-template",
    }
    return labels.get(operation_type, operation_type or "-")


def _broker_label(broker_item: dict) -> str:
    return str(broker_item.get("description") or broker_item.get("id") or "-")


def _json_array_label(json_array_item: dict) -> str:
    return str(json_array_item.get("description") or json_array_item.get("id") or "-")


def _assert_object_type_label(object_type: str) -> str:
    labels = {
        ASSERT_OBJECT_TYPE_JSON_DATA: "json-data",
    }
    return labels.get(object_type, object_type or "-")


def _assert_type_label(assert_type: str) -> str:
    labels = {
        ASSERT_TYPE_NOT_EMPTY: "not-empty",
        ASSERT_TYPE_EMPTY: "empty",
        ASSERT_TYPE_SCHEMA_VALIDATION: "schema-validation",
        ASSERT_TYPE_CONTAINS: "contains",
        ASSERT_TYPE_JSON_ARRAY_EQUALS: "json-array-equals",
        ASSERT_TYPE_EQUALS: "equals",
    }
    return labels.get(assert_type, assert_type or "-")


def _queue_label(queue_item: dict) -> str:
    return str(queue_item.get("description") or queue_item.get("id") or "-")


def _normalize_select_key(key: str, options: list[str]):
    if not key:
        return
    if not options:
        st.session_state[key] = ""
        return
    current_value = str(st.session_state.get(key) or "")
    if current_value not in options:
        st.session_state[key] = options[0]


def _pretty_json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True)


def _example_placeholder(example_value: str) -> str:
    return f"Example: {example_value}"


def _safe_dict(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _safe_list(value: object) -> list[dict]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _map_by_id(items: list[dict]) -> dict[str, dict]:
    return {str(item.get("id")): item for item in items if item.get("id")}


def _resolve_configuration_value(configuration_json: dict, *keys: str):
    for key in keys:
        value = configuration_json.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _normalize_token(value: object) -> str:
    return str(value or "").strip().replace("_", "-").lower()


def _normalize_operation_type(value: object) -> str:
    normalized = _normalize_token(value)
    mapping = {
        "readapi": OPERATION_TYPE_READ_API,
        "read-api": OPERATION_TYPE_READ_API,
        "writeapi": OPERATION_TYPE_WRITE_API,
        "write-api": OPERATION_TYPE_WRITE_API,
    }
    return mapping.get(normalized, normalized)


def _parse_compare_keys(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item or "").strip() for item in value if str(item or "").strip()]
    raw = str(value or "").replace(";", ",").replace("\n", ",")
    return [item.strip() for item in raw.split(",") if item and item.strip()]


def _parse_json_dict(
    value: object,
    *,
    field_label: str = "Json schema",
    allow_empty: bool = False,
) -> tuple[dict | None, str | None]:
    if isinstance(value, dict):
        return value, None
    raw_value = str(value or "").strip()
    if not raw_value:
        if allow_empty:
            return {}, None
        return None, f"Il campo {field_label} e' obbligatorio."
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        return None, f"{field_label} non valido: {str(exc)}"
    if not isinstance(parsed, dict):
        return None, f"{field_label} deve essere un oggetto JSON."
    return parsed, None


def _parse_json_value(value: object) -> tuple[object | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, (dict, list, int, float, bool)):
        return value, None
    raw_value = str(value or "").strip()
    if not raw_value:
        return None, None
    try:
        return json.loads(raw_value), None
    except json.JSONDecodeError:
        return raw_value, None


def _normalize_context_target_path(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("$."):
        return raw
    if raw.startswith("$"):
        return f"$.{raw[1:].lstrip('.')}"
    return f"$.{raw.lstrip('.')}"


def _connection_label(connection_item: dict) -> str:
    return str(connection_item.get("description") or connection_item.get("id") or "-")


def _resolve_operation_target_summary(operation_item: dict) -> tuple[str, str]:
    configuration_json = _safe_dict(operation_item.get("configuration_json") or {})
    target_path = str(
        _resolve_configuration_value(configuration_json, "target", "targetPath") or ""
    ).strip()
    if target_path:
        return "Target", target_path

    result_target_path = str(
        _resolve_configuration_value(configuration_json, "result_target", "resultTarget") or ""
    ).strip()
    if result_target_path:
        return "Result target", result_target_path

    return "Target", "-"


def _reload_test_operations(suite_test: dict):
    operations = suite_test.get("operations")
    if not isinstance(operations, list):
        return
    indexed_operations = list(enumerate(operations))
    indexed_operations.sort(
        key=lambda item: (_safe_int(item[1].get("order"), item[0] + 1), item[0])
    )
    suite_test["operations"] = [operation for _, operation in indexed_operations]


def _persist_suite_changes(persist_suite_changes_fn=None):
    if callable(persist_suite_changes_fn):
        persist_suite_changes_fn()
        return
    st.rerun()


def _find_queue_and_broker_by_queue_id(
    queue_id: str,
    brokers_by_id: dict[str, dict],
) -> tuple[dict, dict]:
    queue_id_value = str(queue_id or "").strip()
    if not queue_id_value:
        return {}, {}

    def _find_queue_in_items(items: list[dict], target_queue_id: str) -> dict:
        return next(
            (
                item
                for item in items
                if str(item.get("id") or "").strip() == target_queue_id
            ),
            {},
        )

    for current_broker_id, broker_item in brokers_by_id.items():
        queues = load_test_editor_queues_for_broker(str(current_broker_id), force=False)
        queue_item = _find_queue_in_items(queues, queue_id_value)
        if queue_item:
            return queue_item, broker_item

    return {}, {}


def _render_operation_details(operation_item: dict):
    if not isinstance(operation_item, dict):
        st.caption("Operation non trovata nel catalogo.")
        return

    operation_type = _normalize_operation_type(
        operation_item.get("operation_type")
        or (operation_item.get("configuration_json") or {}).get("operationType")
        or (operation_item.get("configuration_json") or {}).get("commandCode")
    )
    configuration_json = _safe_dict(operation_item.get("configuration_json") or {})
    target_path = str(
        _resolve_configuration_value(configuration_json, "target", "targetPath") or ""
    ).strip()
    result_target_path = str(
        _resolve_configuration_value(configuration_json, "result_target", "resultTarget") or ""
    ).strip()
    if target_path:
        st.write(f"Target: {target_path}")
    if result_target_path:
        st.write(f"Result target: {result_target_path}")

    if operation_type == OPERATION_TYPE_DATA:
        data_payload = configuration_json.get("data") or []
        st.markdown("**Inline data**")
        st.json(data_payload, expanded=False)
        return

    if operation_type == OPERATION_TYPE_DATA_FROM_JSON_ARRAY:
        load_test_editor_context(force=False)
        json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
        json_arrays_by_id = _map_by_id(json_arrays)
        json_array_id = str(
            _resolve_configuration_value(configuration_json, "json_array_id", "jsonArrayId") or ""
        ).strip()
        json_array_item = json_arrays_by_id.get(json_array_id, {})
        label = _json_array_label(json_array_item)
        if label == "-" and json_array_id:
            label = json_array_id
        st.write(f"Json array: {label}")
        return

    if operation_type == OPERATION_TYPE_DATA_FROM_DB:
        load_test_editor_context(force=False)
        datasources = _safe_list(st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, []))
        datasources_by_id = _map_by_id(datasources)
        datasource_id = str(
            _resolve_configuration_value(configuration_json, "dataset_id", "datasetId", "data_source_id")
            or ""
        ).strip()
        datasource_item = datasources_by_id.get(datasource_id, {})
        label = str(datasource_item.get("description") or datasource_id or "-")
        st.write(f"Dataset: {label}")
        return

    if operation_type == OPERATION_TYPE_DATA_FROM_QUEUE:
        load_test_editor_context(force=False)
        brokers = _safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
        brokers_by_id = _map_by_id(brokers)
        queue_id = str(
            _resolve_configuration_value(configuration_json, "queue_id", "queueId") or ""
        ).strip()
        queue_item, broker_item = _find_queue_and_broker_by_queue_id(queue_id, brokers_by_id)
        st.write(f"Queue: {_queue_label(queue_item) if queue_item else queue_id or '-'}")
        st.write(f"Broker: {_broker_label(broker_item) if broker_item else '-'}")
        st.write(
            "Retry / wait / max: "
            f"{configuration_json.get('retry', 3)} / "
            f"{configuration_json.get('wait_time_seconds', 20)} / "
            f"{configuration_json.get('max_messages', 1000)}"
        )
        return

    if operation_type == OPERATION_TYPE_SLEEP:
        st.write(f"Duration: {configuration_json.get('duration', '-')}")
        return

    if operation_type == OPERATION_TYPE_PUBLISH:
        load_test_editor_context(force=False)
        brokers = _safe_list(st.session_state.get(TEST_EDITOR_BROKERS_KEY, []))
        brokers_by_id = _map_by_id(brokers)
        queue_id = str(
            _resolve_configuration_value(configuration_json, "queue_id", "queueId") or ""
        ).strip()
        queue_item, broker_item = _find_queue_and_broker_by_queue_id(queue_id, brokers_by_id)
        queue_label = str(queue_item.get("description") or queue_id or "-")
        broker_label = str(broker_item.get("description") or broker_item.get("id") or "-")
        st.write(f"Queue: {queue_label} [ {broker_label} ]")
        return

    if operation_type == OPERATION_TYPE_SAVE_INTERNAL_DB:
        table_name = str(
            _resolve_configuration_value(configuration_json, "table_name", "tableName") or "-"
        ).strip()
        st.write(f"Table: {table_name or '-'}")
        return

    if operation_type == OPERATION_TYPE_SAVE_EXTERNAL_DB:
        load_database_connections(force=False)
        connections = _safe_list(st.session_state.get(DATABASE_CONNECTIONS_KEY, []))
        connections_by_id = _map_by_id(connections)
        connection_id = str(
            _resolve_configuration_value(
                configuration_json,
                "connection_id",
                "connectionId",
                "dataset_id",
            )
            or ""
        ).strip()
        connection_item = connections_by_id.get(connection_id, {})
        table_name = str(
            _resolve_configuration_value(configuration_json, "table_name", "tableName") or "-"
        ).strip()
        connection_label = _connection_label(connection_item)
        if connection_label == "-" and connection_id:
            connection_label = connection_id
        st.write(f"Connection: {connection_label}")
        st.write(f"Table: {table_name or '-'}")
        return

    if operation_type == OPERATION_TYPE_ASSERT:
        load_test_editor_context(force=False)
        json_arrays = _safe_list(st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, []))
        json_arrays_by_id = _map_by_id(json_arrays)

        evaluated_object_type = _normalize_token(
            _resolve_configuration_value(
                configuration_json,
                "evaluated_object_type",
                "evaluetedObjectType",
                "evaluatedObjectType",
            )
        )
        assert_type = _normalize_token(
            _resolve_configuration_value(configuration_json, "assert_type", "assertType")
        )
        error_message = str(
            _resolve_configuration_value(configuration_json, "error_message", "errorMessage")
            or ""
        ).strip()

        st.write(f"Target: {_assert_object_type_label(evaluated_object_type)}")
        st.write(f"Assert: {_assert_type_label(assert_type)}")
        if error_message:
            st.write(f"Error message: {error_message}")

        if assert_type in {ASSERT_TYPE_CONTAINS, ASSERT_TYPE_JSON_ARRAY_EQUALS}:
            expected_json_array_id = str(
                _resolve_configuration_value(
                    configuration_json,
                    "expected_json_array_id",
                    "expectedJsonArrayId",
                    "json_array_id",
                )
                or ""
            ).strip()
            compare_keys = _parse_compare_keys(
                _resolve_configuration_value(configuration_json, "compare_keys", "compareKeys")
            )
            expected_json_array = json_arrays_by_id.get(expected_json_array_id, {})
            expected_label = _json_array_label(expected_json_array)
            if expected_label == "-" and expected_json_array_id:
                expected_label = expected_json_array_id
            st.write(f"Expected json-array: {expected_label}")
            st.write(f"Compare keys: {', '.join(compare_keys) if compare_keys else '-'}")
            if isinstance(expected_json_array, dict) and expected_json_array:
                st.markdown("**Expected preview**")
                st.json(expected_json_array.get("payload") or [], expanded=False)

        if assert_type == ASSERT_TYPE_SCHEMA_VALIDATION:
            schema = _safe_dict(
                _resolve_configuration_value(configuration_json, "json_schema", "jsonSchema")
            )
            st.markdown("**Json schema**")
            st.code(_pretty_json(schema), language="json")
        return

    if operation_type == OPERATION_TYPE_RUN_SUITE:
        suite_id = str(
            _resolve_configuration_value(configuration_json, "suite_id", "suiteId", "suite_id", "suiteId")
            or "-"
        ).strip()
        st.write(f"Suite id: {suite_id or '-'}")
        return

    if operation_type == OPERATION_TYPE_SET_VAR:
        st.write(f"Key: {configuration_json.get('key') or '-'}")
        st.write(f"Scope: {configuration_json.get('scope') or 'auto'}")
        st.markdown("**Value**")
        st.code(_pretty_json(configuration_json.get("value")), language="json")
        return

    if operation_type == OPERATION_TYPE_READ_API:
        st.write(f"Method: GET")
        st.write(f"URL: {configuration_json.get('url') or '-'}")
        st.markdown("**Query params**")
        st.code(_pretty_json(configuration_json.get("queryParams") or {}), language="json")
        st.markdown("**Headers**")
        st.code(_pretty_json(configuration_json.get("headers") or {}), language="json")
        st.write(f"Timeout seconds: {configuration_json.get('timeoutSeconds') or 30}")
        return

    if operation_type == OPERATION_TYPE_WRITE_API:
        st.write(f"Method: {configuration_json.get('method') or '-'}")
        st.write(f"URL: {configuration_json.get('url') or '-'}")
        st.markdown("**Query params**")
        st.code(_pretty_json(configuration_json.get("queryParams") or {}), language="json")
        st.markdown("**Headers**")
        st.code(_pretty_json(configuration_json.get("headers") or {}), language="json")
        st.write(f"Body type: {configuration_json.get('bodyType') or 'json'}")
        st.markdown("**Body**")
        st.code(_pretty_json(configuration_json.get("body")), language="json")
        st.write(f"Timeout seconds: {configuration_json.get('timeoutSeconds') or 30}")
        return

    if operation_type == OPERATION_TYPE_SET_RESPONSE_STATUS:
        st.write(f"Status: {configuration_json.get('status', 200)}")
        return

    if operation_type == OPERATION_TYPE_SET_RESPONSE_HEADER:
        st.write(
            f"Header: {configuration_json.get('name') or configuration_json.get('header') or '-'}"
        )
        st.markdown("**Value**")
        st.code(_pretty_json(configuration_json.get("value")), language="json")
        return

    if operation_type == OPERATION_TYPE_SET_RESPONSE_BODY:
        st.markdown("**Body**")
        st.code(_pretty_json(configuration_json.get("body")), language="json")
        return

    if operation_type == OPERATION_TYPE_BUILD_RESPONSE_FROM_TEMPLATE:
        st.write(f"Status: {configuration_json.get('status') or '-'}")
        st.markdown("**Headers**")
        st.code(_pretty_json(configuration_json.get("headers") or {}), language="json")
        st.markdown("**Template**")
        st.code(_pretty_json(configuration_json.get("template")), language="json")
        return

    st.code(_pretty_json(configuration_json), language="json")


def _new_draft_operation(
    description: str = "",
    operation_type: str = OPERATION_TYPE_PUBLISH,
    configuration_json: dict | None = None,
    order: int = 1,
) -> dict:
    return {
        "id": None,
        "order": order,
        "description": str(description or ""),
        "operation_type": str(operation_type or OPERATION_TYPE_PUBLISH),
        "configuration_json": configuration_json if isinstance(configuration_json, dict) else {},
        "_ui_key": _new_ui_key(),
    }


def _extract_operation_draft_fields(operation_item: dict) -> tuple[str, str, dict]:
    cfg = operation_item.get("configuration_json")
    if not isinstance(cfg, dict):
        cfg = {}
    operation_type = str(
        operation_item.get("operation_type") or cfg.get("operationType") or ""
    ).strip().replace("_", "-").lower()
    return (
        str(operation_item.get("description") or ""),
        operation_type or OPERATION_TYPE_PUBLISH,
        cfg,
    )


WRITE_API_METHOD_OPTIONS = ["POST", "PUT", "PATCH", "DELETE"]
API_BODY_TYPE_OPTIONS = ["json", "text"]


def _render_api_edit_fields(
    op_type: str,
    cfg: dict,
    operation_ui_key: str,
    nonce: int,
    test_ui_key: str,
):
    from elaborations_shared.components.guided_kv_editor import (
        ensure_guided_kv_state,
        render_guided_kv_rows_container,
    )
    from elaborations_shared.components.auth_editor import (
        initialize_guided_auth_state,
        render_guided_auth_editor,
    )
    from elaborations_shared.components.body_composer import (
        initialize_body_composer_state,
        render_body_composer,
    )

    prefix = f"suite_{nonce}_test_{test_ui_key}_op_edit_api_{operation_ui_key}"

    if op_type == OPERATION_TYPE_WRITE_API:
        method_key = f"{prefix}_method"
        if method_key not in st.session_state:
            current_method = str(cfg.get("method") or "POST").upper()
            st.session_state[method_key] = (
                current_method
                if current_method in WRITE_API_METHOD_OPTIONS
                else "POST"
            )
        st.selectbox("Method", options=WRITE_API_METHOD_OPTIONS, key=method_key)

    url_key = f"{prefix}_url"
    if url_key not in st.session_state:
        st.session_state[url_key] = str(cfg.get("url") or "")
    st.text_input("URL", key=url_key, placeholder="https://api.example.com/orders/{id}")

    params_state_key = f"{prefix}_params_rows"
    path_state_key = f"{prefix}_path_rows"
    auth_state_key = f"{prefix}_auth"
    headers_state_key = f"{prefix}_headers_rows"

    ensure_guided_kv_state(params_state_key, cfg.get("queryParams") or {})
    ensure_guided_kv_state(path_state_key, cfg.get("pathParams") or {})
    initialize_guided_auth_state(auth_state_key, cfg.get("authorization") or {})
    ensure_guided_kv_state(headers_state_key, cfg.get("headers") or {})

    if op_type == OPERATION_TYPE_READ_API:
        tab_params, tab_path, tab_auth, tab_headers, tab_response = st.tabs(
            ["Params", "Path", "Auth", "Headers", "Response"],
        )
    else:
        tab_params, tab_path, tab_auth, tab_headers, tab_body, tab_response = st.tabs(
            ["Params", "Path", "Auth", "Headers", "Body", "Response"],
        )

    with tab_params:
        render_guided_kv_rows_container(
            editor_state_key=params_state_key,
            key_prefix=f"{params_state_key}_row",
            use_container=False,
        )
    with tab_path:
        render_guided_kv_rows_container(
            editor_state_key=path_state_key,
            key_prefix=f"{path_state_key}_row",
            use_container=False,
        )
    with tab_auth:
        render_guided_auth_editor(auth_state_key)
    with tab_headers:
        render_guided_kv_rows_container(
            editor_state_key=headers_state_key,
            key_prefix=f"{headers_state_key}_row",
            use_container=False,
        )

    if op_type == OPERATION_TYPE_WRITE_API:
        with tab_body:
            body_type_key = f"{prefix}_body_type"
            body_composer_key = f"{prefix}_body_composer"
            if body_type_key not in st.session_state:
                st.session_state[body_type_key] = str(cfg.get("bodyType") or "json")
            st.selectbox("Body type", options=API_BODY_TYPE_OPTIONS, key=body_type_key)
            initialize_body_composer_state(body_composer_key, cfg.get("body"))
            render_body_composer(body_composer_key)

    with tab_response:
        timeout_key = f"{prefix}_timeout"
        result_target_key = f"{prefix}_result_target"
        if timeout_key not in st.session_state:
            st.session_state[timeout_key] = _safe_int(cfg.get("timeoutSeconds"), 30)
        if result_target_key not in st.session_state:
            st.session_state[result_target_key] = str(cfg.get("result_target") or "")
        st.number_input("Timeout seconds", min_value=1, key=timeout_key)
        st.text_input(
            "Result target",
            key=result_target_key,
            placeholder=_example_placeholder("apiResult"),
        )


def _collect_api_edit_values(
    op_type: str,
    operation_ui_key: str,
    nonce: int,
    test_ui_key: str,
) -> tuple[dict | None, str | None]:
    from elaborations_shared.components.guided_kv_editor import (
        collect_guided_kv_rows,
    )
    from elaborations_shared.components.auth_editor import (
        collect_guided_auth_value,
    )
    from elaborations_shared.components.body_composer import (
        collect_body_composer_value,
    )

    prefix = f"suite_{nonce}_test_{test_ui_key}_op_edit_api_{operation_ui_key}"

    url = str(st.session_state.get(f"{prefix}_url") or "").strip()
    if not url:
        return None, "Il campo URL e' obbligatorio."

    params_rows = st.session_state.get(f"{prefix}_params_rows", [])
    query_params, params_error = collect_guided_kv_rows(
        params_rows if isinstance(params_rows, list) else [],
        f"{prefix}_params_rows_row",
        "Params",
    )
    if params_error:
        return None, params_error

    path_rows = st.session_state.get(f"{prefix}_path_rows", [])
    path_params, path_error = collect_guided_kv_rows(
        path_rows if isinstance(path_rows, list) else [],
        f"{prefix}_path_rows_row",
        "Path",
    )
    if path_error:
        return None, path_error

    authorization, auth_error = collect_guided_auth_value(f"{prefix}_auth")
    if auth_error:
        return None, auth_error

    headers_rows = st.session_state.get(f"{prefix}_headers_rows", [])
    headers, headers_error = collect_guided_kv_rows(
        headers_rows if isinstance(headers_rows, list) else [],
        f"{prefix}_headers_rows_row",
        "Headers",
    )
    if headers_error:
        return None, headers_error

    timeout_seconds = _safe_int(st.session_state.get(f"{prefix}_timeout"), 30)
    result_target = _normalize_context_target_path(
        st.session_state.get(f"{prefix}_result_target"),
    )

    if op_type == OPERATION_TYPE_READ_API:
        cfg: dict = {
            "operationType": OPERATION_TYPE_READ_API,
            "commandCode": "readApi",
            "commandType": "action",
            "url": url,
            "timeoutSeconds": timeout_seconds or 30,
        }
    else:
        method = str(
            st.session_state.get(f"{prefix}_method") or "POST"
        ).strip().upper()
        body_type = str(
            st.session_state.get(f"{prefix}_body_type") or "json"
        ).strip().lower()

        body_composer_key = f"{prefix}_body_composer"
        body_payload, body_error = collect_body_composer_value(body_composer_key)
        if body_error:
            return None, body_error

        cfg = {
            "operationType": OPERATION_TYPE_WRITE_API,
            "commandCode": "writeApi",
            "commandType": "action",
            "method": method,
            "url": url,
            "bodyType": body_type,
            "timeoutSeconds": timeout_seconds or 30,
        }
        if body_payload is not None and body_payload != "":
            cfg["body"] = body_payload

    if query_params:
        cfg["queryParams"] = query_params
    if path_params:
        cfg["pathParams"] = path_params
    cfg["authorization"] = authorization
    if headers:
        cfg["headers"] = headers
    if result_target:
        cfg["result_target"] = result_target

    return cfg, None


@st.dialog("Modify operation", width="large")
def _edit_test_operation_dialog(
    suite_test: dict,
    operation: dict,
    op_idx: int,
    test_ui_key: str,
    nonce: int,
    persist_suite_changes_fn=None,
):
    operation_ui_key = operation.get("_ui_key") or f"{test_ui_key}_op_{op_idx}"
    operation["_ui_key"] = operation_ui_key
    raw_operation_type = str(operation.get("operation_type") or "")
    normalized_op_type = _normalize_operation_type(raw_operation_type)
    operation_type_display = _operation_type_label(raw_operation_type)
    configuration_json = _safe_dict(operation.get("configuration_json") or {})
    description_key = (
        f"suite_{nonce}_test_{test_ui_key}_operation_edit_description_{operation_ui_key}"
    )
    cfg_key = f"suite_{nonce}_test_{test_ui_key}_operation_edit_cfg_{operation_ui_key}"

    st.text_input(
        "Description",
        key=description_key,
        value=str(operation.get("description") or ""),
    )
    st.text_input(
        "Operation type",
        key=f"suite_{nonce}_test_{test_ui_key}_operation_edit_type_{operation_ui_key}",
        value=operation_type_display,
        disabled=True,
    )

    is_api_type = normalized_op_type in (OPERATION_TYPE_READ_API, OPERATION_TYPE_WRITE_API)

    if is_api_type:
        _render_api_edit_fields(
            normalized_op_type,
            configuration_json,
            operation_ui_key,
            nonce,
            test_ui_key,
        )
    else:
        st.text_area(
            "Configuration JSON",
            key=cfg_key,
            value=_pretty_json(configuration_json),
            height=240,
            help="Modifica i parametri dell'operazione come oggetto JSON.",
        )

    selected_order = int(
        st.number_input(
            "Operation order",
            min_value=0,
            value=_safe_int(operation.get("order"), op_idx + 1),
            key=f"suite_{nonce}_test_{test_ui_key}_operation_order_{operation_ui_key}",
        )
    )

    action_cols = st.columns([4, 2, 2, 2], gap="small", vertical_alignment="center")
    with action_cols[1]:
        if st.button(
            "Save",
            key=f"suite_{nonce}_test_{test_ui_key}_operation_edit_save_{operation_ui_key}",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            operation_description = str(st.session_state.get(description_key) or "").strip()
            if not operation_description:
                st.error("Il campo Description dell'operazione e' obbligatorio.")
                return

            if is_api_type:
                updated_cfg, cfg_error = _collect_api_edit_values(
                    normalized_op_type,
                    operation_ui_key,
                    nonce,
                    test_ui_key,
                )
                if cfg_error:
                    st.error(cfg_error)
                    return
                final_operation_type = normalized_op_type
            else:
                cfg_raw = str(st.session_state.get(cfg_key) or "").strip()
                if not cfg_raw:
                    st.error("Il campo Configuration JSON e' obbligatorio.")
                    return

                try:
                    updated_cfg = json.loads(cfg_raw)
                except json.JSONDecodeError as exc:
                    st.error(f"Configuration JSON non valido: {str(exc)}")
                    return

                if not isinstance(updated_cfg, dict):
                    st.error("Configuration JSON deve essere un oggetto JSON.")
                    return

                final_operation_type = str(
                    updated_cfg.get("operationType") or operation.get("operation_type") or ""
                ).strip().replace("_", "-").lower()
                if not final_operation_type:
                    st.error("Configuration JSON deve includere operationType.")
                    return

                target_path = _normalize_context_target_path(updated_cfg.get("target"))
                if target_path:
                    updated_cfg["target"] = target_path
                elif "target" in updated_cfg:
                    updated_cfg.pop("target", None)

                result_target_path = _normalize_context_target_path(updated_cfg.get("result_target"))
                if result_target_path:
                    updated_cfg["result_target"] = result_target_path
                elif "result_target" in updated_cfg:
                    updated_cfg.pop("result_target", None)

                updated_cfg["operationType"] = final_operation_type

            operation["description"] = operation_description
            operation["operation_type"] = final_operation_type
            operation["configuration_json"] = updated_cfg
            operation["order"] = selected_order
            _reload_test_operations(suite_test)
            _persist_suite_changes(persist_suite_changes_fn)
    with action_cols[2]:
        if st.button(
            "Delete",
            key=f"suite_{nonce}_test_{test_ui_key}_operation_edit_delete_{operation_ui_key}",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            operations = suite_test.get("operations", [])
            if 0 <= op_idx < len(operations):
                operations.pop(op_idx)
            _persist_suite_changes(persist_suite_changes_fn)
    with action_cols[3]:
        if st.button(
            "Cancel",
            key=f"suite_{nonce}_test_{test_ui_key}_operation_edit_cancel_{operation_ui_key}",
            use_container_width=True,
        ):
            st.rerun()

def _operation_status_icon(operation_status: str) -> str:
    normalized_status = str(operation_status or "").strip().lower()
    if normalized_status == OPERATION_STATUS_SUCCESS:
        return ":material/check_circle:"
    if normalized_status == OPERATION_STATUS_ERROR:
        return ":material/error:"
    if normalized_status == OPERATION_STATUS_RUNNING:
        return ":material/pending:"
    return ":material/radio_button_unchecked:"

def render_operation_component(
    suite_test: dict,
    operation: dict,
    op_idx: int,
    test_ui_key: str,
    nonce: int,
    operation_status: str = OPERATION_STATUS_IDLE,
    operation_error_message: str = "",
    persist_suite_changes_fn=None,
    summary_only: bool = False,
    show_status_indicator: bool = True,
):
    operation_ui_key = operation.get("_ui_key") or f"{test_ui_key}_op_{op_idx}"
    operation["_ui_key"] = operation_ui_key
    operation_description = str(operation.get("description") or "").strip()
    operation_label = operation_description or f"Operation {op_idx + 1}"
    raw_operation_type = str(operation.get("operation_type") or "")
    normalized_op_type = _normalize_operation_type(raw_operation_type)
    operation_type_display = _operation_type_label(raw_operation_type)
    target_label, target_value = _resolve_operation_target_summary(operation)

    is_api_type = normalized_op_type in (OPERATION_TYPE_READ_API, OPERATION_TYPE_WRITE_API)

    if is_api_type:
        _render_api_operation_inline(
            suite_test=suite_test,
            operation=operation,
            op_idx=op_idx,
            test_ui_key=test_ui_key,
            nonce=nonce,
            operation_ui_key=operation_ui_key,
            normalized_op_type=normalized_op_type,
            operation_type_display=operation_type_display,
            operation_label=operation_label,
            persist_suite_changes_fn=persist_suite_changes_fn,
        )
    else:
        with st.container(border=True):
            st.caption("Type")
            st.write(operation_type_display or "-")
            st.caption(target_label)
            st.write(target_value or "-")
            st.caption("Description")
            st.write(operation_description or "-")

        if st.button(
                "",
                key=f"suite_{nonce}_test_{test_ui_key}_operation_more_actions_{operation_ui_key}",
                icon=":material/more_vert:",
                help="Modify operation",
                type="tertiary",
                use_container_width=True,
            ):
                _edit_test_operation_dialog(
                    suite_test=suite_test,
                    operation=operation,
                    op_idx=op_idx,
                    test_ui_key=test_ui_key,
                    nonce=nonce,
                    persist_suite_changes_fn=persist_suite_changes_fn,
                )


def _render_api_operation_inline(
    suite_test: dict,
    operation: dict,
    op_idx: int,
    test_ui_key: str,
    nonce: int,
    operation_ui_key: str,
    normalized_op_type: str,
    operation_type_display: str,
    operation_label: str,
    persist_suite_changes_fn=None,
):
    from elaborations_shared.components.guided_kv_editor import (
        collect_guided_kv_rows,
        ensure_guided_kv_state,
        render_guided_kv_rows_container,
    )
    from elaborations_shared.components.auth_editor import (
        collect_guided_auth_value,
        initialize_guided_auth_state,
        render_guided_auth_editor,
    )
    from elaborations_shared.components.body_composer import (
        collect_body_composer_value,
        initialize_body_composer_state,
        render_body_composer,
    )

    cfg = _safe_dict(operation.get("configuration_json") or {})
    prefix = f"suite_{nonce}_test_{test_ui_key}_op_inline_api_{operation_ui_key}"

    wrapper_cols = st.columns([18, 1], gap="small", vertical_alignment="top")
    with wrapper_cols[0]:
        with st.expander(operation_label, expanded=False):
            st.text_input(
                "Operation type",
                value=operation_type_display,
                disabled=True,
                key=f"{prefix}_type_display",
            )

            if normalized_op_type == OPERATION_TYPE_WRITE_API:
                method_key = f"{prefix}_method"
                if method_key not in st.session_state:
                    current_method = str(cfg.get("method") or "POST").upper()
                    st.session_state[method_key] = (
                        current_method
                        if current_method in WRITE_API_METHOD_OPTIONS
                        else "POST"
                    )

            url_key = f"{prefix}_url"
            if url_key not in st.session_state:
                st.session_state[url_key] = str(cfg.get("url") or "")

            if normalized_op_type == OPERATION_TYPE_WRITE_API:
                conf_cols = st.columns([2, 5], gap="small", vertical_alignment="center")
                with conf_cols[0]:
                    st.selectbox("Method", options=WRITE_API_METHOD_OPTIONS, key=method_key)
                with conf_cols[1]:
                    st.text_input("URL", key=url_key, placeholder="https://api.example.com/orders/{id}")
            else:
                st.text_input("URL", key=url_key, placeholder="https://api.example.com/orders/{id}")

            params_state_key = f"{prefix}_params_rows"
            path_state_key = f"{prefix}_path_rows"
            auth_state_key = f"{prefix}_auth"
            headers_state_key = f"{prefix}_headers_rows"

            ensure_guided_kv_state(params_state_key, cfg.get("queryParams") or {})
            ensure_guided_kv_state(path_state_key, cfg.get("pathParams") or {})
            initialize_guided_auth_state(auth_state_key, cfg.get("authorization") or {})
            ensure_guided_kv_state(headers_state_key, cfg.get("headers") or {})

            if normalized_op_type == OPERATION_TYPE_READ_API:
                tab_params, tab_path, tab_auth, tab_headers, tab_response = st.tabs(
                    ["Params", "Path", "Auth", "Headers", "Response"],
                )
            else:
                tab_params, tab_path, tab_auth, tab_headers, tab_body, tab_response = st.tabs(
                    ["Params", "Path", "Auth", "Headers", "Body", "Response"],
                )

            with tab_params:
                render_guided_kv_rows_container(
                    editor_state_key=params_state_key,
                    key_prefix=f"{params_state_key}_row",
                    use_container=False,
                )
            with tab_path:
                render_guided_kv_rows_container(
                    editor_state_key=path_state_key,
                    key_prefix=f"{path_state_key}_row",
                    use_container=False,
                )
            with tab_auth:
                render_guided_auth_editor(auth_state_key)
            with tab_headers:
                render_guided_kv_rows_container(
                    editor_state_key=headers_state_key,
                    key_prefix=f"{headers_state_key}_row",
                    use_container=False,
                )

            if normalized_op_type == OPERATION_TYPE_WRITE_API:
                with tab_body:
                    body_type_key = f"{prefix}_body_type"
                    body_composer_key = f"{prefix}_body_composer"
                    if body_type_key not in st.session_state:
                        st.session_state[body_type_key] = str(cfg.get("bodyType") or "json")
                    st.selectbox("Body type", options=API_BODY_TYPE_OPTIONS, key=body_type_key)
                    initialize_body_composer_state(body_composer_key, cfg.get("body"))
                    render_body_composer(body_composer_key)

            with tab_response:
                timeout_key = f"{prefix}_timeout"
                result_target_key = f"{prefix}_result_target"
                if timeout_key not in st.session_state:
                    st.session_state[timeout_key] = _safe_int(cfg.get("timeoutSeconds"), 30)
                if result_target_key not in st.session_state:
                    st.session_state[result_target_key] = str(cfg.get("result_target") or "")
                st.number_input("Timeout seconds", min_value=1, key=timeout_key)
                st.text_input(
                    "Result target",
                    key=result_target_key,
                    placeholder=_example_placeholder("apiResult"),
                )

            save_cols = st.columns([6, 2], gap="small", vertical_alignment="center")
            with save_cols[1]:
                if st.button(
                    "Save",
                    key=f"{prefix}_save",
                    icon=":material/save:",
                    use_container_width=True,
                ):
                    url = str(st.session_state.get(url_key) or "").strip()
                    if not url:
                        st.error("Il campo URL e' obbligatorio.")
                        return

                    params_rows = st.session_state.get(params_state_key, [])
                    query_params, params_error = collect_guided_kv_rows(
                        params_rows if isinstance(params_rows, list) else [],
                        f"{params_state_key}_row",
                        "Params",
                    )
                    if params_error:
                        st.error(params_error)
                        return

                    path_rows = st.session_state.get(path_state_key, [])
                    path_params, path_error = collect_guided_kv_rows(
                        path_rows if isinstance(path_rows, list) else [],
                        f"{path_state_key}_row",
                        "Path",
                    )
                    if path_error:
                        st.error(path_error)
                        return

                    authorization, auth_error = collect_guided_auth_value(auth_state_key)
                    if auth_error:
                        st.error(auth_error)
                        return

                    headers_rows_data = st.session_state.get(headers_state_key, [])
                    headers, headers_error = collect_guided_kv_rows(
                        headers_rows_data if isinstance(headers_rows_data, list) else [],
                        f"{headers_state_key}_row",
                        "Headers",
                    )
                    if headers_error:
                        st.error(headers_error)
                        return

                    timeout_seconds = _safe_int(st.session_state.get(timeout_key), 30)
                    result_target = _normalize_context_target_path(
                        st.session_state.get(result_target_key),
                    )

                    if normalized_op_type == OPERATION_TYPE_READ_API:
                        updated_cfg: dict = {
                            "operationType": OPERATION_TYPE_READ_API,
                            "commandCode": "readApi",
                            "commandType": "action",
                            "url": url,
                            "timeoutSeconds": timeout_seconds or 30,
                        }
                    else:
                        method = str(
                            st.session_state.get(f"{prefix}_method") or "POST"
                        ).strip().upper()
                        body_type = str(
                            st.session_state.get(f"{prefix}_body_type") or "json"
                        ).strip().lower()

                        body_composer_key_save = f"{prefix}_body_composer"
                        body_payload, body_error = collect_body_composer_value(body_composer_key_save)
                        if body_error:
                            st.error(body_error)
                            return

                        updated_cfg = {
                            "operationType": OPERATION_TYPE_WRITE_API,
                            "commandCode": "writeApi",
                            "commandType": "action",
                            "method": method,
                            "url": url,
                            "bodyType": body_type,
                            "timeoutSeconds": timeout_seconds or 30,
                        }
                        if body_payload is not None and body_payload != "":
                            updated_cfg["body"] = body_payload

                    if query_params:
                        updated_cfg["queryParams"] = query_params
                    if path_params:
                        updated_cfg["pathParams"] = path_params
                    updated_cfg["authorization"] = authorization
                    if headers:
                        updated_cfg["headers"] = headers
                    if result_target:
                        updated_cfg["result_target"] = result_target

                    operation["configuration_json"] = updated_cfg
                    operation["operation_type"] = normalized_op_type
                    _persist_suite_changes(persist_suite_changes_fn)

    with wrapper_cols[1]:
        if st.button(
            "",
            key=f"suite_{nonce}_test_{test_ui_key}_operation_more_actions_{operation_ui_key}",
            icon=":material/more_vert:",
            help="Modify operation",
            type="tertiary",
            use_container_width=True,
        ):
            _edit_test_operation_dialog(
                suite_test=suite_test,
                operation=operation,
                op_idx=op_idx,
                test_ui_key=test_ui_key,
                nonce=nonce,
                persist_suite_changes_fn=persist_suite_changes_fn,
            )
        


def find_draft_test_by_ui_key(draft: dict, test_ui_key: str) -> dict | None:
    if not test_ui_key:
        return None
    for suite_test in draft.get("tests") or []:
        if str(suite_test.get("_ui_key") or "") == str(test_ui_key):
            return suite_test
    for suite_test in draft.get("tests") or []:
        if str(suite_test.get("_ui_key") or "") == str(test_ui_key):
            return suite_test
    hooks = draft.get("hooks") or {}
    if isinstance(hooks, dict):
        for hook_item in hooks.values():
            if isinstance(hook_item, dict) and str(hook_item.get("_ui_key") or "") == str(test_ui_key):
                return hook_item
    return None


def append_operation_to_test(suite_test: dict, operation_item: dict):
    if not isinstance(operation_item, dict):
        return
    description, operation_type, cfg = _extract_operation_draft_fields(operation_item)
    operations = suite_test.setdefault("operations", [])
    operations.append(
        _new_draft_operation(
            description=description,
            operation_type=operation_type,
            configuration_json=cfg,
            order=len(operations) + 1,
        )
    )


def build_operation_creation_payload(dialog_nonce: int) -> tuple[dict | None, str | None]:
    description = str(
        st.session_state.get(f"suite_add_operation_description_{dialog_nonce}") or ""
    )
    operation_type = str(
        st.session_state.get(f"suite_add_operation_type_{dialog_nonce}") or OPERATION_TYPE_PUBLISH
    )
    if not description.strip():
        return None, "Il campo Description dell'operazione e' obbligatorio."

    cfg: dict
    if operation_type == OPERATION_TYPE_DATA:
        target_path = _normalize_context_target_path(
            st.session_state.get(f"suite_add_operation_target_{dialog_nonce}")
        )
        if not target_path:
            return None, "Il campo Target e' obbligatorio per le input operation."
        data_payload, parse_error = _parse_json_value(
            st.session_state.get(f"suite_add_operation_data_payload_{dialog_nonce}")
        )
        if parse_error:
            return None, parse_error
        if not isinstance(data_payload, list):
            return None, "Il payload Data deve essere un array JSON."
        cfg = {
            "operationType": OPERATION_TYPE_DATA,
            "data": data_payload,
            "target": target_path,
        }
    elif operation_type == OPERATION_TYPE_DATA_FROM_JSON_ARRAY:
        target_path = _normalize_context_target_path(
            st.session_state.get(f"suite_add_operation_target_{dialog_nonce}")
        )
        if not target_path:
            return None, "Il campo Target e' obbligatorio per le input operation."
        json_array_id = str(
            st.session_state.get(f"suite_add_operation_json_array_id_{dialog_nonce}") or ""
        ).strip()
        if not json_array_id:
            return None, "Il campo Json array e' obbligatorio."
        cfg = {
            "operationType": OPERATION_TYPE_DATA_FROM_JSON_ARRAY,
            "json_array_id": json_array_id,
            "target": target_path,
        }
    elif operation_type == OPERATION_TYPE_DATA_FROM_DB:
        target_path = _normalize_context_target_path(
            st.session_state.get(f"suite_add_operation_target_{dialog_nonce}")
        )
        if not target_path:
            return None, "Il campo Target e' obbligatorio per le input operation."
        dataset_id = str(
            st.session_state.get(f"suite_add_operation_dataset_id_{dialog_nonce}") or ""
        ).strip()
        if not dataset_id:
            return None, "Il campo Dataset e' obbligatorio."
        cfg = {
            "operationType": OPERATION_TYPE_DATA_FROM_DB,
            "dataset_id": dataset_id,
            "target": target_path,
        }
    elif operation_type == OPERATION_TYPE_DATA_FROM_QUEUE:
        target_path = _normalize_context_target_path(
            st.session_state.get(f"suite_add_operation_target_{dialog_nonce}")
        )
        if not target_path:
            return None, "Il campo Target e' obbligatorio per le input operation."
        queue_id = str(
            st.session_state.get(f"suite_add_operation_queue_id_{dialog_nonce}") or ""
        ).strip()
        if not queue_id:
            return None, "Il campo Queue id e' obbligatorio."
        cfg = {
            "operationType": OPERATION_TYPE_DATA_FROM_QUEUE,
            "queue_id": queue_id,
            "retry": _safe_int(st.session_state.get(f"suite_add_operation_retry_{dialog_nonce}"), 3),
            "wait_time_seconds": _safe_int(
                st.session_state.get(f"suite_add_operation_wait_time_seconds_{dialog_nonce}"),
                20,
            ),
            "max_messages": _safe_int(
                st.session_state.get(f"suite_add_operation_max_messages_{dialog_nonce}"),
                1000,
            ),
            "target": target_path,
        }
    elif operation_type == OPERATION_TYPE_SLEEP:
        duration = _safe_int(st.session_state.get(f"suite_add_operation_sleep_duration_{dialog_nonce}"), 0)
        if duration < 0:
            return None, "Il campo Duration deve essere >= 0."
        cfg = {"operationType": OPERATION_TYPE_SLEEP, "duration": duration}
    elif operation_type == OPERATION_TYPE_PUBLISH:
        queue_id = str(
            st.session_state.get(f"suite_add_operation_queue_id_{dialog_nonce}") or ""
        ).strip()
        if not queue_id:
            return None, "Il campo Queue id e' obbligatorio."
        result_target = _normalize_context_target_path(
            st.session_state.get(f"suite_add_operation_result_target_{dialog_nonce}")
        )
        cfg = {
            "operationType": OPERATION_TYPE_PUBLISH,
            "queue_id": queue_id,
        }
        if result_target:
            cfg["result_target"] = result_target
    elif operation_type == OPERATION_TYPE_SAVE_INTERNAL_DB:
        table_name = str(
            st.session_state.get(f"suite_add_operation_internal_table_name_{dialog_nonce}")
            or ""
        ).strip()
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        result_target = _normalize_context_target_path(
            st.session_state.get(f"suite_add_operation_result_target_{dialog_nonce}")
        )
        cfg = {
            "operationType": OPERATION_TYPE_SAVE_INTERNAL_DB,
            "table_name": table_name,
        }
        if result_target:
            cfg["result_target"] = result_target
    elif operation_type == OPERATION_TYPE_SAVE_EXTERNAL_DB:
        connection_id = str(
            st.session_state.get(f"suite_add_operation_connection_id_{dialog_nonce}") or ""
        ).strip()
        table_name = str(
            st.session_state.get(f"suite_add_operation_external_table_name_{dialog_nonce}")
            or ""
        ).strip()
        if not connection_id:
            return None, "Il campo Connection e' obbligatorio."
        if not table_name:
            return None, "Il campo Table name e' obbligatorio."
        result_target = _normalize_context_target_path(
            st.session_state.get(f"suite_add_operation_result_target_{dialog_nonce}")
        )
        cfg = {
            "operationType": OPERATION_TYPE_SAVE_EXTERNAL_DB,
            "connection_id": connection_id,
            "table_name": table_name,
        }
        if result_target:
            cfg["result_target"] = result_target
    elif operation_type == OPERATION_TYPE_ASSERT:
        evaluated_object_type = _normalize_token(
            st.session_state.get(
                f"suite_add_operation_assert_object_type_{dialog_nonce}"
            )
            or ASSERT_OBJECT_TYPE_JSON_DATA
        )
        assert_type = _normalize_token(
            st.session_state.get(f"suite_add_operation_assert_type_{dialog_nonce}")
            or ASSERT_TYPE_NOT_EMPTY
        )
        error_message = str(
            st.session_state.get(f"suite_add_operation_assert_error_message_{dialog_nonce}")
            or ""
        ).strip()

        cfg = {
            "operationType": OPERATION_TYPE_ASSERT,
            "evaluated_object_type": evaluated_object_type,
            "assert_type": assert_type,
        }
        if error_message:
            cfg["error_message"] = error_message

        if assert_type == ASSERT_TYPE_SCHEMA_VALIDATION:
            schema, parse_error = _parse_json_dict(
                st.session_state.get(f"suite_add_operation_assert_schema_{dialog_nonce}")
            )
            if parse_error:
                return None, parse_error
            cfg["json_schema"] = schema
        elif assert_type in {ASSERT_TYPE_CONTAINS, ASSERT_TYPE_JSON_ARRAY_EQUALS}:
            expected_json_array_id = str(
                st.session_state.get(
                    f"suite_add_operation_assert_expected_json_array_id_{dialog_nonce}"
                )
                or ""
            ).strip()
            compare_keys = _parse_compare_keys(
                st.session_state.get(
                    f"suite_add_operation_assert_compare_keys_{dialog_nonce}"
                )
            )
            if not expected_json_array_id:
                return None, "Il campo Expected json-array e' obbligatorio."
            if not compare_keys:
                return None, "Il campo Compare keys e' obbligatorio."
            cfg["expected_json_array_id"] = expected_json_array_id
            cfg["compare_keys"] = compare_keys
        elif assert_type == ASSERT_TYPE_EQUALS:
            actual_value, _ = _parse_json_value(
                st.session_state.get(f"suite_add_operation_assert_actual_{dialog_nonce}")
            )
            expected_value, _ = _parse_json_value(
                st.session_state.get(f"suite_add_operation_assert_expected_{dialog_nonce}")
            )
            cfg["actual"] = actual_value
            cfg["expected"] = expected_value
    elif operation_type == OPERATION_TYPE_RUN_SUITE:
        suite_id = str(
            st.session_state.get(
                f"suite_add_operation_run_suite_id_{dialog_nonce}"
            )
            or ""
        ).strip()
        if not suite_id:
            return None, "Il campo Suite id e' obbligatorio."
        result_target = _normalize_context_target_path(
            st.session_state.get(f"suite_add_operation_result_target_{dialog_nonce}")
        )
        cfg = {
            "operationType": OPERATION_TYPE_RUN_SUITE,
            "suite_id": suite_id,
        }
        if result_target:
            cfg["result_target"] = result_target
    elif operation_type == OPERATION_TYPE_READ_API:
        url = str(
            st.session_state.get(f"suite_add_operation_read_api_url_{dialog_nonce}") or ""
        ).strip()
        if not url:
            return None, "Il campo URL e' obbligatorio."
        result_target = _normalize_context_target_path(
            st.session_state.get(f"suite_add_operation_result_target_{dialog_nonce}")
        )
        raw_query_params = st.session_state.get(f"suite_add_operation_read_api_query_params_{dialog_nonce}")
        raw_headers = st.session_state.get(f"suite_add_operation_read_api_headers_{dialog_nonce}")
        timeout_seconds = _safe_int(
            st.session_state.get(f"suite_add_operation_read_api_timeout_seconds_{dialog_nonce}"), 30
        )
        cfg = {
            "operationType": OPERATION_TYPE_READ_API,
            "commandCode": "readApi",
            "commandType": "action",
            "url": url,
            "timeoutSeconds": timeout_seconds or 30,
        }
        if raw_query_params:
            if isinstance(raw_query_params, str):
                parsed_qp, qp_err = _parse_json_value(raw_query_params)
                if not qp_err and isinstance(parsed_qp, dict):
                    cfg["queryParams"] = parsed_qp
            elif isinstance(raw_query_params, dict):
                cfg["queryParams"] = raw_query_params
        if raw_headers:
            if isinstance(raw_headers, str):
                parsed_h, h_err = _parse_json_value(raw_headers)
                if not h_err and isinstance(parsed_h, dict):
                    cfg["headers"] = parsed_h
            elif isinstance(raw_headers, dict):
                cfg["headers"] = raw_headers
        if result_target:
            cfg["result_target"] = result_target
    elif operation_type == OPERATION_TYPE_WRITE_API:
        method = str(
            st.session_state.get(f"suite_add_operation_write_api_method_{dialog_nonce}") or "POST"
        ).strip().upper()
        url = str(
            st.session_state.get(f"suite_add_operation_write_api_url_{dialog_nonce}") or ""
        ).strip()
        if not url:
            return None, "Il campo URL e' obbligatorio."
        result_target = _normalize_context_target_path(
            st.session_state.get(f"suite_add_operation_result_target_{dialog_nonce}")
        )
        raw_query_params = st.session_state.get(f"suite_add_operation_write_api_query_params_{dialog_nonce}")
        raw_headers = st.session_state.get(f"suite_add_operation_write_api_headers_{dialog_nonce}")
        raw_body = st.session_state.get(f"suite_add_operation_write_api_body_{dialog_nonce}")
        timeout_seconds = _safe_int(
            st.session_state.get(f"suite_add_operation_write_api_timeout_seconds_{dialog_nonce}"), 30
        )
        cfg = {
            "operationType": OPERATION_TYPE_WRITE_API,
            "commandCode": "writeApi",
            "commandType": "action",
            "method": method,
            "url": url,
            "bodyType": "json",
            "timeoutSeconds": timeout_seconds or 30,
        }
        if raw_query_params:
            if isinstance(raw_query_params, str):
                parsed_qp, qp_err = _parse_json_value(raw_query_params)
                if not qp_err and isinstance(parsed_qp, dict):
                    cfg["queryParams"] = parsed_qp
            elif isinstance(raw_query_params, dict):
                cfg["queryParams"] = raw_query_params
        if raw_headers:
            if isinstance(raw_headers, str):
                parsed_h, h_err = _parse_json_value(raw_headers)
                if not h_err and isinstance(parsed_h, dict):
                    cfg["headers"] = parsed_h
            elif isinstance(raw_headers, dict):
                cfg["headers"] = raw_headers
        if raw_body:
            if isinstance(raw_body, str):
                parsed_b, b_err = _parse_json_value(raw_body)
                if not b_err:
                    cfg["body"] = parsed_b
            else:
                cfg["body"] = raw_body
        if result_target:
            cfg["result_target"] = result_target
    elif operation_type == OPERATION_TYPE_SET_VAR:
        key = str(
            st.session_state.get(f"suite_add_operation_set_var_key_{dialog_nonce}") or ""
        ).strip()
        scope = str(
            st.session_state.get(f"suite_add_operation_set_var_scope_{dialog_nonce}") or "auto"
        ).strip()
        if not key:
            return None, "Il campo Key e' obbligatorio."
        value_payload, _ = _parse_json_value(
            st.session_state.get(f"suite_add_operation_set_var_value_{dialog_nonce}")
        )
        cfg = {
            "operationType": OPERATION_TYPE_SET_VAR,
            "key": key,
            "scope": scope or "auto",
            "value": value_payload,
        }
    elif operation_type == OPERATION_TYPE_SET_RESPONSE_STATUS:
        status_value = _safe_int(
            st.session_state.get(f"suite_add_operation_response_status_{dialog_nonce}"),
            200,
        )
        cfg = {
            "operationType": OPERATION_TYPE_SET_RESPONSE_STATUS,
            "status": status_value,
        }
    elif operation_type == OPERATION_TYPE_SET_RESPONSE_HEADER:
        header_name = str(
            st.session_state.get(f"suite_add_operation_response_header_name_{dialog_nonce}")
            or ""
        ).strip()
        if not header_name:
            return None, "Il campo Header name e' obbligatorio."
        header_value, _ = _parse_json_value(
            st.session_state.get(f"suite_add_operation_response_header_value_{dialog_nonce}")
        )
        cfg = {
            "operationType": OPERATION_TYPE_SET_RESPONSE_HEADER,
            "name": header_name,
            "value": header_value,
        }
    elif operation_type == OPERATION_TYPE_SET_RESPONSE_BODY:
        body_value, _ = _parse_json_value(
            st.session_state.get(f"suite_add_operation_response_body_{dialog_nonce}")
        )
        cfg = {
            "operationType": OPERATION_TYPE_SET_RESPONSE_BODY,
            "body": body_value,
        }
    elif operation_type == OPERATION_TYPE_BUILD_RESPONSE_FROM_TEMPLATE:
        template_value, _ = _parse_json_value(
            st.session_state.get(
                f"suite_add_operation_response_template_{dialog_nonce}"
            )
        )
        status_value_raw = str(
            st.session_state.get(f"suite_add_operation_response_template_status_{dialog_nonce}")
            or ""
        ).strip()
        headers_value, headers_error = _parse_json_dict(
            st.session_state.get(
                f"suite_add_operation_response_template_headers_{dialog_nonce}"
            ),
            field_label="Response headers",
            allow_empty=True,
        )
        if headers_error:
            return None, headers_error
        cfg = {
            "operationType": OPERATION_TYPE_BUILD_RESPONSE_FROM_TEMPLATE,
            "template": template_value,
            "headers": headers_value or {},
        }
        if status_value_raw:
            cfg["status"] = _safe_int(status_value_raw, 200)
    else:
        return None, f"Operation type non supportato: {operation_type}"

    return {
        "description": description,
        "cfg": cfg,
    }, None


def build_draft_operation_from_creation_payload(payload: dict) -> dict:
    cfg = payload.get("cfg") if isinstance(payload, dict) else {}
    if not isinstance(cfg, dict):
        cfg = {}
    operation_type = _normalize_operation_type(
        cfg.get("operationType") or cfg.get("commandCode") or OPERATION_TYPE_PUBLISH
    )
    return {
        "description": str((payload or {}).get("description") or ""),
        "operation_type": operation_type or OPERATION_TYPE_PUBLISH,
        "configuration_json": cfg,
    }

def _resolve_target_test_for_operation_dialog(
    draft: dict,
    dialog_nonce: int,
    close_add_test_operation_dialog_fn,
) -> dict | None:
    target_test_ui_key = str(
        st.session_state.get(ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY) or ""
    )
    suite_test = find_draft_test_by_ui_key(draft, target_test_ui_key)
    if isinstance(suite_test, dict):
        return suite_test

    st.error("Elemento di destinazione non trovato.")
    if st.button(
        "Cancel",
        key=f"suite_add_operation_missing_test_cancel_{dialog_nonce}",
        use_container_width=True,
    ):
        close_add_test_operation_dialog_fn()
        st.rerun()
    return None

def _render_new_operation_form_panel(
    suite_test: dict,
    close_add_test_operation_dialog_fn,
    dialog_nonce: int,
    persist_suite_changes_fn=None,
):
    load_test_editor_context(force=False)
    load_database_connections(force=False)
    brokers = st.session_state.get(TEST_EDITOR_BROKERS_KEY, [])
    json_arrays = st.session_state.get(TEST_EDITOR_JSON_ARRAYS_KEY, [])
    database_connections = st.session_state.get(DATABASE_CONNECTIONS_KEY, [])
    if not isinstance(brokers, list):
        brokers = []
    if not isinstance(json_arrays, list):
        json_arrays = []
    if not isinstance(database_connections, list):
        database_connections = []

    broker_ids = [str(item.get("id")) for item in brokers if item.get("id")]
    broker_by_id = {str(item.get("id")): item for item in brokers if item.get("id")}
    json_array_ids = [str(item.get("id")) for item in json_arrays if item.get("id")]
    json_array_by_id = {str(item.get("id")): item for item in json_arrays if item.get("id")}
    datasource_items = st.session_state.get(TEST_EDITOR_DATABASE_DATASOURCES_KEY, [])
    if not isinstance(datasource_items, list):
        datasource_items = []
    datasource_ids = [str(item.get("id")) for item in datasource_items if item.get("id")]
    datasource_by_id = {str(item.get("id")): item for item in datasource_items if item.get("id")}
    database_connection_ids = [
        str(item.get("id")) for item in database_connections if item.get("id")
    ]
    database_connection_by_id = {
        str(item.get("id")): item for item in database_connections if item.get("id")
    }

    st.markdown("**Insert new one**")
    st.text_input(
        "Description",
        key=f"suite_add_operation_description_{dialog_nonce}",
    )
    operation_type = st.selectbox(
        "Operation type",
        options=OPERATION_TYPE_OPTIONS,
        format_func=_operation_type_label,
        key=f"suite_add_operation_type_{dialog_nonce}",
    )

    if operation_type == OPERATION_TYPE_DATA:
        st.text_input(
            "Target",
            key=f"suite_add_operation_target_{dialog_nonce}",
            placeholder=_example_placeholder("actualRows"),
            help="Context path where loaded rows are stored.",
        )
        if f"suite_add_operation_data_payload_{dialog_nonce}" not in st.session_state:
            st.session_state[f"suite_add_operation_data_payload_{dialog_nonce}"] = "[]"
        st.text_area(
            "Data payload",
            key=f"suite_add_operation_data_payload_{dialog_nonce}",
            height=180,
            help="JSON array used as input rows for the test/hook.",
        )
    elif operation_type == OPERATION_TYPE_DATA_FROM_JSON_ARRAY:
        st.text_input(
            "Target",
            key=f"suite_add_operation_target_{dialog_nonce}",
            placeholder=_example_placeholder("expectedRows"),
            help="Context path where loaded rows are stored.",
        )
        select_key = f"suite_add_operation_json_array_id_{dialog_nonce}"
        _normalize_select_key(select_key, json_array_ids or [""])
        st.selectbox(
            "Json array",
            options=json_array_ids or [""],
            format_func=lambda _id: (
                _json_array_label(json_array_by_id.get(_id, {}))
                if _id
                else "Nessun json-array disponibile"
            ),
            key=select_key,
            disabled=not bool(json_array_ids),
        )
    elif operation_type == OPERATION_TYPE_DATA_FROM_DB:
        st.text_input(
            "Target",
            key=f"suite_add_operation_target_{dialog_nonce}",
            placeholder=_example_placeholder("actualRows"),
            help="Context path where loaded rows are stored.",
        )
        select_key = f"suite_add_operation_dataset_id_{dialog_nonce}"
        _normalize_select_key(select_key, datasource_ids or [""])
        st.selectbox(
            "Dataset",
            options=datasource_ids or [""],
            format_func=lambda _id: (
                str(
                    datasource_by_id.get(_id, {}).get("description")
                    or datasource_by_id.get(_id, {}).get("code")
                    or _id
                    or "Nessun dataset disponibile"
                )
            ),
            key=select_key,
            disabled=not bool(datasource_ids),
        )
    elif operation_type == OPERATION_TYPE_DATA_FROM_QUEUE:
        st.text_input(
            "Target",
            key=f"suite_add_operation_target_{dialog_nonce}",
            placeholder=_example_placeholder("incomingMessages"),
            help="Context path where loaded rows are stored.",
        )
        broker_select_key = f"suite_add_operation_broker_id_{dialog_nonce}"
        _normalize_select_key(broker_select_key, broker_ids or [""])
        selected_broker_id = st.selectbox(
            "Broker",
            options=broker_ids or [""],
            format_func=lambda _id: (
                _broker_label(broker_by_id.get(_id, {}))
                if _id
                else "Nessun broker disponibile"
            ),
            key=broker_select_key,
            disabled=not bool(broker_ids),
        )
        queues = (
            load_test_editor_queues_for_broker(selected_broker_id, force=False)
            if selected_broker_id
            else []
        )
        queue_ids = [str(item.get("id")) for item in queues if item.get("id")]
        queue_by_id = {str(item.get("id")): item for item in queues if item.get("id")}
        queue_select_key = f"suite_add_operation_queue_id_{dialog_nonce}"
        _normalize_select_key(queue_select_key, queue_ids or [""])
        st.selectbox(
            "Queue",
            options=queue_ids or [""],
            format_func=lambda _id: (
                _queue_label(queue_by_id.get(_id, {}))
                if _id
                else "Nessuna queue disponibile"
            ),
            key=queue_select_key,
            disabled=not bool(queue_ids),
        )
        st.number_input("Retry", min_value=1, value=3, key=f"suite_add_operation_retry_{dialog_nonce}")
        st.number_input(
            "Wait time seconds",
            min_value=0,
            value=20,
            key=f"suite_add_operation_wait_time_seconds_{dialog_nonce}",
        )
        st.number_input(
            "Max messages",
            min_value=1,
            value=1000,
            key=f"suite_add_operation_max_messages_{dialog_nonce}",
        )
    elif operation_type == OPERATION_TYPE_SLEEP:
        st.number_input(
            "Duration seconds",
            min_value=0,
            value=0,
            key=f"suite_add_operation_sleep_duration_{dialog_nonce}",
        )
    elif operation_type == OPERATION_TYPE_PUBLISH:
        st.text_input(
            "Result target (optional)",
            key=f"suite_add_operation_result_target_{dialog_nonce}",
            placeholder=_example_placeholder("publishResult"),
            help="Optional context path to store technical output.",
        )
        broker_select_key = f"suite_add_operation_broker_id_{dialog_nonce}"
        _normalize_select_key(broker_select_key, broker_ids or [""])
        selected_broker_id = st.selectbox(
            "Broker",
            options=broker_ids or [""],
            format_func=lambda _id: (
                _broker_label(broker_by_id.get(_id, {}))
                if _id
                else "Nessun broker disponibile"
            ),
            key=broker_select_key,
            disabled=not bool(broker_ids),
        )
        queues = (
            load_test_editor_queues_for_broker(selected_broker_id, force=False)
            if selected_broker_id
            else []
        )
        queue_ids = [str(item.get("id")) for item in queues if item.get("id")]
        queue_by_id = {str(item.get("id")): item for item in queues if item.get("id")}
        queue_select_key = f"suite_add_operation_queue_id_{dialog_nonce}"
        _normalize_select_key(queue_select_key, queue_ids or [""])
        st.selectbox(
            "Queue",
            options=queue_ids or [""],
            format_func=lambda _id: (
                _queue_label(queue_by_id.get(_id, {}))
                if _id
                else "Nessuna queue disponibile"
            ),
            key=queue_select_key,
            disabled=not bool(queue_ids),
        )
        if not broker_ids:
            st.info("Nessun broker configurato.")
        elif selected_broker_id and not queue_ids:
            st.info("Nessuna queue configurata per il broker selezionato.")
    elif operation_type == OPERATION_TYPE_SAVE_INTERNAL_DB:
        st.text_input(
            "Table name",
            key=f"suite_add_operation_internal_table_name_{dialog_nonce}",
        )
        st.text_input(
            "Result target (optional)",
            key=f"suite_add_operation_result_target_{dialog_nonce}",
            placeholder=_example_placeholder("writeDbResult"),
            help="Optional context path to store technical output.",
        )
    elif operation_type == OPERATION_TYPE_SAVE_EXTERNAL_DB:
        connection_select_key = f"suite_add_operation_connection_id_{dialog_nonce}"
        _normalize_select_key(connection_select_key, database_connection_ids or [""])
        st.selectbox(
            "Connection",
            options=database_connection_ids or [""],
            format_func=lambda _id: (
                _connection_label(database_connection_by_id.get(_id, {}))
                if _id
                else "Nessuna connection disponibile"
            ),
            key=connection_select_key,
            disabled=not bool(database_connection_ids),
        )
        st.text_input(
            "Table name",
            key=f"suite_add_operation_external_table_name_{dialog_nonce}",
        )
        st.text_input(
            "Result target (optional)",
            key=f"suite_add_operation_result_target_{dialog_nonce}",
            placeholder=_example_placeholder("writeDbResult"),
            help="Optional context path to store technical output.",
        )
        if not database_connection_ids:
            st.info("Nessuna connection database configurata.")
    elif operation_type == OPERATION_TYPE_ASSERT:
        st.text_input(
            "Error message",
            key=f"suite_add_operation_assert_error_message_{dialog_nonce}",
            placeholder="Optional custom failure message",
        )
        object_type_key = f"suite_add_operation_assert_object_type_{dialog_nonce}"
        _normalize_select_key(object_type_key, ASSERT_OBJECT_TYPE_OPTIONS)
        st.selectbox(
            "Evaluated object type",
            options=ASSERT_OBJECT_TYPE_OPTIONS,
            format_func=_assert_object_type_label,
            key=object_type_key,
            disabled=True,
        )

        assert_type_key = f"suite_add_operation_assert_type_{dialog_nonce}"
        _normalize_select_key(assert_type_key, ASSERT_TYPE_OPTIONS)
        selected_assert_type = st.selectbox(
            "Assert type",
            options=ASSERT_TYPE_OPTIONS,
            format_func=_assert_type_label,
            key=assert_type_key,
        )

        if selected_assert_type == ASSERT_TYPE_SCHEMA_VALIDATION:
            schema_key = f"suite_add_operation_assert_schema_{dialog_nonce}"
            if schema_key not in st.session_state:
                st.session_state[schema_key] = "{}"
            st.text_area(
                "Json schema",
                key=schema_key,
                height=220,
            )
            if st.button(
                "Beautify schema",
                key=f"suite_add_operation_assert_schema_beautify_{dialog_nonce}",
                icon=":material/auto_fix_high:",
                type="secondary",
                use_container_width=True,
            ):
                schema, parse_error = _parse_json_dict(st.session_state.get(schema_key))
                if parse_error:
                    st.error(parse_error)
                else:
                    st.session_state[schema_key] = _pretty_json(schema or {})

        if selected_assert_type in {ASSERT_TYPE_CONTAINS, ASSERT_TYPE_JSON_ARRAY_EQUALS}:
            expected_key = (
                f"suite_add_operation_assert_expected_json_array_id_{dialog_nonce}"
            )
            _normalize_select_key(expected_key, json_array_ids or [""])
            selected_expected_id = st.selectbox(
                "Expected json-array",
                options=json_array_ids or [""],
                format_func=lambda _id: (
                    _json_array_label(json_array_by_id.get(_id, {}))
                    if _id
                    else "Nessun json-array disponibile"
                ),
                key=expected_key,
                disabled=not bool(json_array_ids),
            )
            compare_keys_key = f"suite_add_operation_assert_compare_keys_{dialog_nonce}"
            st.text_input(
                "Compare keys",
                key=compare_keys_key,
                placeholder="id, description",
                help="Comma-separated keys used for order-insensitive comparison.",
            )
            if not json_array_ids:
                st.info("Nessun json-array configurato.")
            else:
                selected_expected = json_array_by_id.get(selected_expected_id, {})
                st.markdown("**Expected json-array preview**")
                st.json(selected_expected.get("payload") or [], expanded=False)
        elif selected_assert_type == ASSERT_TYPE_EQUALS:
            st.text_area(
                "Actual",
                key=f"suite_add_operation_assert_actual_{dialog_nonce}",
                height=120,
                help="JSON or plain text value.",
            )
            st.text_area(
                "Expected",
                key=f"suite_add_operation_assert_expected_{dialog_nonce}",
                height=120,
                help="JSON or plain text value.",
            )
    elif operation_type == OPERATION_TYPE_RUN_SUITE:
        st.text_input(
            "Suite id",
            key=f"suite_add_operation_run_suite_id_{dialog_nonce}",
            placeholder="test suite uuid",
        )
        st.text_input(
            "Result target (optional)",
            key=f"suite_add_operation_result_target_{dialog_nonce}",
            placeholder=_example_placeholder("triggeredSuite"),
            help="Optional context path to store technical output.",
        )
    elif operation_type == OPERATION_TYPE_READ_API:
        st.text_input(
            "URL",
            key=f"suite_add_operation_read_api_url_{dialog_nonce}",
            placeholder="https://api.example.com/orders",
        )
        st.text_input(
            "Result target (optional)",
            key=f"suite_add_operation_result_target_{dialog_nonce}",
            placeholder=_example_placeholder("readApiResult"),
            help="Optional context path to store technical output.",
        )
    elif operation_type == OPERATION_TYPE_WRITE_API:
        st.selectbox(
            "Method",
            options=["POST", "PUT", "PATCH", "DELETE"],
            key=f"suite_add_operation_write_api_method_{dialog_nonce}",
        )
        st.text_input(
            "URL",
            key=f"suite_add_operation_write_api_url_{dialog_nonce}",
            placeholder="https://api.example.com/orders",
        )
        st.text_input(
            "Result target (optional)",
            key=f"suite_add_operation_result_target_{dialog_nonce}",
            placeholder=_example_placeholder("writeApiResult"),
            help="Optional context path to store technical output.",
        )
    elif operation_type == OPERATION_TYPE_SET_VAR:
        st.text_input(
            "Key",
            key=f"suite_add_operation_set_var_key_{dialog_nonce}",
            placeholder="context variable name",
        )
        st.selectbox(
            "Scope",
            options=["auto", "local", "global"],
            key=f"suite_add_operation_set_var_scope_{dialog_nonce}",
        )
        st.text_area(
            "Value",
            key=f"suite_add_operation_set_var_value_{dialog_nonce}",
            height=140,
            help="JSON or plain text value to store in context.",
        )
    elif operation_type == OPERATION_TYPE_SET_RESPONSE_STATUS:
        st.number_input(
            "Response status",
            min_value=100,
            max_value=599,
            value=200,
            key=f"suite_add_operation_response_status_{dialog_nonce}",
        )
    elif operation_type == OPERATION_TYPE_SET_RESPONSE_HEADER:
        st.text_input(
            "Header name",
            key=f"suite_add_operation_response_header_name_{dialog_nonce}",
            placeholder="Content-Type",
        )
        st.text_area(
            "Header value",
            key=f"suite_add_operation_response_header_value_{dialog_nonce}",
            height=100,
            help="JSON or plain text value.",
        )
    elif operation_type == OPERATION_TYPE_SET_RESPONSE_BODY:
        st.text_area(
            "Response body",
            key=f"suite_add_operation_response_body_{dialog_nonce}",
            height=160,
            help="JSON or plain text value.",
        )
    elif operation_type == OPERATION_TYPE_BUILD_RESPONSE_FROM_TEMPLATE:
        st.number_input(
            "Response status (optional)",
            min_value=100,
            max_value=599,
            value=200,
            key=f"suite_add_operation_response_template_status_{dialog_nonce}",
        )
        st.text_area(
            "Response headers (JSON object)",
            key=f"suite_add_operation_response_template_headers_{dialog_nonce}",
            height=120,
            help="Optional headers object.",
        )
        st.text_area(
            "Response template",
            key=f"suite_add_operation_response_template_{dialog_nonce}",
            height=180,
            help="JSON or plain text template.",
        )

    if st.button(
        "Add operation",
        key=f"suite_add_operation_add_local_{dialog_nonce}",
        icon=":material/add_circle:",
        type="secondary",
        use_container_width=True,
    ):
        payload, validation_error = build_operation_creation_payload(dialog_nonce)
        if validation_error:
            st.error(validation_error)
            return
        append_operation_to_test(
            suite_test,
            build_draft_operation_from_creation_payload(payload or {}),
        )
        close_add_test_operation_dialog_fn()
        st.session_state[SUITE_FEEDBACK_KEY] = "Nuova operation aggiunta."
        _persist_suite_changes(persist_suite_changes_fn)


def render_add_test_operation_dialog(
    draft: dict,
    close_add_test_operation_dialog_fn,
    persist_suite_changes_fn=None,
):
    dialog_nonce = int(st.session_state.get(ADD_TEST_OPERATION_DIALOG_NONCE_KEY, 0))
    suite_test = _resolve_target_test_for_operation_dialog(
        draft,
        dialog_nonce,
        close_add_test_operation_dialog_fn,
    )
    if not isinstance(suite_test, dict):
        return

    _render_new_operation_form_panel(
        suite_test,
        close_add_test_operation_dialog_fn,
        dialog_nonce,
        persist_suite_changes_fn=persist_suite_changes_fn,
    )

    st.divider()
    footer_cols = st.columns([1, 1], gap="large", vertical_alignment="center")
    with footer_cols[1]:
        if st.button(
            "Cancel",
            key=f"suite_add_operation_cancel_dialog_{dialog_nonce}",
            use_container_width=True,
        ):
            close_add_test_operation_dialog_fn()
            st.rerun()


def render_import_test_operation_dialog(
    draft: dict,
    close_add_test_operation_dialog_fn,
):
    render_add_test_operation_dialog(
        draft,
        close_add_test_operation_dialog_fn,
    )


def render_add_new_test_operation_dialog(draft: dict, close_add_test_operation_dialog_fn):
    render_add_test_operation_dialog(
        draft,
        close_add_test_operation_dialog_fn,
    )
