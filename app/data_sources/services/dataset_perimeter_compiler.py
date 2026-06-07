from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.sql import Select
from sqlalchemy.sql.schema import Table

from data_sources.services.dataset_parameter_resolver import (
    DATASET_PARAMETER_TYPE_NAMES,
    DatasetParameterResolver,
    SUPPORTED_DATASET_BUILT_IN_RESOLVERS,
)


SUPPORTED_OPERATORS = {
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
}
STRING_OPERATORS = {"contains", "starts_with", "ends_with"}


@dataclass
class DatasetQueryCompilation:
    stmt: Select
    columns: list[str]
    normalized_perimeter: dict | None


class DatasetPerimeterCompiler:
    @staticmethod
    def _serialize_parameter_default_value(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return value

    @classmethod
    def normalize(cls, perimeter_json: dict | None) -> dict | None:
        if perimeter_json in (None, {}):
            return None
        if not isinstance(perimeter_json, dict):
            raise ValueError("perimeter must be an object.")

        normalized: dict[str, Any] = {}

        raw_parameters = perimeter_json.get("parameters")
        parameter_definitions_by_name: dict[str, dict[str, Any]] = {}
        if raw_parameters is not None:
            if not isinstance(raw_parameters, list):
                raise ValueError("parameters must be an array.")
            normalized_parameters: list[dict[str, Any]] = []
            for index, raw_parameter in enumerate(raw_parameters):
                normalized_parameter = cls._normalize_parameter_definition(
                    raw_parameter,
                    f"parameters[{index}]",
                )
                parameter_name = normalized_parameter["name"]
                if parameter_name in parameter_definitions_by_name:
                    raise ValueError(f"Duplicate dataset parameter '{parameter_name}'.")
                parameter_definitions_by_name[parameter_name] = normalized_parameter
                normalized_parameters.append(normalized_parameter)
            if normalized_parameters:
                normalized["parameters"] = normalized_parameters

        raw_selected_columns = perimeter_json.get("selected_columns")
        if raw_selected_columns is not None:
            if not isinstance(raw_selected_columns, list):
                raise ValueError("selected_columns must be an array.")
            selected_columns: list[str] = []
            for item in raw_selected_columns:
                column_name = str(item or "").strip()
                if not column_name:
                    raise ValueError("selected_columns items must be non-empty strings.")
                if column_name in selected_columns:
                    raise ValueError(f"Duplicate selected column '{column_name}'.")
                selected_columns.append(column_name)
            normalized["selected_columns"] = selected_columns

        raw_filter = perimeter_json.get("filter")
        if raw_filter is not None:
            if not isinstance(raw_filter, dict):
                raise ValueError("filter must be an object.")
            logic = str(raw_filter.get("logic") or "AND").strip().upper()
            if logic not in {"AND", "OR"}:
                raise ValueError("filter.logic must be AND or OR.")
            items: list[dict[str, Any]] = []
            if raw_filter.get("items") is not None:
                raw_items = raw_filter.get("items") or []
                if not isinstance(raw_items, list):
                    raise ValueError("filter.items must be an array.")
                items = [
                    cls._normalize_filter_item(
                        raw_item,
                        f"filter.items[{index}]",
                        parameter_definitions_by_name,
                    )
                    for index, raw_item in enumerate(raw_items)
                ]
            else:
                raw_conditions = raw_filter.get("conditions") or []
                if not isinstance(raw_conditions, list):
                    raise ValueError("filter.conditions must be an array.")
                conditions = [
                    cls._normalize_filter_condition(
                        raw_condition,
                        f"filter.conditions[{index}]",
                        parameter_definitions_by_name,
                    )
                    for index, raw_condition in enumerate(raw_conditions)
                ]
                if conditions:
                    items = [
                        {
                            "kind": "group",
                            "logic": logic,
                            "conditions": conditions,
                        }
                    ]
            if items:
                normalized["filter"] = {
                    "logic": logic,
                    "items": items,
                }

        raw_sort = perimeter_json.get("sort")
        if raw_sort is not None:
            if not isinstance(raw_sort, list):
                raise ValueError("sort must be an array.")
            sort_items: list[dict[str, str]] = []
            for index, raw_sort_item in enumerate(raw_sort):
                if not isinstance(raw_sort_item, dict):
                    raise ValueError(f"sort[{index}] must be an object.")
                field = str(raw_sort_item.get("field") or "").strip()
                if not field:
                    raise ValueError(f"sort[{index}].field is required.")
                direction = str(raw_sort_item.get("direction") or "asc").strip().lower()
                if direction not in {"asc", "desc"}:
                    raise ValueError(f"sort[{index}].direction must be 'asc' or 'desc'.")
                sort_items.append(
                    {
                        "field": field,
                        "direction": direction,
                    }
                )
            normalized["sort"] = sort_items

        return normalized or None

    @classmethod
    def compile(
        cls,
        table: Table,
        perimeter_json: dict | None,
        *,
        limit: int | None = None,
        resolved_parameters: dict[str, Any] | None = None,
    ) -> DatasetQueryCompilation:
        normalized = cls.normalize(perimeter_json)
        parameter_values = resolved_parameters if isinstance(resolved_parameters, dict) else {}
        available_columns = {str(column.name): column for column in table.columns}
        selected_columns = list(available_columns.keys())

        if normalized and normalized.get("selected_columns"):
            selected_columns = normalized["selected_columns"]
            for column_name in selected_columns:
                if column_name not in available_columns:
                    raise ValueError(f"Selected column '{column_name}' does not exist.")

        stmt = select(*[available_columns[column_name] for column_name in selected_columns])

        if normalized and normalized.get("filter", {}).get("items"):
            conditions = [
                cls._compile_filter_item(available_columns, item, parameter_values)
                for item in normalized["filter"]["items"]
            ]
            if normalized["filter"]["logic"] == "OR":
                stmt = stmt.where(or_(*conditions))
            else:
                stmt = stmt.where(and_(*conditions))

        if normalized and normalized.get("sort"):
            order_by = []
            for sort_item in normalized["sort"]:
                field = sort_item["field"]
                if field not in available_columns:
                    raise ValueError(f"Sort field '{field}' does not exist.")
                column = available_columns[field]
                order_by.append(column.desc() if sort_item["direction"] == "desc" else column.asc())
            stmt = stmt.order_by(*order_by)

        if limit is not None:
            stmt = stmt.limit(limit)

        return DatasetQueryCompilation(
            stmt=stmt,
            columns=selected_columns,
            normalized_perimeter=normalized,
        )

    @classmethod
    def _compile_condition(
        cls,
        available_columns: dict[str, Any],
        condition: dict[str, Any],
        resolved_parameters: dict[str, Any],
    ):
        field = condition["field"]
        if field not in available_columns:
            raise ValueError(f"Filter field '{field}' does not exist.")
        column = available_columns[field]
        operator = condition["operator"]
        value = condition.get("value")
        if isinstance(value, dict) and str(value.get("kind") or "").strip().lower() == "parameter":
            parameter_name = str(value.get("name") or "").strip()
            if parameter_name not in resolved_parameters:
                raise ValueError(f"Resolved dataset parameter '{parameter_name}' is missing.")
            value = resolved_parameters.get(parameter_name)

        if operator == "eq":
            return column.is_(None) if value is None else column == value
        if operator == "neq":
            return column.is_not(None) if value is None else column != value
        if operator == "gt":
            return column > value
        if operator == "gte":
            return column >= value
        if operator == "lt":
            return column < value
        if operator == "lte":
            return column <= value
        if operator == "contains":
            return column.contains(value)
        if operator == "starts_with":
            return column.startswith(value)
        if operator == "ends_with":
            return column.endswith(value)
        if operator == "in":
            return column.in_(value)
        if operator == "not_in":
            return column.not_in(value)
        if operator == "is_null":
            return column.is_(None)
        if operator == "is_not_null":
            return column.is_not(None)
        raise ValueError(f"Unsupported operator '{operator}'.")

    @classmethod
    def _normalize_filter_condition(
        cls,
        raw_condition: Any,
        path: str,
        parameter_definitions_by_name: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        if not isinstance(raw_condition, dict):
            raise ValueError(f"{path} must be an object.")
        field = str(raw_condition.get("field") or "").strip()
        if not field:
            raise ValueError(f"{path}.field is required.")
        operator = str(raw_condition.get("operator") or "").strip().lower()
        if operator not in SUPPORTED_OPERATORS:
            raise ValueError(f"{path}.operator '{operator}' is not supported.")

        has_value = "value" in raw_condition
        if operator in {"is_null", "is_not_null"}:
            value = None
        else:
            if not has_value:
                raise ValueError(f"{path}.value is required for operator '{operator}'.")
            value = cls._normalize_filter_value(
                raw_condition.get("value"),
                path=f"{path}.value",
                operator=operator,
                parameter_definitions_by_name=parameter_definitions_by_name,
            )

        normalized = {
            "field": field,
            "operator": operator,
        }
        if operator not in {"is_null", "is_not_null"}:
            normalized["value"] = value
        return normalized

    @classmethod
    def _normalize_filter_item(
        cls,
        raw_item: Any,
        path: str,
        parameter_definitions_by_name: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        if not isinstance(raw_item, dict):
            raise ValueError(f"{path} must be an object.")
        kind = str(raw_item.get("kind") or "condition").strip().lower()
        if kind == "group":
            logic = str(raw_item.get("logic") or "AND").strip().upper()
            if logic not in {"AND", "OR"}:
                raise ValueError(f"{path}.logic must be AND or OR.")
            raw_conditions = raw_item.get("conditions") or []
            if not isinstance(raw_conditions, list):
                raise ValueError(f"{path}.conditions must be an array.")
            conditions = [
                cls._normalize_filter_condition(
                    raw_condition,
                    f"{path}.conditions[{index}]",
                    parameter_definitions_by_name,
                )
                for index, raw_condition in enumerate(raw_conditions)
            ]
            if not conditions:
                raise ValueError(f"{path}.conditions must contain at least one condition.")
            return {
                "kind": "group",
                "logic": logic,
                "conditions": conditions,
            }
        if kind != "condition":
            raise ValueError(f"{path}.kind must be 'condition' or 'group'.")
        return {
            "kind": "condition",
            **cls._normalize_filter_condition(raw_item, path, parameter_definitions_by_name),
        }

    @classmethod
    def _compile_filter_item(
        cls,
        available_columns: dict[str, Any],
        item: dict[str, Any],
        resolved_parameters: dict[str, Any],
    ):
        if item["kind"] == "condition":
            return cls._compile_condition(available_columns, item, resolved_parameters)
        conditions = [
            cls._compile_condition(available_columns, condition, resolved_parameters)
            for condition in item.get("conditions") or []
        ]
        if item.get("logic") == "OR":
            return or_(*conditions)
        return and_(*conditions)

    @classmethod
    def _normalize_parameter_definition(cls, raw_parameter: Any, path: str) -> dict[str, Any]:
        if not isinstance(raw_parameter, dict):
            raise ValueError(f"{path} must be an object.")
        name = str(raw_parameter.get("name") or "").strip()
        if not name:
            raise ValueError(f"{path}.name is required.")
        parameter_type = str(raw_parameter.get("type") or "").strip().lower()
        if parameter_type not in DATASET_PARAMETER_TYPE_NAMES:
            raise ValueError(f"{path}.type '{parameter_type}' is not supported.")
        has_default_value = "default_value" in raw_parameter
        raw_default_binding = raw_parameter.get("default_binding")
        if has_default_value and raw_default_binding is not None:
            raise ValueError(f"{path} cannot declare both default_value and default_binding.")
        normalized = {
            "name": name,
            "type": parameter_type,
            "description": str(raw_parameter.get("description") or "").strip() or None,
        }
        if has_default_value:
            normalized["default_value"] = raw_parameter.get("default_value")
        if normalized.get("default_value") is not None:
            try:
                coerced_default = DatasetParameterResolver.coerce_value(
                    parameter_type,
                    normalized["default_value"],
                )
            except ValueError as exc:
                raise ValueError(f"{path}.default_value {str(exc).rstrip('.')}.".replace("..", ".")) from exc
            normalized["default_value"] = cls._serialize_parameter_default_value(coerced_default)
        if raw_default_binding is not None:
            normalized["default_binding"] = cls._normalize_parameter_default_binding(
                raw_default_binding,
                path=f"{path}.default_binding",
            )
        return normalized

    @classmethod
    def _normalize_parameter_default_binding(cls, raw_default_binding: Any, path: str) -> dict[str, str]:
        if not isinstance(raw_default_binding, dict):
            raise ValueError(f"{path} must be an object.")
        kind = str(raw_default_binding.get("kind") or "").strip().lower()
        if kind != "built_in":
            raise ValueError(f"{path}.kind must be 'built_in'.")
        resolver = str(raw_default_binding.get("resolver") or "").strip()
        if resolver not in SUPPORTED_DATASET_BUILT_IN_RESOLVERS:
            supported = ", ".join(SUPPORTED_DATASET_BUILT_IN_RESOLVERS)
            raise ValueError(f"{path}.resolver must be one of: {supported}.")
        return {
            "kind": kind,
            "resolver": resolver,
        }

    @classmethod
    def _normalize_filter_value(
        cls,
        raw_value: Any,
        *,
        path: str,
        operator: str,
        parameter_definitions_by_name: dict[str, dict[str, Any]],
    ) -> Any:
        if isinstance(raw_value, dict) and str(raw_value.get("kind") or "").strip().lower() == "parameter":
            parameter_name = str(raw_value.get("name") or "").strip()
            if not parameter_name:
                raise ValueError(f"{path}.name is required for parameter references.")
            parameter_definition = parameter_definitions_by_name.get(parameter_name)
            if parameter_definition is None:
                raise ValueError(f"{path} references unknown dataset parameter '{parameter_name}'.")
            if operator in {"in", "not_in"}:
                raise ValueError(f"{path} does not support parameter references for operator '{operator}'.")
            if not DatasetParameterResolver.is_operator_compatible(
                parameter_definition.get("type"),
                operator,
            ):
                raise ValueError(
                    f"{path} parameter '{parameter_name}' with type "
                    f"'{parameter_definition.get('type')}' is not compatible with operator '{operator}'."
                )
            return {
                "kind": "parameter",
                "name": parameter_name,
            }

        if operator in {"in", "not_in"}:
            if not isinstance(raw_value, list) or not raw_value:
                raise ValueError(f"{path} must be a non-empty array for operator '{operator}'.")
        if operator in STRING_OPERATORS and not isinstance(raw_value, str):
            raise ValueError(f"{path} must be a string for operator '{operator}'.")
        return raw_value
