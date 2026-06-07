import re
from typing import Any


_MISSING = object()
_INDEX_TOKEN = re.compile(r"^\d+$")


def _is_runtime_ref_expression(value: object) -> bool:
    ref = str(value or "").strip()
    return ref == "$" or ref.startswith("$.")


def _split_path(path: str) -> list[str]:
    parts: list[str] = []
    buffer: list[str] = []
    bracket_level = 0
    for char in path:
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
    return [part for part in parts if part]


def _segment_tokens(segment: str) -> list[str | int]:
    tokens: list[str | int] = []
    remaining = segment
    while remaining:
        if remaining.startswith("["):
            closing_idx = remaining.find("]")
            if closing_idx < 0:
                raise ValueError(f"Invalid $ref segment '{segment}'")
            index_token = remaining[1:closing_idx].strip()
            if not _INDEX_TOKEN.match(index_token):
                raise ValueError(
                    f"Invalid list index '{index_token}' in $ref segment '{segment}'"
                )
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


def _resolve_ref(scope: dict[str, Any], expression: str):
    ref = str(expression or "").strip()
    if ref == "$":
        return scope
    if not ref.startswith("$."):
        raise ValueError(f"Unsupported $ref '{ref}'. Expected '$.<path>'.")

    raw_path = ref[2:]
    if not raw_path:
        return scope

    current: Any = scope
    for segment in _split_path(raw_path):
        for token in _segment_tokens(segment):
            if isinstance(token, int):
                if not isinstance(current, list):
                    return _MISSING
                if token < 0 or token >= len(current):
                    return _MISSING
                current = current[token]
                continue

            if not isinstance(current, dict):
                return _MISSING
            if token not in current:
                return _MISSING
            current = current[token]
    return current


def resolve_dynamic_value(value: Any, scope: dict[str, Any]):
    if isinstance(value, list):
        return [resolve_dynamic_value(item, scope) for item in value]

    if isinstance(value, str):
        raw = value.strip()
        # Allow natural payload shapes where a scalar field can directly point to context.
        if _is_runtime_ref_expression(raw):
            resolved = _resolve_ref(scope, raw)
            if resolved is not _MISSING:
                return resolved
            # Keep unresolved references as-is to avoid destructive coercion to None.
            return value
        return value

    if not isinstance(value, dict):
        return value

    if "$const" in value and "$ref" not in value:
        return resolve_dynamic_value(value.get("$const"), scope)

    if "$ref" in value:
        ref_value = str(value.get("$ref") or "").strip()
        if _is_runtime_ref_expression(ref_value):
            resolved = _resolve_ref(scope, ref_value)
            if resolved is not _MISSING:
                return resolved

            if "$default" in value:
                return resolve_dynamic_value(value.get("$default"), scope)

            if bool(value.get("$required")):
                raise ValueError(f"Required reference not found: {value.get('$ref')}")

            return None

    return {key: resolve_dynamic_value(item, scope) for key, item in value.items()}
