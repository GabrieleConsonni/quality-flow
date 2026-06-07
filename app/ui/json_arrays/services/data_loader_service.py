import streamlit as st

from api_client import api_get


def load_json_arrays(force: bool = False):
    if force or "json_arrays" not in st.session_state:
        try:
            st.session_state["json_arrays"] = api_get("/data-source/json-array")
        except Exception:
            st.session_state["json_arrays"] = []
            st.error("Errore caricamento json-array")
