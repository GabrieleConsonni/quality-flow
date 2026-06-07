import streamlit as st

from brokers.components.brokers_component import render_brokers_component
from brokers.services.data_loader_service import load_brokers

load_brokers()

brokers = st.session_state.get("brokers", [])
if not brokers:
    st.info("No brokers configured.")

broker_ids = [broker_item.get("id") for broker_item in brokers] if brokers else []
if brokers:
    if (
        "selected_broker_id" not in st.session_state
        or st.session_state["selected_broker_id"] not in broker_ids
    ):
        st.session_state["selected_broker_id"] = broker_ids[0]
else:
    st.session_state["selected_broker_id"] = None

st.subheader("Brokers list")
st.caption("Configure brokers and queues to start sending messages and testing suites.")
st.divider()

render_brokers_component(brokers)

