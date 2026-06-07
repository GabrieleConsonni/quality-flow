import streamlit as st

from queues.components.queue_details_component import render_queue_details_component
from queues.services.queue_service import (
    load_queue_data,
    resolve_queue_context,
    sync_queue_context,
)

broker_id, queue_id = resolve_queue_context()

if broker_id and queue_id:
    sync_queue_context(broker_id, queue_id)

if st.button("Back to broker", icon=":material/arrow_back:"):
    if broker_id:
        st.session_state["selected_broker_id"] = broker_id
        st.session_state["queues_filter_broker_id"] = broker_id
        st.session_state["nav_broker_id"] = broker_id
    st.switch_page("pages/Queues.py")

if not broker_id or not queue_id:
    st.error("Queue non selezionata. Apri questa pagina dalla lista queue in Queues.")
    st.stop()

queue_data = load_queue_data(broker_id, queue_id)
if not queue_data:
    st.error("Errore caricamento dettaglio queue.")
    st.stop()

render_queue_details_component(queue_data, broker_id, queue_id)

