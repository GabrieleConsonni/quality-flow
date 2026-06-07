import streamlit as st

from brokers.components.queues_component import render_queues_component
from brokers.services.data_loader_service import load_brokers


def _get_query_param(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value

load_brokers()

broker_id = (
    _get_query_param("broker_id")
    or st.session_state.get("queues_filter_broker_id")
    or st.session_state.get("selected_broker_id")
)

brokers = st.session_state.get("brokers", [])
selected_broker = None

if isinstance(brokers, list):
    selected_broker = next(
        (
            broker_item
            for broker_item in brokers
            if isinstance(broker_item, dict) and str(broker_item.get("id")) == str(broker_id)
        ),
        None,
    )

if selected_broker:
    selected_broker_id = selected_broker.get("id")
    st.session_state["selected_broker_id"] = selected_broker_id
    st.session_state["queues_filter_broker_id"] = selected_broker_id
    if str(_get_query_param("broker_id")) != str(selected_broker_id):
        st.query_params["broker_id"] = selected_broker_id

if not selected_broker:
    st.info("Broker non trovato. Seleziona un broker dalla sidebar.")
    st.stop()

st.subheader(f"Broker [{selected_broker.get('description', selected_broker.get('code', ''))}]")
st.caption("Configure queues for this broker to start sending messages and testing suites.")
st.divider()

render_queues_component(
    broker=selected_broker
)

