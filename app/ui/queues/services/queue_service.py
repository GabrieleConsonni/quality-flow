import streamlit as st

from api_client import api_get, api_post, api_put


def get_query_param(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def resolve_queue_context() -> tuple[str | None, str | None]:
    query_broker_id = get_query_param("broker_id")
    query_queue_id = get_query_param("queue_id")

    broker_id = (
        query_broker_id
        or st.session_state.get("nav_broker_id")
        or st.session_state.get("selected_broker_id")
    )
    queue_id = query_queue_id or st.session_state.get("nav_queue_id")
    return broker_id, queue_id


def sync_queue_context(broker_id: str, queue_id: str):
    st.session_state["selected_broker_id"] = broker_id
    st.session_state["queues_filter_broker_id"] = broker_id
    st.session_state["nav_broker_id"] = broker_id
    st.session_state["nav_queue_id"] = queue_id
    st.query_params["broker_id"] = broker_id
    st.query_params["queue_id"] = queue_id


def load_queue_data(broker_id: str, queue_id: str) -> dict | None:
    try:
        queues = api_get(f"/broker/{broker_id}/queue")
        queue_item = next((item for item in queues if item.get("id") == queue_id), None)
        if queue_item:
            return queue_item
        queue_item = api_get(f"/broker/{broker_id}/queue/{queue_id}")
        queue_item["messages_sent"] = None
        queue_item["messages_received"] = None
        return queue_item
    except Exception:
        return None


def test_queue_connection(broker_id: str, queue_id: str) -> dict:
    return api_get(f"/broker/{broker_id}/queue/{queue_id}/test")


def send_queue_messages(broker_id: str, queue_id: str, messages: list[object]) -> list[dict]:
    return api_post(
        f"/broker/{broker_id}/queue/{queue_id}/messages",
        {"messages": messages},
    )


def receive_queue_messages(broker_id: str, queue_id: str, count: int = 10) -> list[dict]:
    return api_get(f"/broker/{broker_id}/queue/{queue_id}/messages?count={count}")

def receive_queue_messages_ack(broker_id: str, queue_id: str, messages:list[dict]) -> list[dict]:
    return api_put(f"/broker/{broker_id}/queue/{queue_id}/messages", {"messages": messages})

def load_json_arrays() -> list[dict]:
    return api_get("/data-source/json-array")


def save_json_array(description: str, payload: list[object]) -> dict:
    return api_post(
        "/data-source/json-array",
        {
            "description": description,
            "payload": payload,
        },
    )
