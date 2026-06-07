import streamlit as st

from mock_servers.services.mock_server_api_service import get_all_mock_servers

MOCK_SERVERS_KEY = "mock_servers"


def load_mock_servers(force: bool = False):
    if force or MOCK_SERVERS_KEY not in st.session_state:
        try:
            st.session_state[MOCK_SERVERS_KEY] = get_all_mock_servers()
        except Exception:
            st.session_state[MOCK_SERVERS_KEY] = []
            st.error("Errore caricamento mock servers")
