from datetime import datetime

import streamlit as st

from api_client import api_get


def load_brokers(force: bool = False):
    if force or "brokers" not in st.session_state:
        try:
            st.session_state["brokers"] = api_get("/broker/connection")
        except Exception:
            st.session_state["brokers"] = []
            st.error("Errore caricamento broker")


def load_queues(broker_id: str | None):
    if not broker_id:
        return
    try:
        queues = api_get(f"/broker/{broker_id}/queue")
        st.session_state["queues"] = queues
        st.session_state["queues_for_broker_id"] = broker_id
        st.session_state["queues_loaded_at"] = datetime.now()
    except Exception:
        st.session_state["queues"] = []
        st.error("Errore caricamento code")


