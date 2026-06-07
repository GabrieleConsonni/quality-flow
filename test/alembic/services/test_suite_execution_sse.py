import queue
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.elaborations.services.suite_runs.execution_event_bus import (
    _SUBSCRIBERS,
    publish_execution_event,
    subscribe_to_execution,
    stream_execution_events,
    unsubscribe_from_execution,
)
from app.elaborations.services.test_suites.test_suite_executor_thread import (
    _resolve_tests_to_execute,
)
from exceptions.app_exception import QualityFlowAppException


def _test(test_id: str):
    return SimpleNamespace(id=test_id)


def test_resolve_tests_to_execute_single_test():
    tests = [_test("s1"), _test("s2"), _test("s3")]
    resolved = _resolve_tests_to_execute(
        tests,
        target_suite_item_id="s2",
    )
    assert [item.id for item in resolved] == ["s2"]


def test_resolve_tests_to_execute_raises_when_missing_target():
    tests = [_test("s1"), _test("s2")]
    with pytest.raises(QualityFlowAppException, match="Test with id 'missing-test' not found"):
        _resolve_tests_to_execute(
            tests,
            target_suite_item_id="missing-test",
        )


def test_stream_execution_events_replays_history_and_finishes():
    execution_id = f"exec-{uuid4().hex[:8]}"
    publish_execution_event(execution_id, "execution_started", {"suite_id": "sc-1"})
    publish_execution_event(execution_id, "execution_finished", {"status": "success"})

    stream = stream_execution_events(execution_id)
    first = next(stream)
    second = next(stream)
    stream.close()

    assert "event: execution_started" in first
    assert "event: execution_finished" in second


def test_stream_execution_events_emits_heartbeat_when_idle(monkeypatch):
    execution_id = f"exec-heartbeat-{uuid4().hex[:8]}"
    queue_items: list[str] = []

    class FakeQueue:
        def __init__(self):
            self.calls = 0

        def get(self, timeout):
            self.calls += 1
            raise queue.Empty

    fake_queue = FakeQueue()
    monkeypatch.setattr(
        "app.elaborations.services.suite_runs.execution_event_bus.subscribe_to_execution",
        lambda _execution_id: (fake_queue, []),
    )
    monkeypatch.setattr(
        "app.elaborations.services.suite_runs.execution_event_bus.unsubscribe_from_execution",
        lambda _execution_id, _subscriber_queue: queue_items.append("unsubscribed"),
    )

    stream = stream_execution_events(execution_id)
    heartbeat = next(stream)
    stream.close()

    assert "event: heartbeat" in heartbeat
    assert queue_items == ["unsubscribed"]


def test_subscribe_and_unsubscribe_remove_subscriber():
    execution_id = f"exec-sub-{uuid4().hex[:8]}"
    subscriber_queue, _history = subscribe_to_execution(execution_id)

    assert subscriber_queue in _SUBSCRIBERS[execution_id]

    unsubscribe_from_execution(execution_id, subscriber_queue)

    assert execution_id not in _SUBSCRIBERS


def test_publish_execution_event_drops_when_subscriber_queue_is_full(monkeypatch):
    execution_id = f"exec-drop-{uuid4().hex[:8]}"
    subscriber_queue = queue.Queue(maxsize=1)
    subscriber_queue.put_nowait("already-full")
    _SUBSCRIBERS[execution_id].append(subscriber_queue)
    captured: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "app.elaborations.services.suite_runs.execution_event_bus._LOGGER.warning",
        lambda message, exec_id, event_name: captured.append((message, exec_id, event_name)),
    )
    try:
        publish_execution_event(execution_id, "execution_progress", {"test": 1})
    finally:
        unsubscribe_from_execution(execution_id, subscriber_queue)

    assert captured == [
        (
            "Dropping execution event because subscriber queue is full execution_id=%s event=%s",
            execution_id,
            "execution_progress",
        )
    ]
