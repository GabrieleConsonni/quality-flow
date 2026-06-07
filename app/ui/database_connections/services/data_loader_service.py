import streamlit as st

from api_client import api_get


DATABASE_CONNECTIONS_KEY = "database_connections"


def load_database_connections(force: bool = False):
    if force or DATABASE_CONNECTIONS_KEY not in st.session_state:
        try:
            result = api_get("/database/connection")
            st.session_state[DATABASE_CONNECTIONS_KEY] = (
                result if isinstance(result, list) else []
            )
        except Exception:
            st.session_state[DATABASE_CONNECTIONS_KEY] = []
            st.error("Errore caricamento connessioni database.")

