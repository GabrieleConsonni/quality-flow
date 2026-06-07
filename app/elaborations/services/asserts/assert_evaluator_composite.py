from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationOperationDto,
    AssertEvaluatedObjectType,
    AssertType,
)
from elaborations.services.asserts.assert_evaluator import (
    AssertEvaluationContext,
    AssertEvaluator,
)
from elaborations.services.asserts.json_data_assert_evaluators import (
    ContainsDataAssertEvaluator,
    EmptyDataAssertEvaluator,
    EqualsDataAssertEvaluator,
    JsonArrayContainsDataAssertEvaluator,
    JsonArrayEqualsDataAssertEvaluator,
    NotEmptyDataAssertEvaluator,
    SchemaValidationDataAssertEvaluator,
)

_EVALUATOR_MAPPING: dict[tuple[str, str], type[AssertEvaluator]] = {
    (
        AssertEvaluatedObjectType.JSON_DATA.value,
        AssertType.NOT_EMPTY.value,
    ): NotEmptyDataAssertEvaluator,
    (
        AssertEvaluatedObjectType.JSON_DATA.value,
        AssertType.EMPTY.value,
    ): EmptyDataAssertEvaluator,
    (
        AssertEvaluatedObjectType.JSON_DATA.value,
        AssertType.SCHEMA_VALIDATION.value,
    ): SchemaValidationDataAssertEvaluator,
    (
        AssertEvaluatedObjectType.JSON_DATA.value,
        AssertType.CONTAINS.value,
    ): ContainsDataAssertEvaluator,
    (
        AssertEvaluatedObjectType.JSON_DATA.value,
        AssertType.JSON_ARRAY_EQUALS.value,
    ): JsonArrayEqualsDataAssertEvaluator,
    (
        AssertEvaluatedObjectType.JSON_DATA.value,
        AssertType.JSON_ARRAY_CONTAINS.value,
    ): JsonArrayContainsDataAssertEvaluator,
    (
        AssertEvaluatedObjectType.JSON_DATA.value,
        AssertType.EQUALS.value,
    ): EqualsDataAssertEvaluator,
}


def evaluate_assert(
    session: Session,
    cfg: AssertConfigurationOperationDto,
    data: list[dict],
    actual: object | None = None,
    expected: object | None = None,
) -> None:
    object_type = str(cfg.evaluated_object_type or "").strip().replace("_", "-").lower()
    assert_type = str(cfg.assert_type or "").strip().replace("_", "-").lower()
    clazz = _EVALUATOR_MAPPING.get((object_type, assert_type))
    if clazz is None:
        raise ValueError(
            f"Unsupported assert evaluator for object_type='{object_type}', "
            f"assert_type='{assert_type}'."
        )
    evaluator = clazz()
    evaluator.evaluate(
        AssertEvaluationContext(
            session=session,
            cfg=cfg,
            data=data if isinstance(data, list) else [],
            actual=actual,
            expected=expected,
        )
    )

