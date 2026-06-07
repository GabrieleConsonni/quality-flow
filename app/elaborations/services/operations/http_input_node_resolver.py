from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    HttpInputNode,
    HttpBodyType,
    HttpInputNodeKind,
    SUPPORTED_RUNTIME_FUNCTIONS,
)
from elaborations.services.constants.command_constant_definition_registry import (
    resolve_definition_path,
)
from elaborations.services.suite_runs.run_context import (
    build_run_context_scope,
    get_run_context,
)
from elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value

_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")
_INDEX_TOKEN_RE = re.compile(r"^\d+$")
_MISSING = object()


def _coerce_compatible_http_input_node(node: object) -> HttpInputNode | None:
    if isinstance(node, HttpInputNode):
        return node
    if node is None or isinstance(node, (dict, list, tuple, str, bytes, int, float, bool)):
        return None
    kind = getattr(node, "kind", None)
    if kind is None:
        return None
    try:
        return HttpInputNode(
            kind=str(kind),
            value=getattr(node, "value", None),
            definitionId=getattr(node, "definitionId", None),
            fieldPath=getattr(node, "fieldPath", None),
            sourceCode=getattr(node, "sourceCode", None),
            resolver=getattr(node, "resolver", None),
        )
    except (TypeError, ValueError):
        return None


def _resolve_built_in(resolver: str) -> Any:
    normalized = str(resolver or "").strip().lower()
    if normalized == "now":
        return datetime.now().isoformat()
    if normalized == "today":
        return date.today().isoformat()
    raise ValueError(f"Unsupported built-in resolver '{resolver}'.")


def _resolve_source_value(session: Session, source_code: str) -> Any:
    from elaborations.services.operations.command_data_resolver import (
        _resolve_source_payload,
    )

    payload, _source_type = _resolve_source_payload(session, source_code)
    return payload


def _split_relative_field_path(path: str) -> list[str]:
    normalized_path = str(path or "").strip()
    if not normalized_path:
        return []
    if normalized_path.startswith(".") or normalized_path.endswith(".") or ".." in normalized_path:
        raise ValueError(f"Invalid fieldPath '{normalized_path}'.")
    parts: list[str] = []
    buffer: list[str] = []
    bracket_level = 0
    for char in normalized_path:
        if char == "." and bracket_level == 0:
            parts.append("".join(buffer))
            buffer = []
            continue
        if char == "[":
            bracket_level += 1
        elif char == "]":
            bracket_level = max(bracket_level - 1, 0)
        buffer.append(char)
    parts.append("".join(buffer))
    if any(part == "" for part in parts):
        raise ValueError(f"Invalid fieldPath '{normalized_path}'.")
    return parts


def _relative_segment_tokens(segment: str) -> list[str | int]:
    tokens: list[str | int] = []
    remaining = str(segment or "").strip()
    while remaining:
        if remaining.startswith("["):
            closing_idx = remaining.find("]")
            if closing_idx < 0:
                raise ValueError(f"Invalid field path segment '{segment}'.")
            index_token = remaining[1:closing_idx].strip()
            if not _INDEX_TOKEN_RE.match(index_token):
                raise ValueError(f"Invalid list index '{index_token}' in field path '{segment}'.")
            tokens.append(int(index_token))
            remaining = remaining[closing_idx + 1 :]
            continue
        opening_idx = remaining.find("[")
        if opening_idx < 0:
            tokens.append(remaining)
            break
        property_token = remaining[:opening_idx]
        if property_token:
            tokens.append(property_token)
        remaining = remaining[opening_idx:]
    return tokens


def _resolve_relative_field_path(value: Any, field_path: str) -> Any:
    normalized_path = str(field_path or "").strip()
    if not normalized_path:
        return value
    if normalized_path.startswith("$"):
        raise ValueError("fieldPath must be relative and must not start with '$'.")

    current: Any = value
    for segment in _split_relative_field_path(normalized_path):
        for token in _relative_segment_tokens(segment):
            if isinstance(token, int):
                if not isinstance(current, list):
                    return None
                if token < 0 or token >= len(current):
                    return None
                current = current[token]
                continue
            if not isinstance(current, dict):
                return None
            if token not in current:
                return None
            current = current[token]
    return current


def resolve_http_input_node(session: Session, node: object) -> Any:
    compatible_node = _coerce_compatible_http_input_node(node)
    if compatible_node is not None:
        if compatible_node.kind == HttpInputNodeKind.LITERAL.value:
            return resolve_dynamic_value(compatible_node.value, build_run_context_scope())
        if compatible_node.kind == HttpInputNodeKind.RUNTIME_VALUE.value:
            _definition, path = resolve_definition_path(session, compatible_node.definitionId)
            resolved = resolve_dynamic_value(path, build_run_context_scope())
            if resolved == path:
                return None
            if compatible_node.fieldPath:
                return _resolve_relative_field_path(resolved, compatible_node.fieldPath)
            return resolved
        if compatible_node.kind == HttpInputNodeKind.SOURCE.value:
            return _resolve_source_value(session, compatible_node.sourceCode)
        if compatible_node.kind == HttpInputNodeKind.BUILT_IN.value:
            return _resolve_built_in(compatible_node.resolver)
        raise ValueError(f"Unsupported HTTP input node kind '{compatible_node.kind}'.")
    if isinstance(node, dict):
        return {key: resolve_http_input_node(session, item) for key, item in node.items()}
    if isinstance(node, list):
        return [resolve_http_input_node(session, item) for item in node]
    return resolve_dynamic_value(node, build_run_context_scope())


def resolve_http_kv_params(session: Session, params: dict | None) -> dict | None:
    if not params:
        return None
    result: dict = {}
    for key, node in params.items():
        resolved = resolve_http_input_node(session, node)
        if resolved is not None:
            result[str(key)] = resolved
    return result or None


def resolve_http_headers(session: Session, headers: dict | None) -> dict[str, str]:
    if not headers:
        return {}
    result: dict[str, str] = {}
    for key, node in headers.items():
        resolved = resolve_http_input_node(session, node)
        if resolved is not None:
            result[str(key)] = str(resolved)
    return result


def resolve_path_params_and_url(
    session: Session,
    url: str,
    path_params: dict | None,
) -> str:
    if not path_params:
        unresolved = _PLACEHOLDER_RE.findall(url)
        if unresolved:
            raise ValueError(
                f"URL contains unresolved path parameter(s): {', '.join(unresolved)}."
            )
        return url

    resolved_params: dict[str, str] = {}
    for key, node in path_params.items():
        value = resolve_http_input_node(session, node)
        if value is None:
            raise ValueError(f"Path parameter '{key}' resolved to None.")
        resolved_params[key] = str(value)

    def _replace_placeholder(match: re.Match) -> str:
        name = match.group(1)
        if name in resolved_params:
            return resolved_params[name]
        raise ValueError(f"URL path parameter '{name}' has no matching pathParams entry.")

    resolved_url = _PLACEHOLDER_RE.sub(_replace_placeholder, url)
    return resolved_url


def resolve_http_body(session: Session, body: object, body_type: str) -> Any:
    if body is None:
        return None
    if str(body_type or "").strip() == HttpBodyType.FORM_URL_ENCODED.value:
        if not isinstance(body, dict):
            raise ValueError("formUrlEncoded body must be an object.")
        result: dict[str, Any] = {}
        for key, node in body.items():
            normalized_key = str(key or "").strip()
            if not normalized_key:
                raise ValueError("formUrlEncoded body keys are required.")
            compatible_node = _coerce_compatible_http_input_node(node)
            if compatible_node is not None and compatible_node.kind == HttpInputNodeKind.SOURCE.value:
                raise ValueError(
                    f"formUrlEncoded field '{normalized_key}' does not support datasource values."
                )
            if compatible_node is not None and compatible_node.kind == HttpInputNodeKind.RUNTIME_VALUE.value:
                definition, _path = resolve_definition_path(session, compatible_node.definitionId)
                definition_value_type = str(definition.value_type or "").strip()
                if definition_value_type in {"dataset", "jsonArray"}:
                    raise ValueError(
                        f"formUrlEncoded field '{normalized_key}' does not support runtime value type '{definition_value_type}'."
                    )
            resolved = resolve_http_input_node(session, node)
            if resolved is None:
                continue
            if isinstance(resolved, (dict, list)):
                raise ValueError(
                    f"formUrlEncoded field '{normalized_key}' resolved to a non-scalar value. Use a fieldPath that targets a scalar leaf."
                )
            result[normalized_key] = resolved
        return result or None
    return resolve_http_input_node(session, body)


def compile_authorization(session: Session, authorization: dict | None) -> dict[str, str]:
    import base64
    import json

    import requests as http_requests

    if not authorization or not isinstance(authorization, dict):
        return {}

    auth_type = str(authorization.get("type") or "").strip()
    if not auth_type:
        return {}

    def _resolve_leaf(node) -> str:
        resolved = resolve_http_input_node(session, node)
        return str(resolved or "").strip()

    if auth_type == "basic":
        username = _resolve_leaf(authorization.get("username"))
        password = _resolve_leaf(authorization.get("password"))
        if not username:
            raise ValueError("authorization.username resolved to empty for basic auth.")
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    if auth_type == "bearer":
        token = _resolve_leaf(authorization.get("token"))
        if not token:
            raise ValueError("authorization.token resolved to empty for bearer auth.")
        return {"Authorization": f"Bearer {token}"}

    if auth_type == "apiKey":
        username = _resolve_leaf(authorization.get("username"))
        api_key = _resolve_leaf(authorization.get("apiKey"))
        auth_endpoint = _resolve_leaf(authorization.get("authEndpoint"))
        if not username:
            raise ValueError("authorization.username resolved to empty for apiKey auth.")
        if not api_key:
            raise ValueError("authorization.apiKey resolved to empty for apiKey auth.")
        if not auth_endpoint:
            raise ValueError("authorization.authEndpoint resolved to empty for apiKey auth.")
        try:
            response = http_requests.post(
                auth_endpoint,
                json={"username": username, "apiKey": api_key},
                timeout=30,
            )
        except http_requests.RequestException as exc:
            raise ValueError(
                f"apiKey auth handshake failed: {exc}"
            ) from exc
        if not response.ok:
            raise ValueError(
                f"apiKey auth handshake returned status {response.status_code}."
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise ValueError(
                "apiKey auth handshake response is not valid JSON."
            ) from exc
        access_token = str(body.get("access_token") or "").strip() if isinstance(body, dict) else ""
        if not access_token:
            raise ValueError(
                "apiKey auth handshake response missing 'access_token'."
            )
        return {"Authorization": f"Bearer {access_token}"}

    if auth_type == "oauth2":
        token_url = _resolve_leaf(authorization.get("tokenUrl"))
        client_id = _resolve_leaf(authorization.get("clientId"))
        client_secret = _resolve_leaf(authorization.get("clientSecret"))
        if not token_url:
            raise ValueError("authorization.tokenUrl resolved to empty for oauth2 auth.")
        if not client_id:
            raise ValueError("authorization.clientId resolved to empty for oauth2 auth.")
        try:
            response = http_requests.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=30,
            )
        except http_requests.RequestException as exc:
            raise ValueError(
                f"oauth2 token request failed: {exc}"
            ) from exc
        if not response.ok:
            raise ValueError(
                f"oauth2 token request returned status {response.status_code}."
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise ValueError(
                "oauth2 token response is not valid JSON."
            ) from exc
        access_token = str(body.get("access_token") or "").strip() if isinstance(body, dict) else ""
        if not access_token:
            raise ValueError(
                "oauth2 token response missing 'access_token'."
            )
        return {"Authorization": f"Bearer {access_token}"}

    raise ValueError(f"Unsupported authorization type '{auth_type}'.")
