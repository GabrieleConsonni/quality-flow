import json
from copy import deepcopy
from uuid import uuid4
from xml.dom import minidom

import streamlit as st

from elaborations_shared.components.auth_editor import (
    collect_auth_mode_value,
    collect_auth_editor_value,
    initialize_auth_mode_state,
    initialize_auth_editor_state,
    normalize_authorization_config,
    render_auth_mode_editor,
    render_auth_editor,
)
from mock_servers.services.data_loader_service import MOCK_SERVERS_KEY, load_mock_servers
from mock_servers.services.mock_server_api_service import (
    activate_mock_server,
    deactivate_mock_server,
    get_mock_server_by_id,
    update_mock_server,
)
from mock_servers.services.openapi_import_service import import_openapi_json
from mock_servers.services.state_keys import (
    MOCK_SERVER_EDITOR_ADD_OPERATION_SCOPE_KEY,
    MOCK_SERVER_EDITOR_DRAFT_KEY,
    MOCK_SERVER_EDITOR_FEEDBACK_KEY,
    MOCK_SERVER_EDITOR_NONCE_KEY,
    SELECTED_MOCK_SERVER_ID_KEY,
)
from elaborations_shared.components.kv_editor import (
    ensure_kv_editor_state,
    render_kv_rows_container,
    rows_to_dict,
)
from elaborations_shared.components.test_command_component import (
    render_add_test_operation_dialog,
    render_operation_component,
)
from elaborations_shared.services.data_loader_service import (
    load_test_editor_brokers,
    load_test_editor_queues_for_broker,
)
from elaborations_shared.services.state_keys import (
    ADD_TEST_OPERATION_DIALOG_NONCE_KEY,
    ADD_TEST_OPERATION_DIALOG_OPEN_KEY,
    ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY,
    TEST_EDITOR_BROKERS_KEY,
)

MOCK_SERVERS_PAGE_PATH = "pages/MockServers.py"
HTTP_METHOD_OPTIONS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
API_PRE_RESPONSE_OPERATIONS_KEY = "pre_response_commands"
API_RESPONSE_OPERATIONS_KEY = "response_operations"
API_POST_RESPONSE_OPERATIONS_KEY = "post_response_commands"
BODY_TYPE_ANY = "any"
BODY_TYPE_STRING = "string"
BODY_TYPE_JSON = "json"
BODY_TYPE_XML = "xml"
BODY_TYPE_OPTIONS = [BODY_TYPE_ANY, BODY_TYPE_STRING, BODY_TYPE_JSON, BODY_TYPE_XML]


def _new_ui_key() -> str:
    return uuid4().hex[:10]


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
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


def _normalize_endpoint(raw_value: object) -> str:
    return str(raw_value or "").strip().strip("/")


def _normalize_path(raw_value: object) -> str:
    path = str(raw_value or "").strip()
    if not path:
        return "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def _pretty_json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True)


def _normalized_server_auth(server_item: dict) -> dict:
    cfg = (
        server_item.get("configuration_json")
        if isinstance(server_item.get("configuration_json"), dict)
        else {}
    )
    return normalize_authorization_config(cfg.get("authorization") or {})


def _normalized_api_auth_cfg(cfg: dict) -> dict:
    normalized = {**cfg}
    normalized["authorization"] = normalize_authorization_config(cfg.get("authorization") or {})
    auth_mode = str(cfg.get("authMode") or "").strip()
    if auth_mode not in {"inherit", "none", "custom"}:
        auth_mode = "custom" if normalized["authorization"] else "inherit"
    normalized["authMode"] = auth_mode
    return normalized





def _parse_json_dict(
    raw_value: str,
    *,
    field_label: str,
    allow_empty: bool = True,
) -> tuple[dict | None, str | None]:
    raw_text = str(raw_value or "").strip()
    if not raw_text:
        if allow_empty:
            return {}, None
        return None, f"{field_label}: valore obbligatorio."
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, f"{field_label}: JSON non valido ({str(exc)})."
    if not isinstance(parsed, dict):
        return None, f"{field_label}: deve essere un oggetto JSON."
    return parsed, None


def _body_type_label(body_type: str) -> str:
    if body_type == BODY_TYPE_ANY:
        return "Any"
    if body_type == BODY_TYPE_STRING:
        return "String"
    if body_type == BODY_TYPE_JSON:
        return "JSON"
    if body_type == BODY_TYPE_XML:
        return "XML"
    return str(body_type or "")


def _infer_body_type(body_value: object) -> str:
    if body_value is None:
        return BODY_TYPE_ANY
    if isinstance(body_value, str):
        stripped = body_value.strip()
        if stripped.upper() == "ANY":
            return BODY_TYPE_ANY
        if stripped.startswith("<") and stripped.endswith(">"):
            return BODY_TYPE_XML
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, (dict, list)):
                return BODY_TYPE_JSON
        except json.JSONDecodeError:
            pass
        return BODY_TYPE_STRING
    if isinstance(body_value, (dict, list)):
        return BODY_TYPE_JSON
    return BODY_TYPE_JSON


def _normalize_body_text_for_type(body_value: object, body_type: str) -> str:
    if body_type == BODY_TYPE_ANY:
        return ""
    if body_type == BODY_TYPE_JSON:
        if body_value is None:
            return "{}"
        if isinstance(body_value, str):
            raw = body_value.strip()
            if not raw:
                return "{}"
            try:
                return _pretty_json(json.loads(raw))
            except json.JSONDecodeError:
                return raw
        return _pretty_json(body_value)
    if body_type == BODY_TYPE_XML:
        return str(body_value or "")
    return str(body_value or "")


def _body_editor_keys(api_ui_key: str, nonce: int, scope: str) -> tuple[str, str]:
    key_prefix = f"mock_server_api_{scope}_body_{api_ui_key}_{nonce}"
    return f"{key_prefix}_type", f"{key_prefix}_value"


def _body_editor_source_key(api_ui_key: str, nonce: int, scope: str) -> str:
    return f"mock_server_api_{scope}_body_source_{api_ui_key}_{nonce}"


def _ensure_body_editor_state(api_entry: dict, api_ui_key: str, nonce: int, scope: str):
    cfg = (
        api_entry.get("configuration_json")
        if isinstance(api_entry.get("configuration_json"), dict)
        else {}
    )
    value_key_name = "body" if scope == "expected" else "response_body"
    type_key_name = "body_type" if scope == "expected" else "response_body_type"
    raw_value = cfg.get(value_key_name)
    configured_type = str(cfg.get(type_key_name) or "").strip().lower()
    inferred_type = configured_type if configured_type in BODY_TYPE_OPTIONS else _infer_body_type(raw_value)
    state_type_key, state_value_key = _body_editor_keys(api_ui_key, nonce, scope)
    source_state_key = _body_editor_source_key(api_ui_key, nonce, scope)
    source_signature = json.dumps(
        {
            "body_type": inferred_type,
            "body_value": raw_value,
        },
        default=str,
        sort_keys=True,
        ensure_ascii=True,
    )
    if (
        state_type_key not in st.session_state
        or state_value_key not in st.session_state
        or st.session_state.get(source_state_key) != source_signature
    ):
        st.session_state[state_type_key] = inferred_type
        st.session_state[state_value_key] = _normalize_body_text_for_type(raw_value, inferred_type)
        st.session_state[source_state_key] = source_signature


def _beautify_body_text(body_type: str, raw_value: str) -> tuple[str | None, str | None]:
    if body_type == BODY_TYPE_JSON:
        raw_text = str(raw_value or "").strip()
        if not raw_text:
            return "{}", None
        try:
            return _pretty_json(json.loads(raw_text)), None
        except json.JSONDecodeError as exc:
            return None, f"Body JSON non valido: {str(exc)}"
    if body_type == BODY_TYPE_XML:
        raw_text = str(raw_value or "").strip()
        if not raw_text:
            return "", None
        try:
            parsed = minidom.parseString(raw_text)
            pretty = parsed.toprettyxml(indent="  ")
            lines = [line for line in pretty.splitlines() if line.strip()]
            return "\n".join(lines), None
        except Exception as exc:
            return None, f"Body XML non valido: {str(exc)}"
    return str(raw_value or ""), None


def _resolve_body_from_state(
    api_ui_key: str,
    nonce: int,
    scope: str,
) -> tuple[object | None, str, str | None]:
    state_type_key, state_value_key = _body_editor_keys(api_ui_key, nonce, scope)
    body_type = str(st.session_state.get(state_type_key) or BODY_TYPE_ANY).strip().lower()
    if body_type not in BODY_TYPE_OPTIONS:
        body_type = BODY_TYPE_ANY
    raw_value = str(st.session_state.get(state_value_key) or "")
    if body_type == BODY_TYPE_ANY:
        # For request matching ANY is explicit. For response body, None means no body.
        return ("ANY" if scope == "expected" else None), body_type, None
    if body_type == BODY_TYPE_JSON:
        stripped = raw_value.strip()
        if not stripped:
            return None, body_type, "Body JSON obbligatorio."
        try:
            return json.loads(stripped), body_type, None
        except json.JSONDecodeError as exc:
            return None, body_type, f"Body JSON non valido: {str(exc)}"
    if body_type == BODY_TYPE_XML:
        value = raw_value
        if not value.strip():
            return None, body_type, "Body XML obbligatorio."
        return value, body_type, None
    value = raw_value
    if not value.strip():
        return None, body_type, "Body string obbligatorio."
    return value, body_type, None


def _operation_payload(operation: dict) -> dict:
    cfg = operation.get("configuration_json") if isinstance(operation.get("configuration_json"), dict) else {}
    return {
        "order": _safe_int(operation.get("order"), 0),
        "description": str(operation.get("description") or ""),
        "cfg": cfg,
    }


def _api_operations_list(api_entry: dict, scope_key: str) -> list[dict]:
    if not isinstance(api_entry, dict):
        return []
    operations = api_entry.get(scope_key)
    if isinstance(operations, list):
        return operations
    if scope_key == API_POST_RESPONSE_OPERATIONS_KEY:
        legacy_operations = api_entry.get("operations")
        if isinstance(legacy_operations, list):
            return legacy_operations
    return []


def _api_payload(api_entry: dict) -> dict:
    cfg = api_entry.get("configuration_json") if isinstance(api_entry.get("configuration_json"), dict) else {}
    cfg = _normalized_api_auth_cfg(cfg)
    method = str(cfg.get("method") or api_entry.get("method") or "GET").strip().upper()
    if method not in HTTP_METHOD_OPTIONS:
        method = "GET"
    pre_response_operations_payload = [
        _operation_payload(item)
        for item in _api_operations_list(api_entry, API_PRE_RESPONSE_OPERATIONS_KEY)
        if isinstance(item, dict)
    ]
    response_operations_payload = [
        _operation_payload(item)
        for item in _api_operations_list(api_entry, API_RESPONSE_OPERATIONS_KEY)
        if isinstance(item, dict)
    ]
    post_response_operations_payload = [
        _operation_payload(item)
        for item in _api_operations_list(api_entry, API_POST_RESPONSE_OPERATIONS_KEY)
        if isinstance(item, dict)
    ]
    cfg = {
        **cfg,
        "method": method,
        "path": _normalize_path(cfg.get("path") or api_entry.get("path")),
        API_PRE_RESPONSE_OPERATIONS_KEY: pre_response_operations_payload,
        API_RESPONSE_OPERATIONS_KEY: response_operations_payload,
        API_POST_RESPONSE_OPERATIONS_KEY: post_response_operations_payload,
    }
    return {
        "order": _safe_int(api_entry.get("order"), 0),
        "description": str(api_entry.get("description") or ""),
        "cfg": cfg,
        "commands": post_response_operations_payload,
    }


def _queue_payload(queue_entry: dict) -> dict:
    cfg = queue_entry.get("configuration_json") if isinstance(queue_entry.get("configuration_json"), dict) else {}
    return {
        "order": _safe_int(queue_entry.get("order"), 0),
        "description": str(queue_entry.get("description") or ""),
        "queue_id": str(queue_entry.get("queue_id") or "").strip(),
        "cfg": cfg,
        "commands": [
            _operation_payload(item)
            for item in (queue_entry.get("operations") or [])
            if isinstance(item, dict)
        ],
    }


def _validate_draft(draft: dict) -> str | None:
    if not str(draft.get("id") or "").strip():
        return "Mock server non valido."
    if not str(draft.get("description") or "").strip():
        return "Il campo Description e' obbligatorio."
    if not _normalize_endpoint(draft.get("endpoint")):
        return "Il campo Endpoint e' obbligatorio."

    for idx, api_entry in enumerate(draft.get("apis") or []):
        if not str(api_entry.get("description") or "").strip():
            return f"API #{idx + 1}: description obbligatoria."
        cfg = api_entry.get("configuration_json") if isinstance(api_entry.get("configuration_json"), dict) else {}
        method = str(cfg.get("method") or "").strip().upper()
        if method not in HTTP_METHOD_OPTIONS:
            return f"API #{idx + 1}: method non valido."
        if not _normalize_path(cfg.get("path")):
            return f"API #{idx + 1}: path obbligatorio."
        pre_operations = _api_operations_list(api_entry, API_PRE_RESPONSE_OPERATIONS_KEY)
        response_operations = _api_operations_list(api_entry, API_RESPONSE_OPERATIONS_KEY)
        post_operations = _api_operations_list(api_entry, API_POST_RESPONSE_OPERATIONS_KEY)
        for op_idx, operation in enumerate(pre_operations):
            if not str(operation.get("description") or "").strip():
                return f"API #{idx + 1}, pre-operation #{op_idx + 1}: description obbligatoria."
            operation_cfg = (
                operation.get("configuration_json")
                if isinstance(operation.get("configuration_json"), dict)
                else {}
            )
            if not str(operation_cfg.get("operationType") or "").strip():
                return f"API #{idx + 1}, pre-operation #{op_idx + 1}: operationType obbligatorio."

        for op_idx, operation in enumerate(response_operations):
            if not str(operation.get("description") or "").strip():
                return f"API #{idx + 1}, response-operation #{op_idx + 1}: description obbligatoria."
            operation_cfg = (
                operation.get("configuration_json")
                if isinstance(operation.get("configuration_json"), dict)
                else {}
            )
            if not str(operation_cfg.get("operationType") or "").strip():
                return f"API #{idx + 1}, response-operation #{op_idx + 1}: operationType obbligatorio."

        for op_idx, operation in enumerate(post_operations):
            if not str(operation.get("description") or "").strip():
                return f"API #{idx + 1}, post-operation #{op_idx + 1}: description obbligatoria."
            operation_cfg = (
                operation.get("configuration_json")
                if isinstance(operation.get("configuration_json"), dict)
                else {}
            )
            if not str(operation_cfg.get("operationType") or "").strip():
                return f"API #{idx + 1}, post-operation #{op_idx + 1}: operationType obbligatorio."

    for idx, queue_entry in enumerate(draft.get("queues") or []):
        if not str(queue_entry.get("description") or "").strip():
            return f"Queue #{idx + 1}: description obbligatoria."
        if not str(queue_entry.get("queue_id") or "").strip():
            return f"Queue #{idx + 1}: queue obbligatoria."
        for op_idx, operation in enumerate(queue_entry.get("operations") or []):
            if not str(operation.get("description") or "").strip():
                return f"Queue #{idx + 1}, operation #{op_idx + 1}: description obbligatoria."
            operation_cfg = (
                operation.get("configuration_json")
                if isinstance(operation.get("configuration_json"), dict)
                else {}
            )
            if not str(operation_cfg.get("operationType") or "").strip():
                return f"Queue #{idx + 1}, operation #{op_idx + 1}: operationType obbligatorio."
    return None


def _server_payload(draft: dict) -> dict:
    return {
        "id": str(draft.get("id") or "").strip(),
        "description": str(draft.get("description") or ""),
        "cfg": {
            "endpoint": _normalize_endpoint(draft.get("endpoint")),
            "authorization": normalize_authorization_config(draft.get("authorization") or {}),
        },
        "apis": [
            _api_payload(api_entry)
            for api_entry in (draft.get("apis") or [])
            if isinstance(api_entry, dict)
        ],
        "queues": [
            _queue_payload(queue_entry)
            for queue_entry in (draft.get("queues") or [])
            if isinstance(queue_entry, dict)
        ],
        "is_active": bool(draft.get("is_active")),
    }


def _operation_from_api_payload(operation: dict, op_idx: int) -> dict:
    cfg = (
        operation.get("configuration_json")
        if isinstance(operation.get("configuration_json"), dict)
        else (
            operation.get("cfg")
            if isinstance(operation.get("cfg"), dict)
            else {}
        )
    )
    return {
        "id": operation.get("id"),
        "order": _safe_int(operation.get("order"), op_idx + 1),
        "description": str(operation.get("description") or ""),
        "operation_type": str(operation.get("operation_type") or cfg.get("operationType") or ""),
        "configuration_json": cfg,
        "_ui_key": _new_ui_key(),
    }


def _api_from_server_payload(api_entry: dict, api_idx: int) -> dict:
    cfg = api_entry.get("configuration_json") if isinstance(api_entry.get("configuration_json"), dict) else {}
    method = str(cfg.get("method") or api_entry.get("method") or "GET").strip().upper()
    path = _normalize_path(cfg.get("path") or api_entry.get("path"))
    cfg = _normalized_api_auth_cfg({**cfg, "method": method, "path": path})
    operations = [
        _operation_from_api_payload(operation, op_idx)
        for op_idx, operation in enumerate(api_entry.get("operations") or [])
        if isinstance(operation, dict)
    ]
    pre_response_operations = [
        _operation_from_api_payload(operation, op_idx)
        for op_idx, operation in enumerate(cfg.get(API_PRE_RESPONSE_OPERATIONS_KEY) or [])
        if isinstance(operation, dict)
    ]
    response_operations = [
        _operation_from_api_payload(operation, op_idx)
        for op_idx, operation in enumerate(cfg.get(API_RESPONSE_OPERATIONS_KEY) or [])
        if isinstance(operation, dict)
    ]
    post_response_operations = [
        _operation_from_api_payload(operation, op_idx)
        for op_idx, operation in enumerate(cfg.get(API_POST_RESPONSE_OPERATIONS_KEY) or [])
        if isinstance(operation, dict)
    ]
    if not post_response_operations and operations:
        post_response_operations = deepcopy(operations)
    return {
        "id": api_entry.get("id"),
        "order": _safe_int(api_entry.get("order"), api_idx + 1),
        "description": str(api_entry.get("description") or ""),
        "method": method,
        "path": path,
        "configuration_json": cfg,
        "operations": deepcopy(post_response_operations),
        API_PRE_RESPONSE_OPERATIONS_KEY: pre_response_operations,
        API_RESPONSE_OPERATIONS_KEY: response_operations,
        API_POST_RESPONSE_OPERATIONS_KEY: post_response_operations,
        "_ui_key": _new_ui_key(),
    }


def _queue_from_server_payload(queue_entry: dict, queue_idx: int) -> dict:
    cfg = queue_entry.get("configuration_json") if isinstance(queue_entry.get("configuration_json"), dict) else {}
    operations = [
        _operation_from_api_payload(operation, op_idx)
        for op_idx, operation in enumerate(queue_entry.get("operations") or [])
        if isinstance(operation, dict)
    ]
    return {
        "id": queue_entry.get("id"),
        "order": _safe_int(queue_entry.get("order"), queue_idx + 1),
        "description": str(queue_entry.get("description") or ""),
        "queue_id": str(queue_entry.get("queue_id") or ""),
        "configuration_json": cfg,
        "operations": operations,
        "_ui_key": _new_ui_key(),
    }


def _build_server_draft(server_item: dict) -> dict:
    apis = [
        _api_from_server_payload(api_entry, api_idx)
        for api_idx, api_entry in enumerate(server_item.get("apis") or [])
        if isinstance(api_entry, dict)
    ]
    queues = [
        _queue_from_server_payload(queue_entry, queue_idx)
        for queue_idx, queue_entry in enumerate(server_item.get("queues") or [])
        if isinstance(queue_entry, dict)
    ]
    apis.sort(key=lambda item: _safe_int(item.get("order"), 0))
    queues.sort(key=lambda item: _safe_int(item.get("order"), 0))
    return {
        "id": str(server_item.get("id") or ""),
        "description": str(server_item.get("description") or ""),
        "endpoint": _normalize_endpoint(server_item.get("endpoint")),
        "authorization": _normalized_server_auth(server_item),
        "is_active": bool(server_item.get("is_active")),
        "apis": apis,
        "queues": queues,
    }


def _draft_api_routes(draft: dict) -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for api_entry in draft.get("apis") or []:
        if not isinstance(api_entry, dict):
            continue
        cfg = (
            api_entry.get("configuration_json")
            if isinstance(api_entry.get("configuration_json"), dict)
            else {}
        )
        method = str(cfg.get("method") or api_entry.get("method") or "").strip().upper()
        path = _normalize_path(cfg.get("path") or api_entry.get("path"))
        if method and path:
            routes.add((method, path))
    return routes


def _append_imported_apis(draft: dict, imported_apis: list[dict]):
    apis = draft.setdefault("apis", [])
    max_order = max(
        (_safe_int(api_entry.get("order"), 0) for api_entry in apis if isinstance(api_entry, dict)),
        default=0,
    )
    for index, imported_api in enumerate(imported_apis, start=1):
        if not isinstance(imported_api, dict):
            continue
        imported_payload = deepcopy(imported_api)
        imported_payload["order"] = max_order + index
        apis.append(_api_from_server_payload(imported_payload, len(apis)))
    draft["apis"] = sorted(
        [api_entry for api_entry in apis if isinstance(api_entry, dict)],
        key=lambda item: _safe_int(item.get("order"), 0),
    )


def _find_server_by_id(mock_server_id: str) -> dict | None:
    server_id = str(mock_server_id or "").strip()
    if not server_id:
        return None
    servers = st.session_state.get(MOCK_SERVERS_KEY, [])
    if isinstance(servers, list):
        for server in servers:
            if not isinstance(server, dict):
                continue
            if str(server.get("id") or "").strip() == server_id:
                return server
    try:
        payload = get_mock_server_by_id(server_id)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_selected_server_id() -> str:
    selected_id = str(st.session_state.get(SELECTED_MOCK_SERVER_ID_KEY) or "").strip()
    if selected_id:
        return selected_id

    servers = st.session_state.get(MOCK_SERVERS_KEY, [])
    if not isinstance(servers, list):
        return ""
    for server in servers:
        if not isinstance(server, dict):
            continue
        server_id = str(server.get("id") or "").strip()
        if server_id:
            st.session_state[SELECTED_MOCK_SERVER_ID_KEY] = server_id
            return server_id
    return ""


def _ensure_editor_draft():
    load_mock_servers(force=False)
    selected_id = _resolve_selected_server_id()
    current_draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not selected_id:
        st.session_state[MOCK_SERVER_EDITOR_DRAFT_KEY] = None
        return
    if isinstance(current_draft, dict) and str(current_draft.get("id") or "") == selected_id:
        return
    server_item = _find_server_by_id(selected_id)
    if not isinstance(server_item, dict):
        st.session_state[MOCK_SERVER_EDITOR_DRAFT_KEY] = None
        return
    st.session_state[MOCK_SERVER_EDITOR_DRAFT_KEY] = _build_server_draft(server_item)
    st.session_state[MOCK_SERVER_EDITOR_NONCE_KEY] = int(
        st.session_state.get(MOCK_SERVER_EDITOR_NONCE_KEY, 0)
    ) + 1


def _persist_draft(*, should_rerun: bool, success_message: str = "Mock server aggiornato."):
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Nessun mock server selezionato.")
        return

    validation_error = _validate_draft(draft)
    if validation_error:
        st.error(validation_error)
        return

    try:
        update_mock_server(_server_payload(draft))
    except Exception as exc:
        st.error(f"Errore aggiornamento mock server: {str(exc)}")
        return

    load_mock_servers(force=True)
    refreshed = _find_server_by_id(str(draft.get("id") or ""))
    if isinstance(refreshed, dict):
        st.session_state[MOCK_SERVER_EDITOR_DRAFT_KEY] = _build_server_draft(refreshed)
    st.session_state[MOCK_SERVER_EDITOR_FEEDBACK_KEY] = success_message
    st.session_state[MOCK_SERVER_EDITOR_NONCE_KEY] = int(
        st.session_state.get(MOCK_SERVER_EDITOR_NONCE_KEY, 0)
    ) + 1
    if should_rerun:
        st.rerun()


def _persist_draft_after_change():
    _persist_draft(should_rerun=True)


def _render_server_auth_section(draft: dict) -> None:
    auth_prefix = f"mock_server_default_auth_{str(draft.get('id') or 'new')}"
    initialize_auth_editor_state(auth_prefix, draft.get("authorization") or {})

    section_cols = st.columns([6, 2], gap="small", vertical_alignment="center")
    with section_cols[0]:
        st.subheader("Default Auth")
    with section_cols[1]:
        if st.button(
            "Save auth",
            key=f"{auth_prefix}_save",
            icon=":material/save:",
            use_container_width=True,
        ):
            authorization, auth_error = collect_auth_editor_value(auth_prefix)
            if auth_error:
                st.error(auth_error)
                return
            draft["authorization"] = authorization
            _persist_draft(should_rerun=True, success_message="Mock server default auth updated.")

    render_auth_editor(auth_prefix)


def _render_openapi_import_preview(import_result):
    summary_cols = st.columns(3, gap="small")
    with summary_cols[0]:
        st.metric("Importabili", import_result.imported_count)
    with summary_cols[1]:
        st.metric("Duplicati saltati", len(import_result.skipped_duplicates))
    with summary_cols[2]:
        st.metric("Path templated", len(import_result.templated_paths))

    if import_result.errors:
        for error_message in import_result.errors:
            st.error(error_message)

    if import_result.warnings:
        st.warning("\n".join(f"- {warning}" for warning in import_result.warnings))

    if import_result.skipped_duplicates:
        duplicate_lines = "\n".join(
            f"- {duplicate_route}" for duplicate_route in import_result.skipped_duplicates
        )
        st.info(f"Route duplicate saltate:\n{duplicate_lines}")

    if import_result.apis_to_append:
        preview_lines = []
        for api_entry in import_result.apis_to_append:
            description = str(api_entry.get("description") or "-")
            method = str(api_entry.get("method") or "GET")
            path = _normalize_path(api_entry.get("path"))
            preview_lines.append(f"- `{method} {path}` - {description}")
        st.markdown("**API da importare**")
        st.markdown("\n".join(preview_lines))


@st.dialog("Import OpenAPI JSON", width="large")
def _import_openapi_dialog():
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Mock server non disponibile.")
        return

    dialog_key = str(draft.get("id") or _new_ui_key())
    uploaded_file = st.file_uploader(
        "OpenAPI JSON file",
        type=["json"],
        key=f"mock_server_import_openapi_file_{dialog_key}",
        help="Sono supportati solo file OpenAPI 3.x JSON locali.",
    )
    if not uploaded_file:
        st.caption("Carica un file `.json` OpenAPI 3.x per vedere la preview dell'import.")
        return

    import_result = import_openapi_json(
        uploaded_file.getvalue(),
        existing_routes=_draft_api_routes(draft),
    )
    _render_openapi_import_preview(import_result)

    can_import = bool(import_result.apis_to_append) and not bool(import_result.errors)
    if st.button(
        "Import",
        key=f"mock_server_import_openapi_confirm_{dialog_key}",
        icon=":material/upload_file:",
        use_container_width=True,
        disabled=not can_import,
    ):
        _append_imported_apis(draft, import_result.apis_to_append)
        warning_suffix = ""
        if import_result.templated_paths:
            warning_suffix = (
                f" Path templated importati letteralmente: {len(import_result.templated_paths)}."
            )
        duplicate_suffix = ""
        if import_result.skipped_duplicates:
            duplicate_suffix = (
                f" Duplicati saltati: {len(import_result.skipped_duplicates)}."
            )
        _persist_draft(
            should_rerun=True,
            success_message=(
                f"Import OpenAPI completato: {import_result.imported_count} API aggiunte."
                f"{duplicate_suffix}{warning_suffix}"
            ),
        )


def _load_queue_options() -> tuple[list[dict], dict[str, dict]]:
    load_test_editor_brokers(force=False)
    brokers = st.session_state.get(TEST_EDITOR_BROKERS_KEY, [])
    if not isinstance(brokers, list):
        brokers = []

    queue_options: list[dict] = []
    queue_by_id: dict[str, dict] = {}
    for broker in brokers:
        if not isinstance(broker, dict):
            continue
        broker_id = str(broker.get("id") or "").strip()
        if not broker_id:
            continue
        broker_label = str(broker.get("description") or broker_id)
        queues = load_test_editor_queues_for_broker(broker_id, force=False)
        if not isinstance(queues, list):
            continue
        for queue in queues:
            if not isinstance(queue, dict):
                continue
            queue_id = str(queue.get("id") or "").strip()
            if not queue_id:
                continue
            queue_label = str(queue.get("description") or queue_id)
            option = {
                "broker_id": broker_id,
                "broker_label": broker_label,
                "queue_id": queue_id,
                "queue_label": queue_label,
                "display": f"{broker_label} | {queue_label}",
            }
            queue_options.append(option)
            queue_by_id[queue_id] = option
    return queue_options, queue_by_id


def _open_add_operation_dialog(target_ui_key: str, scope_key: str = "operations"):
    if not target_ui_key:
        return
    st.session_state[ADD_TEST_OPERATION_DIALOG_OPEN_KEY] = True
    st.session_state[ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY] = target_ui_key
    st.session_state[MOCK_SERVER_EDITOR_ADD_OPERATION_SCOPE_KEY] = str(scope_key or "operations")
    st.session_state[ADD_TEST_OPERATION_DIALOG_NONCE_KEY] = int(
        st.session_state.get(ADD_TEST_OPERATION_DIALOG_NONCE_KEY, 0)
    ) + 1


def _close_add_operation_dialog():
    st.session_state[ADD_TEST_OPERATION_DIALOG_OPEN_KEY] = False
    st.session_state.pop(ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY, None)
    st.session_state.pop(MOCK_SERVER_EDITOR_ADD_OPERATION_SCOPE_KEY, None)


def _find_draft_item_by_ui_key(draft: dict, target_ui_key: str) -> dict | None:
    if not isinstance(draft, dict):
        return None
    target_key = str(target_ui_key or "").strip()
    if not target_key:
        return None
    for item in (draft.get("apis") or []) + (draft.get("queues") or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("_ui_key") or "").strip() == target_key:
            return item
    return None


@st.dialog("Add operation", width="large")
def _add_operation_dialog(
    draft: dict,
):
    target_ui_key = str(st.session_state.get(ADD_TEST_OPERATION_DIALOG_TARGET_TEST_UI_KEY) or "").strip()
    target_scope = str(st.session_state.get(MOCK_SERVER_EDITOR_ADD_OPERATION_SCOPE_KEY) or "operations").strip()
    target_item = _find_draft_item_by_ui_key(draft, target_ui_key)
    if not isinstance(target_item, dict):
        st.error("Target non trovato per l'aggiunta operazione.")
        return

    if target_scope not in {
        "operations",
        API_PRE_RESPONSE_OPERATIONS_KEY,
        API_RESPONSE_OPERATIONS_KEY,
        API_POST_RESPONSE_OPERATIONS_KEY,
    }:
        target_scope = "operations"

    if target_scope not in target_item or not isinstance(target_item.get(target_scope), list):
        target_item[target_scope] = []

    pseudo_target = (
        target_item
        if target_scope == "operations"
        else {
            "_ui_key": target_ui_key,
            "operations": target_item[target_scope],
        }
    )
    pseudo_draft = {"tests": [pseudo_target]}
    render_add_test_operation_dialog(
        pseudo_draft,
        _close_add_operation_dialog,
        persist_suite_changes_fn=_persist_draft_after_change,
    )


@st.dialog("Body editor", width="large")
def _body_editor_dialog(api_entry: dict, api_ui_key: str, nonce: int, scope: str):
    if not isinstance(api_entry, dict):
        st.error("API non disponibile.")
        return

    normalized_scope = "expected" if scope == "expected" else "response"
    _ensure_body_editor_state(api_entry, api_ui_key, nonce, normalized_scope)
    state_type_key, state_value_key = _body_editor_keys(api_ui_key, nonce, normalized_scope)

    body_type = st.selectbox(
        "Body type",
        options=BODY_TYPE_OPTIONS,
        format_func=_body_type_label,
        key=state_type_key,
    )
    if body_type != BODY_TYPE_ANY:
        st.text_area(
            "Body",
            key=state_value_key,
            height=280,
        )

    action_cols = st.columns([2, 2], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Beautify",
            key=f"mock_server_api_{normalized_scope}_body_beautify_{api_ui_key}_{nonce}",
            icon=":material/auto_fix_high:",
            type="secondary",
            use_container_width=True,
            disabled=(body_type == BODY_TYPE_ANY),
        ):
            beautified, beautify_error = _beautify_body_text(
                body_type,
                str(st.session_state.get(state_value_key) or ""),
            )
            if beautify_error:
                st.error(beautify_error)
            else:
                st.session_state[state_value_key] = beautified or ""
                st.rerun()
    with action_cols[1]:
        if st.button(
            "Add",
            key=f"mock_server_api_{normalized_scope}_body_add_{api_ui_key}_{nonce}",
            icon=":material/add:",
            use_container_width=True,
        ):
            body_value, resolved_type, resolve_error = _resolve_body_from_state(
                api_ui_key,
                nonce,
                normalized_scope,
            )
            if resolve_error:
                st.error(resolve_error)
                return

            current_cfg = (
                api_entry.get("configuration_json")
                if isinstance(api_entry.get("configuration_json"), dict)
                else {}
            )
            if normalized_scope == "expected":
                api_entry["configuration_json"] = {
                    **current_cfg,
                    "body": body_value,
                    "body_type": resolved_type,
                }
            else:
                api_entry["configuration_json"] = {
                    **current_cfg,
                    "response_body": body_value,
                    "response_body_type": resolved_type,
                }
            _persist_draft(should_rerun=True)

@st.dialog("Add API", width="medium")
def _add_api_dialog():
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Mock server non disponibile.")
        return

    dialog_key = str(draft.get("id") or _new_ui_key())
    st.text_input("Description", key=f"mock_server_add_api_desc_{dialog_key}")
    method = st.selectbox(
        "Method",
        options=HTTP_METHOD_OPTIONS,
        key=f"mock_server_add_api_method_{dialog_key}",
    )
    path = st.text_input(
        "Path",
        key=f"mock_server_add_api_path_{dialog_key}",
        placeholder="/orders",
    )
    if st.button(
        "Add",
        key=f"mock_server_add_api_submit_{dialog_key}",
        icon=":material/add:",
        use_container_width=True,
    ):
        description = str(st.session_state.get(f"mock_server_add_api_desc_{dialog_key}") or "")
        if not description.strip():
            st.error("Il campo Description e' obbligatorio.")
            return
        new_api = {
            "id": None,
            "order": len(draft.get("apis") or []) + 1,
            "description": description,
            "method": str(method or "GET"),
            "path": _normalize_path(path),
            "configuration_json": {
                "method": str(method or "GET"),
                "path": _normalize_path(path),
                "params": {},
                "authMode": "inherit",
                "authorization": {},
                "headers": {},
                "body": None,
                "body_type": BODY_TYPE_ANY,
                "body_match": "contains",
                "response_status": 200,
                "response_headers": {"Content-Type": "application/json"},
                "response_body": {"status": "ok"},
                "response_body_type": BODY_TYPE_JSON,
                "priority": 0,
                API_PRE_RESPONSE_OPERATIONS_KEY: [],
                API_RESPONSE_OPERATIONS_KEY: [],
                API_POST_RESPONSE_OPERATIONS_KEY: [],
            },
            "operations": [],
            API_PRE_RESPONSE_OPERATIONS_KEY: [],
            API_RESPONSE_OPERATIONS_KEY: [],
            API_POST_RESPONSE_OPERATIONS_KEY: [],
            "_ui_key": _new_ui_key(),
        }
        draft.setdefault("apis", []).append(new_api)
        _persist_draft(should_rerun=True)


@st.dialog("Edit API", width="medium")
def _edit_api_dialog(api_entry: dict, api_idx: int):
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Mock server non disponibile.")
        return
    api_ui_key = str(api_entry.get("_ui_key") or _new_ui_key())
    st.number_input(
        "Order",
        min_value=1,
        test=1,
        key=f"mock_server_edit_api_order_{api_ui_key}",
        value=max(_safe_int(api_entry.get("order"), api_idx + 1), 1),
    )
    st.text_input(
        "Description",
        key=f"mock_server_edit_api_desc_{api_ui_key}",
        value=str(api_entry.get("description") or ""),
    )
    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"mock_server_edit_api_save_{api_ui_key}",
            icon=":material/save:",
            use_container_width=True,
        ):
            api_entry["order"] = int(
                st.session_state.get(f"mock_server_edit_api_order_{api_ui_key}") or api_idx + 1
            )
            api_entry["description"] = str(
                st.session_state.get(f"mock_server_edit_api_desc_{api_ui_key}") or ""
            )
            draft["apis"] = sorted(
                draft.get("apis") or [],
                key=lambda item: _safe_int(item.get("order"), 0),
            )
            _persist_draft(should_rerun=True)
    with action_cols[1]:
        if st.button(
            "Delete",
            key=f"mock_server_edit_api_delete_{api_ui_key}",
            icon=":material/delete:",
            use_container_width=True,
        ):
            apis = draft.get("apis") or []
            if 0 <= api_idx < len(apis):
                apis.pop(api_idx)
            _persist_draft(should_rerun=True)


@st.dialog("Copy API", width="medium")
def _copy_api_dialog(
    source_api: dict,
    copied_cfg: dict,
):
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Mock server non disponibile.")
        return

    source_ui_key = str(source_api.get("_ui_key") or _new_ui_key())
    source_description = str(source_api.get("description") or "")
    default_description = (
        f"{source_description} copy"
        if source_description
        else "API copy"
    )

    description_key = f"mock_server_copy_api_desc_{source_ui_key}"
    if description_key not in st.session_state:
        st.session_state[description_key] = default_description

    st.text_input("Description", key=description_key)

    if st.button(
        "Copy API",
        key=f"mock_server_copy_api_confirm_{source_ui_key}",
        icon=":material/content_copy:",
        use_container_width=True,
    ):
        new_description = str(st.session_state.get(description_key) or "")
        if not new_description.strip():
            st.error("Il campo Description e' obbligatorio.")
            return

        def _copy_operations(source_operations: list[dict]) -> list[dict]:
            copied: list[dict] = []
            for op_idx, operation in enumerate(source_operations):
                if not isinstance(operation, dict):
                    continue
                copied.append(
                    {
                        "id": None,
                        "order": _safe_int(operation.get("order"), op_idx + 1),
                        "description": str(operation.get("description") or ""),
                        "operation_type": str(operation.get("operation_type") or ""),
                        "configuration_json": deepcopy(
                            operation.get("configuration_json")
                            if isinstance(operation.get("configuration_json"), dict)
                            else {}
                        ),
                        "_ui_key": _new_ui_key(),
                    }
                )
            return copied

        source_pre_operations = _api_operations_list(source_api, API_PRE_RESPONSE_OPERATIONS_KEY)
        source_response_operations = _api_operations_list(source_api, API_RESPONSE_OPERATIONS_KEY)
        source_post_operations = _api_operations_list(source_api, API_POST_RESPONSE_OPERATIONS_KEY)
        copied_pre_operations = _copy_operations(source_pre_operations)
        copied_response_operations = _copy_operations(source_response_operations)
        copied_post_operations = _copy_operations(source_post_operations)
        if not copied_post_operations:
            copied_post_operations = _copy_operations(source_api.get("operations") or [])

        copied_cfg = deepcopy(copied_cfg if isinstance(copied_cfg, dict) else {})
        copied_cfg[API_PRE_RESPONSE_OPERATIONS_KEY] = [
            _operation_payload(item)
            for item in copied_pre_operations
            if isinstance(item, dict)
        ]
        copied_cfg[API_RESPONSE_OPERATIONS_KEY] = [
            _operation_payload(item)
            for item in copied_response_operations
            if isinstance(item, dict)
        ]
        copied_cfg[API_POST_RESPONSE_OPERATIONS_KEY] = [
            _operation_payload(item)
            for item in copied_post_operations
            if isinstance(item, dict)
        ]

        apis = draft.setdefault("apis", [])
        apis.append(
            {
                "id": None,
                "order": len(apis) + 1,
                "description": new_description,
                "method": str(copied_cfg.get("method") or "GET"),
                "path": _normalize_path(copied_cfg.get("path")),
                "configuration_json": copied_cfg,
                "operations": deepcopy(copied_post_operations),
                API_PRE_RESPONSE_OPERATIONS_KEY: copied_pre_operations,
                API_RESPONSE_OPERATIONS_KEY: copied_response_operations,
                API_POST_RESPONSE_OPERATIONS_KEY: copied_post_operations,
                "_ui_key": _new_ui_key(),
            }
        )
        _persist_draft(should_rerun=True)


@st.dialog("Add Queue", width="medium")
def _add_queue_dialog():
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Mock server non disponibile.")
        return
    queue_options, _ = _load_queue_options()
    option_ids = [str(item.get("queue_id") or "") for item in queue_options if item.get("queue_id")]
    option_by_id = {str(item.get("queue_id")): item for item in queue_options if item.get("queue_id")}

    dialog_key = str(draft.get("id") or _new_ui_key())
    st.text_input("Description", key=f"mock_server_add_queue_desc_{dialog_key}")
    selected_queue_id = st.selectbox(
        "Queue",
        options=option_ids or [""],
        key=f"mock_server_add_queue_select_{dialog_key}",
        format_func=lambda queue_id: (
            option_by_id.get(queue_id, {}).get("display")
            if queue_id
            else "Nessuna queue disponibile"
        ),
    )
    if st.button(
        "Add",
        key=f"mock_server_add_queue_submit_{dialog_key}",
        icon=":material/add:",
        use_container_width=True,
    ):
        description = str(st.session_state.get(f"mock_server_add_queue_desc_{dialog_key}") or "")
        if not description.strip():
            st.error("Il campo Description e' obbligatorio.")
            return
        if not str(selected_queue_id or "").strip():
            st.error("Seleziona una queue.")
            return
        draft.setdefault("queues", []).append(
            {
                "id": None,
                "order": len(draft.get("queues") or []) + 1,
                "description": description,
                "queue_id": str(selected_queue_id),
                "configuration_json": {
                    "polling_interval_seconds": 1,
                    "max_messages": 10,
                },
                "operations": [],
                "_ui_key": _new_ui_key(),
            }
        )
        _persist_draft(should_rerun=True)


@st.dialog("Edit Queue", width="medium")
def _edit_queue_dialog(queue_entry: dict, queue_idx: int):
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.error("Mock server non disponibile.")
        return
    queue_options, _ = _load_queue_options()
    option_ids = [str(item.get("queue_id") or "") for item in queue_options if item.get("queue_id")]
    option_by_id = {str(item.get("queue_id")): item for item in queue_options if item.get("queue_id")}

    queue_ui_key = str(queue_entry.get("_ui_key") or _new_ui_key())
    st.number_input(
        "Order",
        min_value=1,
        test=1,
        key=f"mock_server_edit_queue_order_{queue_ui_key}",
        value=max(_safe_int(queue_entry.get("order"), queue_idx + 1), 1),
    )
    st.text_input(
        "Description",
        key=f"mock_server_edit_queue_desc_{queue_ui_key}",
        value=str(queue_entry.get("description") or ""),
    )
    current_queue_id = str(queue_entry.get("queue_id") or "").strip()
    if current_queue_id and current_queue_id not in option_ids:
        option_ids = [current_queue_id, *option_ids]
    selected_queue_id = st.selectbox(
        "Queue",
        options=option_ids or [""],
        key=f"mock_server_edit_queue_select_{queue_ui_key}",
        index=(option_ids.index(current_queue_id) if current_queue_id in option_ids else 0),
        format_func=lambda queue_id: (
            option_by_id.get(queue_id, {}).get("display")
            if queue_id
            else "Nessuna queue disponibile"
        ),
    )
    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"mock_server_edit_queue_save_{queue_ui_key}",
            icon=":material/save:",
            use_container_width=True,
        ):
            queue_entry["order"] = int(
                st.session_state.get(f"mock_server_edit_queue_order_{queue_ui_key}") or queue_idx + 1
            )
            queue_entry["description"] = str(
                st.session_state.get(f"mock_server_edit_queue_desc_{queue_ui_key}") or ""
            )
            queue_entry["queue_id"] = str(selected_queue_id or "").strip()
            draft["queues"] = sorted(
                draft.get("queues") or [],
                key=lambda item: _safe_int(item.get("order"), 0),
            )
            _persist_draft(should_rerun=True)
    with action_cols[1]:
        if st.button(
            "Delete",
            key=f"mock_server_edit_queue_delete_{queue_ui_key}",
            icon=":material/delete:",
            use_container_width=True,
        ):
            queues = draft.get("queues") or []
            if 0 <= queue_idx < len(queues):
                queues.pop(queue_idx)
            _persist_draft(should_rerun=True)


def _render_api_editor(api_entry: dict, api_idx: int, nonce: int):
    api_ui_key = str(api_entry.get("_ui_key") or _new_ui_key())
    api_entry["_ui_key"] = api_ui_key

    description = str(api_entry.get("description") or "").strip()
    label = description or f"API {api_idx + 1}"

    wrapper_cols = st.columns([18, 1], gap="small", vertical_alignment="top")
    with wrapper_cols[0]:
        with st.expander(label, expanded=False):
            cfg = api_entry.get("configuration_json") if isinstance(api_entry.get("configuration_json"), dict) else {}
            cfg = _normalized_api_auth_cfg(cfg)
            method_key = f"mock_server_api_method_{api_ui_key}_{nonce}"
            path_key = f"mock_server_api_path_{api_ui_key}_{nonce}"
            params_state_key = f"mock_server_api_params_rows_{api_ui_key}_{nonce}"
            auth_state_key = f"mock_server_api_auth_{api_ui_key}_{nonce}"
            headers_state_key = f"mock_server_api_headers_rows_{api_ui_key}_{nonce}"
            status_key = f"mock_server_api_status_{api_ui_key}_{nonce}"
            response_headers_state_key = (
                f"mock_server_api_response_headers_rows_{api_ui_key}_{nonce}"
            )
            _ensure_body_editor_state(api_entry, api_ui_key, nonce, "expected")
            _ensure_body_editor_state(api_entry, api_ui_key, nonce, "response")

            if method_key not in st.session_state:
                st.session_state[method_key] = str(cfg.get("method") or api_entry.get("method") or "GET")
            if path_key not in st.session_state:
                st.session_state[path_key] = _normalize_path(cfg.get("path") or api_entry.get("path"))
            ensure_kv_editor_state(params_state_key, cfg.get("params") or {})
            initialize_auth_mode_state(auth_state_key, cfg.get("authMode"), cfg.get("authorization") or {})
            ensure_kv_editor_state(headers_state_key, cfg.get("headers") or {})
            ensure_kv_editor_state(
                response_headers_state_key,
                cfg.get("response_headers") or {},
            )
            if status_key not in st.session_state:
                st.session_state[status_key] = max(_safe_int(cfg.get("response_status"), 200), 100)

            conf_cols = st.columns([2, 5], gap="small", vertical_alignment="center")
            with conf_cols[0]:
                selected_method = st.selectbox(
                    "Method",
                    options=HTTP_METHOD_OPTIONS,
                    key=method_key,
                )
            with conf_cols[1]:
                selected_path = st.text_input(
                    "URL path",
                    key=path_key,
                    placeholder="/orders",
                )

            pre_operations = _api_operations_list(api_entry, API_PRE_RESPONSE_OPERATIONS_KEY)
            post_operations = _api_operations_list(api_entry, API_POST_RESPONSE_OPERATIONS_KEY)
            api_entry[API_PRE_RESPONSE_OPERATIONS_KEY] = pre_operations
            api_entry[API_RESPONSE_OPERATIONS_KEY] = _api_operations_list(
                api_entry,
                API_RESPONSE_OPERATIONS_KEY,
            )
            api_entry[API_POST_RESPONSE_OPERATIONS_KEY] = post_operations
            # Keep legacy field aligned with post-response operations.
            api_entry["operations"] = post_operations

            (
                tab_params,
                tab_auth,
                tab_headers,
                tab_body,
                tab_pre_response,
                tab_response,
                tab_post_response,
            ) = st.tabs(
                [
                    "Params",
                    "Auth",
                    "Headers",
                    "Body",
                    "Pre-response",
                    "Response",
                    "Post-response",
                ]
            )
            with tab_params:
                params_rows = render_kv_rows_container(
                    editor_state_key=params_state_key,
                    key_prefix=f"{params_state_key}_row",
                    use_container=False,
                )
            with tab_auth:
                render_auth_mode_editor(auth_state_key)
            with tab_headers:
                headers_rows = render_kv_rows_container(
                    editor_state_key=headers_state_key,
                    key_prefix=f"{headers_state_key}_row",
                    use_container=False,
                )
            with tab_body:
                expected_type_key, expected_value_key = _body_editor_keys(
                    api_ui_key,
                    nonce,
                    "expected",
                )
                current_expected_type = str(
                    st.session_state.get(expected_type_key) or BODY_TYPE_ANY
                ).strip().lower()
                body_header_cols = st.columns([10, 1], gap="small", vertical_alignment="center")
                with body_header_cols[0]:
                    st.markdown("**Expected Body ( JSON or string)**")
                with body_header_cols[1]:
                    if st.button(
                        "",
                        key=f"mock_server_api_expected_body_edit_{api_ui_key}_{nonce}",
                        icon=":material/edit:",
                        help="Edit expected body",
                        type="tertiary",
                        use_container_width=True,
                    ):
                        _body_editor_dialog(api_entry, api_ui_key, nonce, "expected")
                if current_expected_type == BODY_TYPE_ANY:
                    st.caption("Body type: Any")
                else:
                    st.caption(f"Body type: {_body_type_label(current_expected_type)}")
                    st.text_area(
                        "Expected body preview",
                        value=str(st.session_state.get(expected_value_key) or ""),
                        key=f"mock_server_api_expected_body_preview_{api_ui_key}_{nonce}",
                        disabled=True,
                        height=180,
                    )
            with tab_pre_response:
                pre_scope_test = {"operations": pre_operations}
                for op_idx, operation in enumerate(pre_operations):
                    render_operation_component(
                        pre_scope_test,
                        operation,
                        op_idx,
                        f"{api_ui_key}_pre",
                        nonce,
                        show_status_indicator=False,
                        persist_suite_changes_fn=_persist_draft_after_change,
                    )
                pre_add_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
                with pre_add_cols[1]:
                    if st.button(
                        "Add operation",
                        key=f"mock_server_add_api_pre_operation_{api_ui_key}_{nonce}",
                        icon=":material/add:",
                        use_container_width=True,
                    ):
                        _open_add_operation_dialog(api_ui_key, API_PRE_RESPONSE_OPERATIONS_KEY)
                        st.rerun()
            with tab_response:
                st.markdown("**Response configuration**")
                st.number_input(
                    "Response status",
                    min_value=100,
                    max_value=599,
                    key=status_key,
                )
                st.markdown("**headers**")
                response_headers_rows = render_kv_rows_container(
                    editor_state_key=response_headers_state_key,
                    key_prefix=f"{response_headers_state_key}_row",
                )
                response_type_key, response_value_key = _body_editor_keys(
                    api_ui_key,
                    nonce,
                    "response",
                )
                current_response_type = str(
                    st.session_state.get(response_type_key) or BODY_TYPE_ANY
                ).strip().lower()
                response_body_cols = st.columns([10, 1], gap="small", vertical_alignment="center")
                with response_body_cols[0]:
                    st.markdown("**Response Body ( JSON or string)**")
                with response_body_cols[1]:
                    if st.button(
                        "",
                        key=f"mock_server_api_response_body_edit_{api_ui_key}_{nonce}",
                        icon=":material/edit:",
                        help="Edit response body",
                        type="tertiary",
                        use_container_width=True,
                    ):
                        _body_editor_dialog(api_entry, api_ui_key, nonce, "response")
                if current_response_type == BODY_TYPE_ANY:
                    st.caption("Body type: Any")
                else:
                    st.caption(f"Body type: {_body_type_label(current_response_type)}")
                    st.text_area(
                        "Response body preview",
                        value=str(st.session_state.get(response_value_key) or ""),
                        key=f"mock_server_api_response_body_preview_{api_ui_key}_{nonce}",
                        disabled=True,
                        height=180,
                    )
            with tab_post_response:
                post_scope_test = {"operations": post_operations}
                for op_idx, operation in enumerate(post_operations):
                    render_operation_component(
                        post_scope_test,
                        operation,
                        op_idx,
                        f"{api_ui_key}_post",
                        nonce,
                        show_status_indicator=False,
                        persist_suite_changes_fn=_persist_draft_after_change,
                    )
                post_add_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
                with post_add_cols[1]:
                    if st.button(
                        "Add operation",
                        key=f"mock_server_add_api_post_operation_{api_ui_key}_{nonce}",
                        icon=":material/add:",
                        use_container_width=True,
                    ):
                        _open_add_operation_dialog(api_ui_key, API_POST_RESPONSE_OPERATIONS_KEY)
                        st.rerun()

            save_cols = st.columns([4, 2, 2], gap="small", vertical_alignment="center")
            with save_cols[1]:
                if st.button(
                    "Save API",
                    key=f"mock_server_save_api_{api_ui_key}_{nonce}",
                    icon=":material/save:",
                    use_container_width=True,
                ):
                    params_value, params_error = rows_to_dict(params_rows, "Params")
                    if params_error:
                        st.error(params_error)
                        return
                    auth_mode, auth_value, auth_error = collect_auth_mode_value(auth_state_key)
                    if auth_error:
                        st.error(auth_error)
                        return
                    headers_value, headers_error = rows_to_dict(headers_rows, "Headers")
                    if headers_error:
                        st.error(headers_error)
                        return
                    response_headers_value, response_headers_error = rows_to_dict(
                        response_headers_rows,
                        "Response headers",
                    )
                    if response_headers_error:
                        st.error(response_headers_error)
                        return
                    expected_body_value, expected_body_type, expected_body_error = _resolve_body_from_state(
                        api_ui_key,
                        nonce,
                        "expected",
                    )
                    if expected_body_error:
                        st.error(expected_body_error)
                        return
                    response_body_value, response_body_type, response_body_error = _resolve_body_from_state(
                        api_ui_key,
                        nonce,
                        "response",
                    )
                    if response_body_error:
                        st.error(response_body_error)
                        return

                    api_entry["method"] = str(selected_method or "GET").upper()
                    api_entry["path"] = _normalize_path(selected_path)
                    current_cfg = (
                        api_entry.get("configuration_json")
                        if isinstance(api_entry.get("configuration_json"), dict)
                        else {}
                    )
                    api_entry["configuration_json"] = {
                        **current_cfg,
                        "method": api_entry["method"],
                        "path": api_entry["path"],
                        "params": params_value or {},
                        "authMode": auth_mode,
                        "authorization": auth_value or {},
                        "headers": headers_value or {},
                        "body": expected_body_value,
                        "body_type": expected_body_type,
                        "response_status": int(st.session_state.get(status_key) or 200),
                        "response_headers": response_headers_value or {},
                        "response_body": response_body_value,
                        "response_body_type": response_body_type,
                    }
                    _persist_draft(should_rerun=True)
            with save_cols[2]:
                if st.button(
                    "Copy",
                    key=f"mock_server_copy_api_{api_ui_key}_{nonce}",
                    icon=":material/content_copy:",
                    use_container_width=True,
                ):
                    params_value, params_error = rows_to_dict(params_rows, "Params")
                    if params_error:
                        st.error(params_error)
                        return
                    auth_mode, auth_value, auth_error = collect_auth_mode_value(auth_state_key)
                    if auth_error:
                        st.error(auth_error)
                        return
                    headers_value, headers_error = rows_to_dict(headers_rows, "Headers")
                    if headers_error:
                        st.error(headers_error)
                        return
                    response_headers_value, response_headers_error = rows_to_dict(
                        response_headers_rows,
                        "Response headers",
                    )
                    if response_headers_error:
                        st.error(response_headers_error)
                        return
                    expected_body_value, expected_body_type, expected_body_error = _resolve_body_from_state(
                        api_ui_key,
                        nonce,
                        "expected",
                    )
                    if expected_body_error:
                        st.error(expected_body_error)
                        return
                    response_body_value, response_body_type, response_body_error = _resolve_body_from_state(
                        api_ui_key,
                        nonce,
                        "response",
                    )
                    if response_body_error:
                        st.error(response_body_error)
                        return

                    current_cfg = (
                        api_entry.get("configuration_json")
                        if isinstance(api_entry.get("configuration_json"), dict)
                        else {}
                    )
                    copied_cfg = {
                        **current_cfg,
                        "method": str(selected_method or "GET").upper(),
                        "path": _normalize_path(selected_path),
                        "params": params_value or {},
                        "authMode": auth_mode,
                        "authorization": auth_value or {},
                        "headers": headers_value or {},
                        "body": expected_body_value,
                        "body_type": expected_body_type,
                        "response_status": int(st.session_state.get(status_key) or 200),
                        "response_headers": response_headers_value or {},
                        "response_body": response_body_value,
                        "response_body_type": response_body_type,
                    }
                    _copy_api_dialog(api_entry, copied_cfg)
    with wrapper_cols[1]:
        if st.button(
            "",
            key=f"mock_server_edit_api_btn_{api_ui_key}_{nonce}",
            icon=":material/more_vert:",
            help="Edit/Delete API",
            type="tertiary",
            use_container_width=True,
        ):
            _edit_api_dialog(api_entry, api_idx)


def _render_queue_editor(
    queue_entry: dict,
    queue_idx: int,
    queue_by_id: dict[str, dict],
    nonce: int,
):
    queue_ui_key = str(queue_entry.get("_ui_key") or _new_ui_key())
    queue_entry["_ui_key"] = queue_ui_key

    description = str(queue_entry.get("description") or "").strip()
    label = description or f"Queue {queue_idx + 1}"

    queue_id = str(queue_entry.get("queue_id") or "").strip()
    queue_item = queue_by_id.get(queue_id) or {}
    broker_label = str(queue_item.get("broker_label") or "-")
    queue_label = str(queue_item.get("queue_label") or queue_id or "-")

    wrapper_cols = st.columns([18, 1], gap="small", vertical_alignment="top")
    with wrapper_cols[0]:
        with st.expander(label, expanded=False):
            st.markdown(f"**Broker:** {broker_label}")
            st.markdown(f"**Queue:** {queue_label}")
            st.divider()
            st.markdown("**Operations**")
            operations = queue_entry.get("operations") or []
            for op_idx, operation in enumerate(operations):
                render_operation_component(
                    queue_entry,
                    operation,
                    op_idx,
                    queue_ui_key,
                    nonce,
                    persist_suite_changes_fn=_persist_draft_after_change,
                )
            add_op_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
            with add_op_cols[1]:
                if st.button(
                    "Add operation",
                    key=f"mock_server_add_queue_operation_{queue_ui_key}_{nonce}",
                    icon=":material/add:",
                    use_container_width=True,
                ):
                    _open_add_operation_dialog(queue_ui_key)
                    st.rerun()
    with wrapper_cols[1]:
        if st.button(
            "",
            key=f"mock_server_edit_queue_btn_{queue_ui_key}_{nonce}",
            icon=":material/more_vert:",
            help="Edit/Delete queue binding",
            type="tertiary",
            use_container_width=True,
        ):
            _edit_queue_dialog(queue_entry, queue_idx)


def _render_feedback():
    message = st.session_state.pop(MOCK_SERVER_EDITOR_FEEDBACK_KEY, None)
    if message:
        st.success(str(message), icon=":material/check_circle:")


def _render_editor():
    _ensure_editor_draft()
    draft = st.session_state.get(MOCK_SERVER_EDITOR_DRAFT_KEY)
    if not isinstance(draft, dict):
        st.info("Nessun mock server selezionato.")
        if st.button(
            "Back to Mock Servers",
            icon=":material/arrow_back:",
            use_container_width=False,
        ):
            st.switch_page(MOCK_SERVERS_PAGE_PATH)
        _render_feedback()
        return

    _, queue_by_id = _load_queue_options()

    header_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
    with header_cols[1]:
        if st.button(
            "Back",
            key="mock_server_editor_back_btn",
            icon=":material/arrow_back:",
            use_container_width=True,
        ):
            st.switch_page(MOCK_SERVERS_PAGE_PATH)

    description = str(draft.get("description") or draft.get("id") or "-")
    endpoint = _normalize_endpoint(draft.get("endpoint"))
    st.title(description)
    st.subheader(f"/mock/{endpoint or '-'}")

    toggle_value = st.toggle(
        "Active",
        key=f"mock_server_editor_active_toggle_{draft.get('id')}",
        value=bool(draft.get("is_active")),
    )
    if toggle_value != bool(draft.get("is_active")):
        try:
            if toggle_value:
                activate_mock_server(str(draft.get("id") or ""))
            else:
                deactivate_mock_server(str(draft.get("id") or ""))
        except Exception as exc:
            st.error(f"Errore aggiornamento stato mock server: {str(exc)}")
        else:
            load_mock_servers(force=True)
            refreshed = _find_server_by_id(str(draft.get("id") or ""))
            if isinstance(refreshed, dict):
                st.session_state[MOCK_SERVER_EDITOR_DRAFT_KEY] = _build_server_draft(refreshed)
            st.session_state[MOCK_SERVER_EDITOR_FEEDBACK_KEY] = (
                "Mock server attivato." if toggle_value else "Mock server disattivato."
            )
            st.rerun()

    _render_server_auth_section(draft)
    st.divider()
    api_header_cols = st.columns([6, 2, 2], gap="small", vertical_alignment="center")
    with api_header_cols[0]:
        st.subheader("APIs")
    with api_header_cols[1]:
        if st.button(
            "Import",
            key=f"mock_server_editor_import_api_{draft.get('id')}",
            icon=":material/upload_file:",
            use_container_width=True,
            type="secondary",
        ):
            _import_openapi_dialog()
    with api_header_cols[2]:
        if st.button(
            "Add API",
            key=f"mock_server_editor_add_api_{draft.get('id')}",
            icon=":material/add:",
            use_container_width=True,
        ):
            _add_api_dialog()

    apis = draft.get("apis") or []
    if not apis:
        st.caption("Nessuna API configurata.")
    nonce = int(st.session_state.get(MOCK_SERVER_EDITOR_NONCE_KEY, 0))
    for api_idx, api_entry in enumerate(apis):
        if not isinstance(api_entry, dict):
            continue
        _render_api_editor(api_entry, api_idx, nonce)

    st.divider()
    queue_header_cols = st.columns([8, 2], gap="small", vertical_alignment="center")
    with queue_header_cols[0]:
        st.subheader("Queues")
    with queue_header_cols[1]:
        if st.button(
            "Add Queue",
            key=f"mock_server_editor_add_queue_{draft.get('id')}",
            icon=":material/add:",
            use_container_width=True,
        ):
            _add_queue_dialog()

    queues = draft.get("queues") or []
    if not queues:
        st.caption("Nessuna queue configurata.")
    for queue_idx, queue_entry in enumerate(queues):
        if not isinstance(queue_entry, dict):
            continue
        _render_queue_editor(queue_entry, queue_idx, queue_by_id, nonce)

    if st.session_state.get(ADD_TEST_OPERATION_DIALOG_OPEN_KEY, False):
        _add_operation_dialog(draft)
    _render_feedback()


def render_mock_server_editor_page():
    _render_editor()
