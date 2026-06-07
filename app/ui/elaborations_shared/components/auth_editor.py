import streamlit as st


AUTH_TYPE_NONE = "none"
AUTH_TYPE_BASIC = "basic"
AUTH_TYPE_BEARER = "bearer"
AUTH_TYPE_API_KEY = "apiKey"
AUTH_TYPE_OAUTH2 = "oauth2"

AUTH_TYPE_OPTIONS = [
    AUTH_TYPE_NONE,
    AUTH_TYPE_BASIC,
    AUTH_TYPE_BEARER,
    AUTH_TYPE_API_KEY,
    AUTH_TYPE_OAUTH2,
]

AUTH_TYPE_LABELS = {
    AUTH_TYPE_NONE: "No auth",
    AUTH_TYPE_BASIC: "Basic auth",
    AUTH_TYPE_BEARER: "Bearer token",
    AUTH_TYPE_API_KEY: "API key",
    AUTH_TYPE_OAUTH2: "OAuth 2",
}

AUTH_MODE_INHERIT = "inherit"
AUTH_MODE_NONE = "none"
AUTH_MODE_CUSTOM = "custom"

AUTH_MODE_OPTIONS = [
    AUTH_MODE_INHERIT,
    AUTH_MODE_NONE,
    AUTH_MODE_CUSTOM,
]

AUTH_MODE_LABELS = {
    AUTH_MODE_INHERIT: "Inherit server auth",
    AUTH_MODE_NONE: "No auth",
    AUTH_MODE_CUSTOM: "Custom auth",
}


def _auth_key(prefix: str, field: str) -> str:
    return f"{prefix}_{field}"


def normalize_authorization_config(value: object) -> dict:
    if not isinstance(value, dict):
        return {}

    auth_type = str(value.get("type") or "").strip()
    if auth_type == AUTH_TYPE_BASIC:
        return {
            "type": AUTH_TYPE_BASIC,
            "username": str(value.get("username") or "").strip(),
            "password": str(value.get("password") or ""),
        }
    if auth_type == AUTH_TYPE_BEARER:
        return {
            "type": AUTH_TYPE_BEARER,
            "token": str(value.get("token") or "").strip(),
        }
    if auth_type == AUTH_TYPE_API_KEY:
        return {
            "type": AUTH_TYPE_API_KEY,
            "username": str(value.get("username") or "").strip(),
            "apiKey": str(value.get("apiKey") or "").strip(),
            "authEndpoint": str(value.get("authEndpoint") or "").strip(),
        }
    if auth_type == AUTH_TYPE_OAUTH2:
        return {
            "type": AUTH_TYPE_OAUTH2,
            "tokenUrl": str(value.get("tokenUrl") or "").strip(),
            "clientId": str(value.get("clientId") or "").strip(),
            "clientSecret": str(value.get("clientSecret") or ""),
        }
    return {}


def normalize_auth_mode(value: object) -> str:
    auth_mode = str(value or "").strip()
    if auth_mode in AUTH_MODE_OPTIONS:
        return auth_mode
    return AUTH_MODE_INHERIT


def initialize_auth_editor_state(prefix: str, authorization: object) -> None:
    normalized = normalize_authorization_config(authorization)
    auth_type = str(normalized.get("type") or AUTH_TYPE_NONE)

    type_key = _auth_key(prefix, "type")
    if type_key not in st.session_state:
        st.session_state[type_key] = auth_type

    field_defaults = {
        "username": str(normalized.get("username") or ""),
        "password": str(normalized.get("password") or ""),
        "token": str(normalized.get("token") or ""),
        "tokenUrl": str(normalized.get("tokenUrl") or ""),
        "clientId": str(normalized.get("clientId") or ""),
        "clientSecret": str(normalized.get("clientSecret") or ""),
        "apiKey": str(normalized.get("apiKey") or ""),
        "authEndpoint": str(normalized.get("authEndpoint") or ""),
    }
    for field_name, default_value in field_defaults.items():
        state_key = _auth_key(prefix, field_name)
        if state_key not in st.session_state:
            st.session_state[state_key] = default_value


def initialize_auth_mode_state(prefix: str, auth_mode: object, authorization: object) -> None:
    normalized_auth = normalize_authorization_config(authorization)
    normalized_mode = normalize_auth_mode(auth_mode)
    if normalized_mode == AUTH_MODE_INHERIT and normalized_auth:
        normalized_mode = AUTH_MODE_CUSTOM

    mode_key = _auth_key(prefix, "mode")
    if mode_key not in st.session_state:
        st.session_state[mode_key] = normalized_mode
    initialize_auth_editor_state(prefix, normalized_auth)


def render_auth_editor(prefix: str) -> None:
    auth_type = st.selectbox(
        "Auth type",
        options=AUTH_TYPE_OPTIONS,
        key=_auth_key(prefix, "type"),
        format_func=lambda auth_value: AUTH_TYPE_LABELS.get(str(auth_value), str(auth_value)),
    )

    if auth_type == AUTH_TYPE_BASIC:
        st.text_input("Username", key=_auth_key(prefix, "username"))
        st.text_input("Password", key=_auth_key(prefix, "password"), type="password")
    elif auth_type == AUTH_TYPE_BEARER:
        st.text_input("Token", key=_auth_key(prefix, "token"), type="password")
    elif auth_type == AUTH_TYPE_API_KEY:
        st.text_input("Username", key=_auth_key(prefix, "username"))
        st.text_input("API key", key=_auth_key(prefix, "apiKey"), type="password")
        st.text_input("Auth endpoint", key=_auth_key(prefix, "authEndpoint"))
    elif auth_type == AUTH_TYPE_OAUTH2:
        st.text_input("Token URL", key=_auth_key(prefix, "tokenUrl"))
        st.text_input("Client ID", key=_auth_key(prefix, "clientId"))
        st.text_input("Client secret", key=_auth_key(prefix, "clientSecret"), type="password")
    else:
        st.caption("No authentication configured.")


def render_auth_mode_editor(prefix: str) -> str:
    auth_mode = st.selectbox(
        "Auth mode",
        options=AUTH_MODE_OPTIONS,
        key=_auth_key(prefix, "mode"),
        format_func=lambda mode_value: AUTH_MODE_LABELS.get(str(mode_value), str(mode_value)),
    )
    if auth_mode == AUTH_MODE_CUSTOM:
        render_auth_editor(prefix)
    elif auth_mode == AUTH_MODE_NONE:
        st.caption("Authentication disabled for this API.")
    else:
        st.caption("This API inherits the mock server default auth.")
    return auth_mode


def collect_auth_editor_value(prefix: str) -> tuple[dict, str | None]:
    auth_type = str(st.session_state.get(_auth_key(prefix, "type")) or AUTH_TYPE_NONE).strip()
    if auth_type not in AUTH_TYPE_OPTIONS or auth_type == AUTH_TYPE_NONE:
        return {}, None

    if auth_type == AUTH_TYPE_BASIC:
        username = str(st.session_state.get(_auth_key(prefix, "username")) or "").strip()
        password = str(st.session_state.get(_auth_key(prefix, "password")) or "")
        if not username:
            return {}, "Auth username is required."
        if not password:
            return {}, "Auth password is required."
        return {
            "type": AUTH_TYPE_BASIC,
            "username": username,
            "password": password,
        }, None

    if auth_type == AUTH_TYPE_BEARER:
        token = str(st.session_state.get(_auth_key(prefix, "token")) or "").strip()
        if not token:
            return {}, "Auth token is required."
        return {
            "type": AUTH_TYPE_BEARER,
            "token": token,
        }, None

    if auth_type == AUTH_TYPE_API_KEY:
        username = str(st.session_state.get(_auth_key(prefix, "username")) or "").strip()
        api_key = str(st.session_state.get(_auth_key(prefix, "apiKey")) or "").strip()
        auth_endpoint = str(st.session_state.get(_auth_key(prefix, "authEndpoint")) or "").strip()
        if not username:
            return {}, "Auth username is required."
        if not api_key:
            return {}, "API key is required."
        if not auth_endpoint:
            return {}, "Auth endpoint is required."
        return {
            "type": AUTH_TYPE_API_KEY,
            "username": username,
            "apiKey": api_key,
            "authEndpoint": auth_endpoint,
        }, None

    token_url = str(st.session_state.get(_auth_key(prefix, "tokenUrl")) or "").strip()
    client_id = str(st.session_state.get(_auth_key(prefix, "clientId")) or "").strip()
    client_secret = str(st.session_state.get(_auth_key(prefix, "clientSecret")) or "")
    if not token_url:
        return {}, "OAuth 2 token URL is required."
    if not client_id:
        return {}, "OAuth 2 client ID is required."
    if not client_secret:
        return {}, "OAuth 2 client secret is required."
    return {
        "type": AUTH_TYPE_OAUTH2,
        "tokenUrl": token_url,
        "clientId": client_id,
        "clientSecret": client_secret,
    }, None


def collect_auth_mode_value(prefix: str) -> tuple[str, dict, str | None]:
    auth_mode = normalize_auth_mode(st.session_state.get(_auth_key(prefix, "mode")))
    if auth_mode == AUTH_MODE_INHERIT:
        return AUTH_MODE_INHERIT, {}, None
    if auth_mode == AUTH_MODE_NONE:
        return AUTH_MODE_NONE, {}, None
    authorization, error = collect_auth_editor_value(prefix)
    if error:
        return AUTH_MODE_CUSTOM, {}, error
    return AUTH_MODE_CUSTOM, authorization, None


# ---------------------------------------------------------------------------
# Guided auth editor — leaf fields use guided value controls
# ---------------------------------------------------------------------------

_GUIDED_AUTH_FIELDS = {
    AUTH_TYPE_BASIC: ["username", "password"],
    AUTH_TYPE_BEARER: ["token"],
    AUTH_TYPE_API_KEY: ["username", "apiKey", "authEndpoint"],
    AUTH_TYPE_OAUTH2: ["tokenUrl", "clientId", "clientSecret"],
}

_GUIDED_AUTH_FIELD_LABELS = {
    "username": "Username",
    "password": "Password",
    "token": "Token",
    "apiKey": "API key",
    "authEndpoint": "Auth endpoint",
    "tokenUrl": "Token URL",
    "clientId": "Client ID",
    "clientSecret": "Client secret",
}


def _extract_guided_auth_leaf(authorization: dict, field_name: str) -> object:
    value = authorization.get(field_name)
    if isinstance(value, dict) and "kind" in value:
        return value
    if value is not None:
        return {"kind": "literal", "value": value}
    return {"kind": "literal", "value": ""}


def initialize_guided_auth_state(prefix: str, authorization: object) -> None:
    from elaborations_shared.components.guided_value_control import (
        initialize_guided_value_state,
    )

    normalized = authorization if isinstance(authorization, dict) else {}
    auth_type = str(normalized.get("type") or AUTH_TYPE_NONE)

    type_key = _auth_key(prefix, "type")
    if type_key not in st.session_state:
        st.session_state[type_key] = auth_type

    fields = _GUIDED_AUTH_FIELDS.get(auth_type, [])
    for field_name in fields:
        node = _extract_guided_auth_leaf(normalized, field_name)
        field_prefix = _auth_key(prefix, f"g_{field_name}")
        initialize_guided_value_state(field_prefix, node)


def render_guided_auth_editor(
    prefix: str,
    *,
    available_constants: list[dict] | None = None,
    available_sources: list[dict] | None = None,
) -> None:
    from elaborations_shared.components.guided_value_control import (
        initialize_guided_value_state,
        render_guided_value_control,
    )

    auth_type = st.selectbox(
        "Auth type",
        options=AUTH_TYPE_OPTIONS,
        key=_auth_key(prefix, "type"),
        format_func=lambda v: AUTH_TYPE_LABELS.get(str(v), str(v)),
    )

    fields = _GUIDED_AUTH_FIELDS.get(auth_type, [])
    if not fields:
        st.caption("No authentication configured.")
        return

    for field_name in fields:
        field_prefix = _auth_key(prefix, f"g_{field_name}")
        initialize_guided_value_state(field_prefix, {"kind": "literal", "value": ""})
        render_guided_value_control(
            field_prefix,
            label=_GUIDED_AUTH_FIELD_LABELS.get(field_name, field_name),
            available_constants=available_constants,
            available_sources=available_sources,
        )


def collect_guided_auth_value(prefix: str) -> tuple[dict, str | None]:
    from elaborations_shared.components.guided_value_control import (
        collect_guided_value,
    )

    auth_type = str(st.session_state.get(_auth_key(prefix, "type")) or AUTH_TYPE_NONE).strip()
    if auth_type not in AUTH_TYPE_OPTIONS or auth_type == AUTH_TYPE_NONE:
        return {}, None

    fields = _GUIDED_AUTH_FIELDS.get(auth_type, [])
    result = {"type": auth_type}
    for field_name in fields:
        field_prefix = _auth_key(prefix, f"g_{field_name}")
        node, error = collect_guided_value(field_prefix)
        if error:
            label = _GUIDED_AUTH_FIELD_LABELS.get(field_name, field_name)
            return {}, f"Auth {label}: {error}"
        result[field_name] = node

    return result, None
