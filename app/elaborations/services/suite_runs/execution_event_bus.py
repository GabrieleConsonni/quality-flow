import json
import logging
import queue
import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Iterator

from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType

from elaborations.services.suite_runs.execution_runtime_context import (
    get_execution_id,
    get_suite_id,
    get_suite_test_id,
)

_HEARTBEAT_EVENT = "heartbeat"
_HEARTBEAT_INTERVAL_SECONDS = 10
_EVENT_HISTORY_SIZE = 500
_QUEUE_SIZE = 1000

_LOCK = threading.RLock()
_SUBSCRIBERS: dict[str, list[queue.Queue[str]]] = defaultdict(list)
_HISTORY: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=_EVENT_HISTORY_SIZE))
_LOGGER = logging.getLogger("quality-flow.execution_events")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_sse_frame(event_name: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=True, default=str)
    return f"event: {event_name}\ndata: {payload}\n\n"


def publish_execution_event(execution_id: str, event_name: str, payload: dict | None = None):
    if not execution_id:
        return
    event_payload = {
        "execution_id": execution_id,
        "event": event_name,
        "timestamp": _utc_now_iso(),
        **(payload or {}),
    }
    frame = _serialize_sse_frame(event_name, event_payload)
    with _LOCK:
        _HISTORY[execution_id].append(frame)
        subscribers = list(_SUBSCRIBERS.get(execution_id, []))
    for subscriber_queue in subscribers:
        try:
            subscriber_queue.put_nowait(frame)
        except queue.Full:
            _LOGGER.warning(
                "Dropping execution event because subscriber queue is full execution_id=%s event=%s",
                execution_id,
                event_name,
            )
            continue


def publish_runtime_log_event(
    *,
    subject_type: LogSubjectType,
    subject: str,
    level: LogLevel,
    message: str,
    payload: dict | list[dict] | None = None,
):
    execution_id = get_execution_id()
    if not execution_id:
        return
    publish_execution_event(
        execution_id,
        "execution_log",
        {
            "subject_type": subject_type.value,
            "subject": subject,
            "level": level.value,
            "message": message,
            "payload": payload,
            "suite_id": get_suite_id(),
            "suite_test_id": get_suite_test_id(),
        },
    )


def subscribe_to_execution(execution_id: str) -> tuple[queue.Queue[str], list[str]]:
    subscriber_queue: queue.Queue[str] = queue.Queue(maxsize=_QUEUE_SIZE)
    with _LOCK:
        _SUBSCRIBERS[execution_id].append(subscriber_queue)
        history = list(_HISTORY.get(execution_id, []))
    return subscriber_queue, history


def unsubscribe_from_execution(execution_id: str, subscriber_queue: queue.Queue[str]):
    with _LOCK:
        subscribers = _SUBSCRIBERS.get(execution_id, [])
        if subscriber_queue in subscribers:
            subscribers.remove(subscriber_queue)
        if not subscribers:
            _SUBSCRIBERS.pop(execution_id, None)


def stream_execution_events(execution_id: str) -> Iterator[str]:
    subscriber_queue, history = subscribe_to_execution(execution_id)
    try:
        finished_in_history = False
        for frame in history:
            yield frame
            if "event: execution_finished" in frame:
                finished_in_history = True
        if finished_in_history:
            return
        while True:
            try:
                frame = subscriber_queue.get(timeout=_HEARTBEAT_INTERVAL_SECONDS)
                yield frame
                if "event: execution_finished" in frame:
                    break
            except queue.Empty:
                yield _serialize_sse_frame(
                    _HEARTBEAT_EVENT,
                    {
                        "execution_id": execution_id,
                        "event": _HEARTBEAT_EVENT,
                        "timestamp": _utc_now_iso(),
                    },
                )
    finally:
        unsubscribe_from_execution(execution_id, subscriber_queue)
