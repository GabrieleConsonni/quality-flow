import json
from collections import Counter

from jsonschema import SchemaError, ValidationError, validate as json_schema_validate

from _alembic.models.json_payload_entity import JsonPayloadEntity
from json_utils.models.enums.json_type import JsonType
from json_utils.services.alembic.json_files_service import JsonFilesService

from elaborations.services.asserts.assert_evaluator import (
    AssertEvaluationContext,
    AssertEvaluator,
)


def _normalize_rows(value: object, label: str) -> list[dict]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON array.")
    rows: list[dict] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{label} item at index {index} must be a JSON object.")
        rows.append(item)
    return rows


def _normalize_json_object(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def _is_empty_json_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, (dict, list, str)):
        return len(value) == 0
    return False


def _serialize_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)


def _build_multiset(rows: list[dict], compare_keys: list[str], label: str) -> Counter:
    multiset = Counter()
    for index, row in enumerate(rows):
        missing_keys = [key for key in compare_keys if key not in row]
        if missing_keys:
            raise ValueError(
                f"{label} item at index {index} is missing compare_keys: {missing_keys}"
            )
        key = tuple(_serialize_value(row.get(compare_key)) for compare_key in compare_keys)
        multiset[key] += 1
    return multiset


def _load_expected_json_array_rows(context: AssertEvaluationContext) -> list[dict]:
    if context.expected is not None:
        expected_payload = context.expected
        if isinstance(expected_payload, dict):
            return [expected_payload]
        return _normalize_rows(expected_payload, "Expected value")

    expected_json_array_id = str(context.cfg.expected_json_array_id or "").strip()
    if not expected_json_array_id:
        raise ValueError("expected_json_array_id is required.")

    entity: JsonPayloadEntity = JsonFilesService().get_by_id(
        context.session,
        expected_json_array_id,
    )
    if not entity:
        raise ValueError(f"Expected json-array '{expected_json_array_id}' not found.")
    if str(entity.json_type or "").strip() != JsonType.JSON_ARRAY.value:
        raise ValueError(
            f"Datasource '{expected_json_array_id}' is not of type '{JsonType.JSON_ARRAY.value}'."
        )

    payload = entity.payload
    if isinstance(payload, dict):
        return [payload]
    return _normalize_rows(payload, "Expected json-array payload")


class NotEmptyDataAssertEvaluator(AssertEvaluator):
    def evaluate(self, context: AssertEvaluationContext) -> None:
        if _is_empty_json_value(context.actual):
            raise ValueError("Assert failed: expected actual value to be not empty.")


class EmptyDataAssertEvaluator(AssertEvaluator):
    def evaluate(self, context: AssertEvaluationContext) -> None:
        if not _is_empty_json_value(context.actual):
            raise ValueError("Assert failed: expected actual value to be empty.")


class SchemaValidationDataAssertEvaluator(AssertEvaluator):
    def evaluate(self, context: AssertEvaluationContext) -> None:
        schema = context.cfg.json_schema
        if not isinstance(schema, dict):
            raise ValueError("Assert failed: json_schema is required.")

        rows = _normalize_rows(context.data, "Actual data")
        for index, row in enumerate(rows):
            try:
                json_schema_validate(instance=row, schema=schema)
            except ValidationError as exc:
                raise ValueError(
                    f"Assert failed: row {index} does not match json schema ({exc.message})."
                ) from exc
            except SchemaError as exc:
                raise ValueError(
                    f"Assert failed: invalid json schema ({exc.message})."
                ) from exc


class ContainsDataAssertEvaluator(AssertEvaluator):
    def evaluate(self, context: AssertEvaluationContext) -> None:
        compare_keys = list(context.cfg.compare_keys or [])
        if not compare_keys:
            raise ValueError("Assert failed: compare_keys is required.")
        actual_value = _normalize_json_object(context.actual, "Actual value")
        expected_value = _normalize_json_object(context.expected, "Expected value")

        missing_expected_keys = [key for key in compare_keys if key not in expected_value]
        if missing_expected_keys:
            raise ValueError(
                f"Expected value is missing compare_keys: {missing_expected_keys}"
            )

        missing_actual_keys = [key for key in compare_keys if key not in actual_value]
        if missing_actual_keys:
            raise ValueError(
                f"Actual value is missing compare_keys: {missing_actual_keys}"
            )

        for key in compare_keys:
            if actual_value.get(key) != expected_value.get(key):
                raise ValueError(
                    "Assert failed: actual value does not contain expected values."
                )


class JsonArrayContainsDataAssertEvaluator(AssertEvaluator):
    def evaluate(self, context: AssertEvaluationContext) -> None:
        compare_keys = list(context.cfg.compare_keys or [])
        if not compare_keys:
            raise ValueError("Assert failed: compare_keys is required.")

        actual_rows = _normalize_rows(context.data, "Actual data")
        expected_rows = _load_expected_json_array_rows(context)

        actual_multiset = _build_multiset(actual_rows, compare_keys, "Actual data")
        expected_multiset = _build_multiset(
            expected_rows,
            compare_keys,
            "Expected json-array payload",
        )

        for item_key, actual_count in actual_multiset.items():
            expected_count = expected_multiset.get(item_key, 0)
            if actual_count > expected_count:
                raise ValueError(
                    "Assert failed: actual data is not contained in expected json-array."
                )


class JsonArrayEqualsDataAssertEvaluator(AssertEvaluator):
    def evaluate(self, context: AssertEvaluationContext) -> None:
        compare_keys = list(context.cfg.compare_keys or [])
        if not compare_keys:
            raise ValueError("Assert failed: compare_keys is required.")

        actual_rows = _normalize_rows(context.data, "Actual data")
        expected_rows = _load_expected_json_array_rows(context)

        actual_multiset = _build_multiset(actual_rows, compare_keys, "Actual data")
        expected_multiset = _build_multiset(
            expected_rows,
            compare_keys,
            "Expected json-array payload",
        )

        if actual_multiset != expected_multiset:
            raise ValueError(
                "Assert failed: actual data is not equal to expected json-array."
            )


class EqualsDataAssertEvaluator(AssertEvaluator):
    def evaluate(self, context: AssertEvaluationContext) -> None:
        if context.actual != context.expected:
            raise ValueError("Assert failed: actual value is not equal to expected value.")
