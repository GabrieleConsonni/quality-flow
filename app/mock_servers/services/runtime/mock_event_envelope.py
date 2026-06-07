from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def build_api_event_envelope(
    *,
    mock_server_id: str,
    trigger_id: str,
    trigger_description: str,
    method: str,
    payload: Any,
    headers: dict[str, Any] | None = None,
    query_params: dict[str, Any] | None = None,
    path_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "source": "api",
        "mock_server_id": str(mock_server_id or "").strip(),
        "trigger": {
            "id": str(trigger_id or "").strip(),
            "description": str(trigger_description or "").strip(),
            "method": str(method or "").strip().upper(),
            "queue_code": "",
        },
        "timestamp": _utc_timestamp(),
        "payload": payload,
        "meta": {
            "headers": headers if isinstance(headers, dict) else {},
            "query": query_params if isinstance(query_params, dict) else {},
            "path_params": path_params if isinstance(path_params, dict) else {},
        },
    }


def build_queue_event_envelope(
    *,
    mock_server_id: str,
    queue_id: str,
    queue_code: str,
    payload: Any,
    messages: list[dict] | None = None,
) -> dict[str, Any]:
    message_attributes: list[dict] = []
    message_ids: list[str] = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        message_id = str(message.get("MessageId") or "").strip()
        if message_id:
            message_ids.append(message_id)
        attrs = message.get("MessageAttributes")
        if isinstance(attrs, dict):
            message_attributes.append(attrs)

    return {
        "id": str(uuid4()),
        "source": "queue",
        "mock_server_id": str(mock_server_id or "").strip(),
        "trigger": {
            "id": str(queue_id or "").strip(),
            "description": "",
            "method": "",
            "queue_code": str(queue_code or "").strip(),
        },
        "timestamp": _utc_timestamp(),
        "payload": payload,
        "meta": {
            "message_attributes": message_attributes,
            "message_id": message_ids,
        },
    }
