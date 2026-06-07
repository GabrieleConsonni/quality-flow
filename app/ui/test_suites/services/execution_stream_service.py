import json
import threading

import requests

from api_client import API_BASE_URL

_LOCK = threading.RLock()
_EXECUTION_STATES: dict[str, dict] = {}
_LISTENER_THREADS: dict[str, threading.Thread] = {}


def _new_execution_state(execution_id: str, test_suite_id: str) -> dict:
    return {
        "execution_id": execution_id,
        "test_suite_id": test_suite_id,
        "running": True,
        "status": "running",
        "executed_tests": 0,
        "total_tests": 0,
        "item_status": {},
        "item_error": {},
        "operation_status": {},
        "operation_error": {},
        "events": [],
        "error": None,
    }


def _operation_key(suite_item_id: str, operation_id: str) -> str:
    return f"{suite_item_id}:{operation_id}"


def _append_event(execution_id: str, event_name: str, data: dict):
    with _LOCK:
        state = _EXECUTION_STATES.get(execution_id)
        if not state:
            return
        state["events"].append({"event": event_name, "data": data})
        if len(state["events"]) > 1000:
            state["events"] = state["events"][-1000:]


def _apply_event(execution_id: str, event_name: str, data: dict):
    _append_event(execution_id, event_name, data)
    with _LOCK:
        state = _EXECUTION_STATES.get(execution_id)
        if not state:
            return

        if event_name == "suite_started":
            state["running"] = True
            state["status"] = "running"
            state["executed_tests"] = 0
            state["total_tests"] = 0
            state["item_status"] = {}
            state["item_error"] = {}
            state["operation_status"] = {}
            state["operation_error"] = {}
            return

        if event_name == "suite_progress":
            state["executed_tests"] = int(data.get("executed_tests") or 0)
            state["total_tests"] = int(data.get("total_tests") or 0)
            return

        if event_name in {"test_started", "hook_started"}:
            suite_item_id = str(data.get("suite_item_id") or "").strip()
            if suite_item_id:
                state["item_status"][suite_item_id] = "running"
            return

        if event_name in {"test_finished", "hook_finished"}:
            suite_item_id = str(data.get("suite_item_id") or "").strip()
            status = str(data.get("status") or "").strip() or "idle"
            if suite_item_id:
                state["item_status"][suite_item_id] = status
                if status == "error":
                    state["item_error"][suite_item_id] = str(data.get("error") or "")
                else:
                    state["item_error"].pop(suite_item_id, None)
            return

        if event_name == "operation_finished":
            suite_item_id = str(data.get("suite_item_id") or "").strip()
            operation_id = str(data.get("operation_id") or "").strip()
            status = str(data.get("status") or "").strip() or "idle"
            if suite_item_id and operation_id:
                operation_key = _operation_key(suite_item_id, operation_id)
                state["operation_status"][operation_key] = status
                if status == "error":
                    state["operation_error"][operation_key] = str(data.get("error") or "")
                else:
                    state["operation_error"].pop(operation_key, None)
            return

        if event_name == "suite_finished":
            state["running"] = False
            state["status"] = str(data.get("status") or "finished")
            return


def _iter_sse_events(response):
    event_name = "message"
    data_lines: list[str] = []
    for raw_line in response.iter_lines(decode_unicode=True):
        line = (raw_line or "").strip()
        if not line:
            if data_lines:
                payload_raw = "\n".join(data_lines)
                try:
                    payload = json.loads(payload_raw)
                except json.JSONDecodeError:
                    payload = {"raw": payload_raw}
                yield event_name, payload
            event_name = "message"
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip() or "message"
            continue
        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].lstrip())


def _listen_execution_events(execution_id: str):
    stream_url = f"{API_BASE_URL}/elaborations/execution/{execution_id}/events"
    try:
        with requests.get(stream_url, timeout=120, stream=True) as response:
            response.raise_for_status()
            for event_name, payload in _iter_sse_events(response):
                _apply_event(execution_id, event_name, payload)
                if event_name == "suite_finished":
                    break
    except Exception as exc:
        with _LOCK:
            state = _EXECUTION_STATES.get(execution_id)
            if state:
                state["running"] = False
                state["status"] = "error"
                state["error"] = str(exc)
    finally:
        with _LOCK:
            _LISTENER_THREADS.pop(execution_id, None)


def register_execution_listener(execution_id: str, test_suite_id: str):
    execution_id_value = str(execution_id or "").strip()
    suite_id_value = str(test_suite_id or "").strip()
    if not execution_id_value or not suite_id_value:
        return
    with _LOCK:
        if execution_id_value not in _EXECUTION_STATES:
            _EXECUTION_STATES[execution_id_value] = _new_execution_state(
                execution_id=execution_id_value,
                test_suite_id=suite_id_value,
            )
        if execution_id_value in _LISTENER_THREADS:
            return
        listener_thread = threading.Thread(
            target=_listen_execution_events,
            args=(execution_id_value,),
            daemon=True,
            name=f"test-suite-sse-{execution_id_value}",
        )
        _LISTENER_THREADS[execution_id_value] = listener_thread
    listener_thread.start()


def get_execution_state(execution_id: str) -> dict:
    execution_id_value = str(execution_id or "").strip()
    if not execution_id_value:
        return {}
    with _LOCK:
        state = _EXECUTION_STATES.get(execution_id_value)
        if not state:
            return {}
        return {
            **state,
            "item_status": dict(state.get("item_status") or {}),
            "item_error": dict(state.get("item_error") or {}),
            "operation_status": dict(state.get("operation_status") or {}),
            "operation_error": dict(state.get("operation_error") or {}),
            "events": list(state.get("events") or []),
        }
