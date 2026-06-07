import pytest

from app.elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
)
from app.elaborations.services.asserts.assert_evaluator import (
    AssertEvaluationContext,
    AssertEvaluator,
)
from app.elaborations.services.asserts.assert_evaluator_composite import (
    _EVALUATOR_MAPPING,
    evaluate_assert,
)


class _RecordingEvaluator(AssertEvaluator):
    calls: list[AssertEvaluationContext] = []

    def evaluate(self, context: AssertEvaluationContext) -> None:
        self.calls.append(context)


def test_evaluate_assert_dispatches_to_configured_evaluator(monkeypatch):
    original = _EVALUATOR_MAPPING.get(("json-data", "not-empty"))
    monkeypatch.setitem(
        _EVALUATOR_MAPPING,
        ("json-data", "not-empty"),
        _RecordingEvaluator,
    )
    _RecordingEvaluator.calls.clear()

    cfg = AssertConfigurationCommandDto(
        commandCode="jsonNotEmpty",
        commandType="assert",
        evaluated_object_type="json-data",
    )
    evaluate_assert(
        session=None,
        cfg=cfg,
        data=[{"id": 1}],
        actual={"value": 1},
        expected={"value": 1},
    )

    assert len(_RecordingEvaluator.calls) == 1
    context = _RecordingEvaluator.calls[0]
    assert context.data == [{"id": 1}]
    assert context.actual == {"value": 1}
    assert context.expected == {"value": 1}
    if original is not None:
        monkeypatch.setitem(
            _EVALUATOR_MAPPING,
            ("json-data", "not-empty"),
            original,
        )


def test_evaluate_assert_raises_when_evaluator_is_missing(monkeypatch):
    original = _EVALUATOR_MAPPING.get(("json-data", "not-empty"))
    monkeypatch.delitem(_EVALUATOR_MAPPING, ("json-data", "not-empty"), raising=False)
    cfg = AssertConfigurationCommandDto(
        commandCode="jsonNotEmpty",
        commandType="assert",
        evaluated_object_type="json-data",
    )

    with pytest.raises(ValueError, match="Unsupported assert evaluator"):
        evaluate_assert(session=None, cfg=cfg, data=[])
    if original is not None:
        monkeypatch.setitem(
            _EVALUATOR_MAPPING,
            ("json-data", "not-empty"),
            original,
        )

