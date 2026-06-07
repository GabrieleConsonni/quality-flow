from types import SimpleNamespace

import pytest

from app.elaborations.services.suite_runs.suite_executor_thread import (
    _resolve_tests_to_execute as resolve_suite_tests_to_execute,
)
from app.elaborations.services.test_suites.test_suite_executor_thread import (
    _resolve_tests_to_execute as resolve_suite_items_to_execute,
)
from exceptions.app_exception import QualityFlowAppException


def _entity(entity_id: str):
    return SimpleNamespace(id=entity_id)


def test_resolve_tests_to_execute_returns_requested_prefix():
    tests = [_entity("s1"), _entity("s2"), _entity("s3")]

    resolved = resolve_suite_tests_to_execute(
        tests,
        target_suite_test_id="s2",
        include_previous=True,
    )

    assert [item.id for item in resolved] == ["s1", "s2"]


def test_resolve_tests_to_execute_returns_requested_item_only():
    tests = [_entity("t1"), _entity("t2"), _entity("t3")]

    resolved = resolve_suite_items_to_execute(
        tests,
        target_suite_item_id="t2",
    )

    assert [item.id for item in resolved] == ["t2"]


def test_resolve_tests_to_execute_raises_for_missing_target():
    tests = [_entity("t1"), _entity("t2")]

    with pytest.raises(QualityFlowAppException, match="Test with id 'missing' not found"):
        resolve_suite_items_to_execute(
            tests,
            target_suite_item_id="missing",
        )
