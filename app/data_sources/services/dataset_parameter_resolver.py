from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

DATASET_PARAMETER_TYPE_NAMES = {
    "string",
    "integer",
    "number",
    "boolean",
    "date",
    "datetime",
}
SUPPORTED_DATASET_BUILT_IN_RESOLVERS = ("$now", "$today")


class DatasetParameterResolutionError(ValueError):
    CODE = "DATASET_PARAMETER_RESOLUTION_FAILED"

    def __init__(self, dataset_id: str | None, parameter: str, reason: str):
        self.dataset_id = str(dataset_id or "").strip()
        self.parameter = str(parameter or "").strip()
        self.reason = str(reason or "").strip() or "Unknown error."
        super().__init__(str(self))

    def __str__(self) -> str:
        dataset_token = self.dataset_id or "-"
        parameter_token = self.parameter or "-"
        return (
            f"{self.CODE}: dataset_id={dataset_token}; "
            f"parameter={parameter_token}; reason={self.reason}"
        )


class DatasetParameterResolver:
    @classmethod
    def resolve(
        cls,
        perimeter: dict | None,
        explicit_values: dict | None = None,
        *,
        dataset_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_perimeter = perimeter if isinstance(perimeter, dict) else {}
        parameter_definitions = normalized_perimeter.get("parameters") or []
        if not parameter_definitions:
            return {}

        if explicit_values is None:
            normalized_explicit_values: dict[str, Any] = {}
        elif isinstance(explicit_values, dict):
            normalized_explicit_values = dict(explicit_values)
        else:
            raise ValueError("Dataset parameter overrides must be an object.")

        definitions_by_name = {
            str(definition.get("name") or "").strip(): definition
            for definition in parameter_definitions
            if isinstance(definition, dict) and str(definition.get("name") or "").strip()
        }

        for parameter_name in normalized_explicit_values.keys():
            if str(parameter_name or "").strip() not in definitions_by_name:
                raise ValueError(f"Unknown dataset parameter '{parameter_name}'.")

        resolved: dict[str, Any] = {}
        for definition in parameter_definitions:
            if not isinstance(definition, dict):
                continue
            parameter_name = str(definition.get("name") or "").strip()
            if not parameter_name:
                continue
            if parameter_name in normalized_explicit_values:
                try:
                    resolved[parameter_name] = cls.coerce_value(
                        definition.get("type"),
                        normalized_explicit_values[parameter_name],
                    )
                except ValueError as exc:
                    raise DatasetParameterResolutionError(dataset_id, parameter_name, str(exc)) from exc
                continue
            resolved[parameter_name] = cls._resolve_default_value(
                definition,
                dataset_id=dataset_id,
            )
        return resolved

    @classmethod
    def resolve_builtin(cls, resolver_name: str) -> Any:
        normalized_resolver = str(resolver_name or "").strip()
        if normalized_resolver not in SUPPORTED_DATASET_BUILT_IN_RESOLVERS:
            raise ValueError(f"Unsupported dataset built-in resolver '{normalized_resolver}'.")
        if normalized_resolver == "$now":
            return datetime.now()
        return date.today()

    @classmethod
    def coerce_value(cls, parameter_type: object, value: Any) -> Any:
        normalized_type = str(parameter_type or "").strip().lower()
        if normalized_type not in DATASET_PARAMETER_TYPE_NAMES:
            raise ValueError(f"Unsupported dataset parameter type '{parameter_type}'.")
        if value is None:
            return None
        if normalized_type == "string":
            return str(value)
        if normalized_type == "integer":
            return cls._coerce_integer(value)
        if normalized_type == "number":
            return cls._coerce_number(value)
        if normalized_type == "boolean":
            return cls._coerce_boolean(value)
        if normalized_type == "date":
            return cls._coerce_date(value)
        if normalized_type == "datetime":
            return cls._coerce_datetime(value)
        raise ValueError(f"Unsupported dataset parameter type '{parameter_type}'.")

    @classmethod
    def is_operator_compatible(cls, parameter_type: object, operator: object) -> bool:
        normalized_type = str(parameter_type or "").strip().lower()
        normalized_operator = str(operator or "").strip().lower()
        if normalized_operator in {"eq", "neq"}:
            return normalized_type in DATASET_PARAMETER_TYPE_NAMES
        if normalized_operator in {"gt", "gte", "lt", "lte"}:
            return normalized_type in {"integer", "number", "date", "datetime"}
        if normalized_operator in {"contains", "starts_with", "ends_with"}:
            return normalized_type == "string"
        return False

    @classmethod
    def _resolve_default_value(
        cls,
        definition: dict,
        *,
        dataset_id: str | None,
    ) -> Any:
        parameter_name = str(definition.get("name") or "").strip()
        parameter_type = definition.get("type")

        if "default_value" in definition:
            default_value = definition.get("default_value")
            if default_value is not None:
                try:
                    return cls.coerce_value(parameter_type, default_value)
                except ValueError as exc:
                    raise DatasetParameterResolutionError(dataset_id, parameter_name, str(exc)) from exc
        default_binding = definition.get("default_binding")
        if default_binding is not None:
            try:
                resolved_value = cls.resolve_builtin(
                    str((default_binding or {}).get("resolver") or "").strip()
                )
                return cls.coerce_value(parameter_type, resolved_value)
            except ValueError as exc:
                raise DatasetParameterResolutionError(dataset_id, parameter_name, str(exc)) from exc
        return None

    @staticmethod
    def _coerce_integer(value: Any) -> int:
        if isinstance(value, bool):
            raise ValueError("Expected integer value.")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            raw = value.strip()
            if raw.lstrip("-").isdigit():
                return int(raw)
        raise ValueError("Expected integer value.")

    @staticmethod
    def _coerce_number(value: Any) -> int | float:
        if isinstance(value, bool):
            raise ValueError("Expected number value.")
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            raw = value.strip()
            try:
                parsed = float(raw)
            except ValueError as exc:
                raise ValueError("Expected number value.") from exc
            return int(parsed) if parsed.is_integer() else parsed
        raise ValueError("Expected number value.")

    @staticmethod
    def _coerce_boolean(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            mapping = {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
                "yes": True,
                "no": False,
            }
            if normalized in mapping:
                return mapping[normalized]
        if isinstance(value, int) and value in {0, 1}:
            return bool(value)
        raise ValueError("Expected boolean value.")

    @classmethod
    def _coerce_date(cls, value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            raw = value.strip()
            try:
                return date.fromisoformat(raw)
            except ValueError:
                return cls._coerce_datetime(raw).date()
        raise ValueError("Expected date value.")

    @classmethod
    def _coerce_datetime(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, time.min)
        if isinstance(value, str):
            raw = value.strip()
            if raw.endswith("Z"):
                raw = f"{raw[:-1]}+00:00"
            try:
                return datetime.fromisoformat(raw)
            except ValueError as exc:
                raise ValueError("Expected datetime value.") from exc
        raise ValueError("Expected datetime value.")
