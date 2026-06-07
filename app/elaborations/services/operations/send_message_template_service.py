from datetime import UTC, date, datetime

from elaborations.models.dtos.configuration_command_dto import SendMessageTemplateDto
from elaborations.services.suite_runs.run_context import build_run_context_scope
from elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value


def _normalize_template_path(value: object) -> list[str]:
    raw = str(value or "").strip()
    if not raw or raw == "$":
        return []
    if raw.startswith("$."):
        raw = raw[2:]
    elif raw.startswith("$"):
        raw = raw[1:]
    raw = raw.strip(".")
    if not raw:
        return []
    return [segment for segment in raw.split(".") if segment]


def _segment_parts(segment: str) -> tuple[str, bool]:
    normalized = str(segment or "").strip()
    if normalized.endswith("[*]"):
        return normalized[:-3], True
    return normalized, False


def _flatten_template_value(value, prefix: str = "") -> dict[str, object]:
    result: dict[str, object] = {}
    if prefix:
        result[prefix] = value
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key or "").strip()
            if not key:
                continue
            child_prefix = f"{prefix}.{key}" if prefix else key
            result.update(_flatten_template_value(child, child_prefix))
    return result


def _append_match(matches: list[dict[str, object]], current, ancestors: dict[str, object]):
    if isinstance(current, list):
        for item in current:
            _append_match(matches, item, ancestors)
        return

    row = dict(ancestors)
    if isinstance(current, dict):
        row.update(_flatten_template_value(current))
    else:
        row["value"] = current
    matches.append(row)


def _extract_template_matches(root, for_each: object) -> list[dict[str, object]]:
    segments = _normalize_template_path(for_each)
    if not segments:
        matches: list[dict[str, object]] = []
        _append_match(matches, root, {})
        return matches

    matches: list[dict[str, object]] = []

    def walk(current, segment_index: int, ancestors: dict[str, object], path_prefix: str):
        if segment_index >= len(segments):
            _append_match(matches, current, ancestors)
            return

        segment_name, is_array = _segment_parts(segments[segment_index])
        if not isinstance(current, dict) or segment_name not in current:
            return

        next_value = current.get(segment_name)
        next_prefix = f"{path_prefix}.{segment_name}" if path_prefix else segment_name
        capture_ancestor = segment_index < len(segments) - 1

        if is_array:
            if not isinstance(next_value, list):
                return
            for item in next_value:
                next_ancestors = dict(ancestors)
                if capture_ancestor:
                    next_ancestors.update(_flatten_template_value(item, next_prefix))
                walk(item, segment_index + 1, next_ancestors, next_prefix)
            return

        next_ancestors = dict(ancestors)
        if capture_ancestor:
            next_ancestors.update(_flatten_template_value(next_value, next_prefix))
        walk(next_value, segment_index + 1, next_ancestors, next_prefix)

    walk(root, 0, {}, "")
    return matches


def preview_send_message_template_rows(input_data, *, source_type: str, for_each: object = None) -> list[dict[str, object]]:
    normalized_source_type = str(source_type or "").strip()
    if normalized_source_type == "dataset":
        if isinstance(input_data, list):
            return [row for row in (_flatten_template_value(item) for item in input_data) if row]
        if isinstance(input_data, dict):
            return [_flatten_template_value(input_data)]
        return []

    if normalized_source_type == "jsonArray" or isinstance(input_data, list):
        rows: list[dict[str, object]] = []
        for item in input_data if isinstance(input_data, list) else []:
            rows.extend(_extract_template_matches(item, for_each))
        return rows

    return _extract_template_matches(input_data, for_each)


def _evaluate_template_constant(constant) -> object:
    kind = str(constant.kind or "").strip().lower()
    value = constant.value
    if kind == "number":
        if isinstance(value, int | float):
            return value
        numeric_value = str(value or "").strip()
        if "." in numeric_value:
            return float(numeric_value)
        return int(numeric_value)
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        normalized_value = str(value or "").strip().lower()
        return normalized_value in {"true", "1", "yes", "y", "on"}
    if kind == "variable":
        return resolve_dynamic_value(str(value or "").strip(), build_run_context_scope())
    if kind == "function":
        if str(value or "").strip().lower() == "today":
            return date.today().isoformat()
        return datetime.now(UTC).replace(microsecond=0).isoformat()
    return value


def build_send_message_payloads(
    input_data,
    *,
    source_type: str,
    message_template: SendMessageTemplateDto | None,
) -> list[object]:
    if message_template is None:
        return input_data if isinstance(input_data, list) else [input_data]

    rows = preview_send_message_template_rows(
        input_data,
        source_type=source_type,
        for_each=message_template.forEach,
    )
    payloads: list[dict[str, object]] = []
    for row in rows:
        payload: dict[str, object] = {}
        for field in message_template.fields:
            field_key = str(field or "").strip()
            if field_key and field_key in row:
                payload[field_key] = row[field_key]
        for constant in message_template.constants:
            payload[str(constant.name or "").strip()] = _evaluate_template_constant(constant)
        payloads.append(payload)
    return payloads
