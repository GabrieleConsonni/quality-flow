import json

import pandas as pd

PERIMETER_OPERATORS = [
    "eq",
    "neq",
    "gt",
    "gte",
    "lt",
    "lte",
    "contains",
    "starts_with",
    "ends_with",
    "in",
    "not_in",
    "is_null",
    "is_not_null",
]
PERIMETER_PARAMETER_TYPES = [
    "string",
    "integer",
    "number",
    "boolean",
    "date",
    "datetime",
]
PERIMETER_PARAMETER_DEFAULT_MODE_OPTIONS = ["None", "Literal", "Function"]
PERIMETER_PARAMETER_DEFAULT_FUNCTION_OPTIONS = ["", "Now", "Today"]
PERIMETER_PARAMETER_DEFAULT_FUNCTION_TO_RESOLVER = {
    "Now": "$now",
    "Today": "$today",
}
PERIMETER_PARAMETER_RESOLVER_TO_DEFAULT_FUNCTION = {
    resolver: label
    for label, resolver in PERIMETER_PARAMETER_DEFAULT_FUNCTION_TO_RESOLVER.items()
}


def build_connection_label(connection_item: dict) -> str:
    description = str(connection_item.get("description") or connection_item.get("id") or "-")
    payload = connection_item.get("payload") or {}
    connection_type = str(payload.get("database_type") or "-")
    return f"{description} [{connection_type}]"


def build_dataset_payload(
    connection_id: str,
    schema: str | None,
    object_name: str,
    object_type: str,
) -> dict:
    return {
        "connection_id": connection_id,
        "schema": schema,
        "object_name": object_name,
        "object_type": object_type,
    }


def build_dataset_summary(datasource_item: dict, connection_labels: dict[str, str]) -> dict:
    datasource_id = str(datasource_item.get("id") or "").strip()
    description = str(datasource_item.get("description") or "").strip() or datasource_id or "-"
    payload = datasource_item.get("payload") if isinstance(datasource_item.get("payload"), dict) else {}
    connection_id = str(payload.get("connection_id") or "").strip()
    object_type = str(payload.get("object_type") or "table").strip().lower() or "table"
    object_name = str(payload.get("object_name") or "").strip() or "-"
    schema = str(payload.get("schema") or "").strip() or "-"
    return {
        "id": datasource_id,
        "description": description,
        "connection_id": connection_id,
        "connection_label": connection_labels.get(connection_id, connection_id or "-"),
        "schema": schema,
        "object_type": object_type,
        "object_name": object_name,
        "object_label": f"{object_type.upper()} {object_name}",
    }


def build_perimeter_scope_key(
    key_prefix: str,
    datasource_id: str,
    connection_id: str,
    schema: str | None,
    object_type: str,
    object_name: str,
) -> str:
    return "_".join(
        [
            str(key_prefix or "dataset_perimeter").strip(),
            str(datasource_id or "nodatasource").strip(),
            str(connection_id or "noconnection").strip(),
            str(schema or "noschema").strip(),
            str(object_type or "table").strip(),
            str(object_name or "noobject").strip(),
        ]
    )


def coerce_editor_rows(value: object) -> list[dict]:
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def normalize_editor_value(value: object):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return value


def normalize_filter_rows(rows: object) -> list[dict]:
    normalized_rows: list[dict] = []
    for row in coerce_editor_rows(rows):
        normalized = normalize_filter_condition(row)
        if normalized:
            normalized_rows.append(normalized)
    return normalized_rows


def normalize_filter_condition(condition: object) -> dict | None:
    if not isinstance(condition, dict):
        return None
    field = str(condition.get("field") or "").strip()
    operator = str(condition.get("operator") or "").strip().lower()
    raw_value = condition.get("value")
    value = normalize_editor_value(raw_value)
    if not field and not operator and value is None:
        return None
    if not field or not operator:
        return None
    if operator not in {"is_null", "is_not_null"}:
        if isinstance(raw_value, dict) and str(raw_value.get("kind") or "").strip().lower() == "parameter":
            parameter_name = str(raw_value.get("name") or "").strip()
            if not parameter_name:
                return None
            value = {
                "kind": "parameter",
                "name": parameter_name,
            }
        elif value is None:
            return None
    item = {"field": field, "operator": operator}
    if operator not in {"is_null", "is_not_null"}:
        item["value"] = value
    return item


def normalize_filter_group(group: object) -> dict | None:
    if not isinstance(group, dict):
        return None
    logic = str(group.get("logic") or "AND").strip().upper()
    if logic not in {"AND", "OR"}:
        logic = "AND"
    conditions = normalize_filter_rows(group.get("conditions") or [])
    if not conditions:
        return None
    return {
        "kind": "group",
        "logic": logic,
        "conditions": conditions,
    }


def normalize_filter_items(items: object) -> list[dict]:
    normalized_items: list[dict] = []
    if not isinstance(items, list):
        return normalized_items
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "condition").strip().lower()
        if kind == "group":
            normalized_group = normalize_filter_group(item)
            if normalized_group:
                normalized_items.append(normalized_group)
            continue
        normalized_condition = normalize_filter_condition(item)
        if normalized_condition:
            normalized_items.append(
                {
                    "kind": "condition",
                    **normalized_condition,
                }
            )
    return normalized_items


def normalize_sort_rows(rows: object) -> list[dict]:
    normalized_rows: list[dict] = []
    for row in coerce_editor_rows(rows):
        field = str(row.get("field") or "").strip()
        direction = str(row.get("direction") or "").strip().lower()
        if not field and not direction:
            continue
        if not field:
            continue
        normalized_rows.append(
            {
                "field": field,
                "direction": direction or "asc",
            }
        )
    return normalized_rows


def _normalize_parameter_default_mode(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"none", "literal", "function"}:
        return normalized
    return ""


def _normalize_parameter_default_function(value: object) -> str:
    normalized = str(value or "").strip().title()
    if normalized in PERIMETER_PARAMETER_DEFAULT_FUNCTION_TO_RESOLVER:
        return normalized
    return ""


def normalize_parameter_editor_row(parameter: object) -> dict | None:
    if not isinstance(parameter, dict):
        return None
    name = str(parameter.get("name") or "").strip()
    parameter_type = str(parameter.get("type") or "").strip().lower()
    default_value = normalize_editor_value(parameter.get("default_value"))
    default_binding = parameter.get("default_binding") if isinstance(parameter.get("default_binding"), dict) else None
    default_mode = _normalize_parameter_default_mode(parameter.get("default_mode"))
    default_function = _normalize_parameter_default_function(parameter.get("default_function"))
    if default_binding:
        default_mode = "function"
        default_function = (
            PERIMETER_PARAMETER_RESOLVER_TO_DEFAULT_FUNCTION.get(
                str(default_binding.get("resolver") or "").strip()
            )
            or "Now"
        )
        default_value = None
    elif default_value is not None:
        default_mode = "literal"
    elif not default_mode:
        default_mode = "none"
    if default_mode == "function" and not default_function:
        default_function = "Now"
    if default_mode != "literal":
        default_value = None
    if (
        not name
        and not parameter_type
        and default_value is None
        and not default_binding
        and not str(parameter.get("description") or "").strip()
    ):
        return None
    if not name or parameter_type not in PERIMETER_PARAMETER_TYPES:
        return None
    return {
        "name": name,
        "type": parameter_type,
        "default_mode": {
            "none": "None",
            "literal": "Literal",
            "function": "Function",
        }[default_mode],
        "default_value": default_value,
        "default_function": default_function,
        "description": str(parameter.get("description") or "").strip() or None,
    }


def normalize_parameter_definition(parameter: object) -> dict | None:
    editor_row = normalize_parameter_editor_row(parameter)
    if not editor_row:
        return None
    name = str(editor_row.get("name") or "").strip()
    parameter_type = str(editor_row.get("type") or "").strip().lower()
    if not name or parameter_type not in PERIMETER_PARAMETER_TYPES:
        return None
    normalized = {
        "name": name,
        "type": parameter_type,
        "description": str(editor_row.get("description") or "").strip() or None,
    }
    default_mode = _normalize_parameter_default_mode(editor_row.get("default_mode"))
    if default_mode == "literal":
        default_value = normalize_editor_value(editor_row.get("default_value"))
        if default_value is not None:
            normalized["default_value"] = default_value
    elif default_mode == "function":
        default_function = _normalize_parameter_default_function(editor_row.get("default_function")) or "Now"
        normalized["default_binding"] = {
            "kind": "built_in",
            "resolver": PERIMETER_PARAMETER_DEFAULT_FUNCTION_TO_RESOLVER[default_function],
        }
    return normalized


def normalize_parameter_editor_rows(rows: object) -> list[dict]:
    normalized_rows: list[dict] = []
    seen_names: set[str] = set()
    for row in coerce_editor_rows(rows):
        normalized = normalize_parameter_editor_row(row)
        if not normalized:
            continue
        parameter_name = str(normalized.get("name") or "").strip()
        if parameter_name in seen_names:
            continue
        seen_names.add(parameter_name)
        normalized_rows.append(normalized)
    return normalized_rows


def normalize_parameter_rows(rows: object) -> list[dict]:
    normalized_rows: list[dict] = []
    seen_names: set[str] = set()
    for row in coerce_editor_rows(rows):
        normalized = normalize_parameter_definition(row)
        if not normalized:
            continue
        parameter_name = str(normalized.get("name") or "").strip()
        if parameter_name in seen_names:
            continue
        seen_names.add(parameter_name)
        normalized_rows.append(normalized)
    return normalized_rows


def build_perimeter_payload(
    selected_columns: list[str],
    parameter_rows_or_filter_logic: object,
    filter_logic_or_items: object,
    filter_items_or_sort_rows: object,
    sort_rows: object | None = None,
) -> dict | None:
    perimeter: dict = {}
    if sort_rows is None:
        parameter_rows = []
        filter_logic = parameter_rows_or_filter_logic
        filter_items = filter_logic_or_items
        sort_rows = filter_items_or_sort_rows
    else:
        parameter_rows = parameter_rows_or_filter_logic
        filter_logic = filter_logic_or_items
        filter_items = filter_items_or_sort_rows
    normalized_columns = [str(column).strip() for column in selected_columns if str(column).strip()]
    normalized_parameters = normalize_parameter_rows(parameter_rows)
    normalized_filter_items = normalize_filter_items(filter_items)
    normalized_sort = normalize_sort_rows(sort_rows)

    if normalized_columns:
        perimeter["selected_columns"] = normalized_columns
    if normalized_parameters:
        perimeter["parameters"] = normalized_parameters
    if normalized_filter_items:
        perimeter["filter"] = {
            "logic": str(filter_logic or "AND").strip().upper(),
            "items": normalized_filter_items,
        }
    if normalized_sort:
        perimeter["sort"] = normalized_sort

    return perimeter or None


def default_selected_columns(perimeter: dict | None, available_columns: list[str]) -> list[str]:
    payload = perimeter if isinstance(perimeter, dict) else {}
    return [
        str(column)
        for column in (payload.get("selected_columns") or [])
        if str(column) in available_columns
    ]


def default_filter_logic(perimeter: dict | None) -> str:
    payload = perimeter if isinstance(perimeter, dict) else {}
    return str((payload.get("filter") or {}).get("logic") or "AND").strip().upper()


def default_filter_items(perimeter: dict | None) -> list[dict]:
    payload = perimeter if isinstance(perimeter, dict) else {}
    filter_payload = payload.get("filter") if isinstance(payload.get("filter"), dict) else {}
    if filter_payload.get("items") is not None:
        return normalize_filter_items(filter_payload.get("items") or [])

    legacy_conditions = normalize_filter_rows(filter_payload.get("conditions") or [])
    if not legacy_conditions:
        return []
    return [
        {
            "kind": "group",
            "logic": str(filter_payload.get("logic") or "AND").strip().upper(),
            "conditions": legacy_conditions,
        }
    ]


def default_parameter_rows(perimeter: dict | None) -> list[dict]:
    payload = perimeter if isinstance(perimeter, dict) else {}
    return normalize_parameter_editor_rows(payload.get("parameters") or [])


def default_sort_rows(perimeter: dict | None) -> list[dict]:
    payload = perimeter if isinstance(perimeter, dict) else {}
    return payload.get("sort") or []


def _format_perimeter_value(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict) and str(value.get("kind") or "").strip().lower() == "parameter":
        parameter_name = str(value.get("name") or "").strip()
        return f"${parameter_name}" if parameter_name else "$?"
    if isinstance(value, str):
        return f"'{value}'"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(_format_perimeter_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def _format_filter_condition_text(condition: dict) -> str:
    field = str(condition.get("field") or "").strip()
    operator = str(condition.get("operator") or "").strip().lower()
    if not field or not operator:
        return ""
    if operator in {"is_null", "is_not_null"}:
        return f"{field} {operator}"
    return f"{field} {operator} {_format_perimeter_value(condition.get('value'))}"


def build_filter_text(perimeter: dict | None) -> str:
    items = default_filter_items(perimeter)
    if not items:
        return ""
    root_logic = default_filter_logic(perimeter).strip().lower() or "and"
    formatted_items: list[str] = []
    for item in items:
        kind = str(item.get("kind") or "condition").strip().lower()
        if kind == "group":
            group_logic = str(item.get("logic") or "AND").strip().lower() or "and"
            group_conditions = [
                _format_filter_condition_text(condition)
                for condition in (item.get("conditions") or [])
                if _format_filter_condition_text(condition)
            ]
            if group_conditions:
                formatted_items.append(f"({f' {group_logic} '.join(group_conditions)})")
            continue
        condition_text = _format_filter_condition_text(item)
        if condition_text:
            formatted_items.append(condition_text)
    return f" {root_logic} ".join(formatted_items)


def build_sort_text(perimeter: dict | None) -> str:
    sort_rows = normalize_sort_rows(default_sort_rows(perimeter))
    if not sort_rows:
        return ""
    return ", ".join(
        f"{str(item.get('field') or '').strip()} {str(item.get('direction') or 'asc').strip().lower() or 'asc'}"
        for item in sort_rows
        if str(item.get("field") or "").strip()
    )
