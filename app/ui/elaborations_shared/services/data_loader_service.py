import streamlit as st

from elaborations_shared.services.api_service import (
    get_all_brokers,
    get_all_database_datasources,
    get_all_json_arrays,
    get_queues_by_broker_id,
)
from elaborations_shared.services.state_keys import (
    TEST_EDITOR_BROKERS_KEY,
    TEST_EDITOR_DATABASE_DATASOURCES_KEY,
    TEST_EDITOR_JSON_ARRAYS_KEY,
    TEST_EDITOR_QUEUES_BY_BROKER_KEY,
)


def load_test_editor_json_arrays(force: bool = False):
    if force or TEST_EDITOR_JSON_ARRAYS_KEY not in st.session_state:
        try:
            st.session_state[TEST_EDITOR_JSON_ARRAYS_KEY] = get_all_json_arrays()
        except Exception:
            st.session_state[TEST_EDITOR_JSON_ARRAYS_KEY] = []
            st.error("Errore caricamento json-array per test.")


def load_test_editor_database_datasources(force: bool = False):
    if force or TEST_EDITOR_DATABASE_DATASOURCES_KEY not in st.session_state:
        try:
            st.session_state[TEST_EDITOR_DATABASE_DATASOURCES_KEY] = (
                get_all_database_datasources()
            )
        except Exception:
            st.session_state[TEST_EDITOR_DATABASE_DATASOURCES_KEY] = []
            st.error("Errore caricamento database datasources per test.")


def load_test_editor_brokers(force: bool = False):
    if force or TEST_EDITOR_BROKERS_KEY not in st.session_state:
        try:
            st.session_state[TEST_EDITOR_BROKERS_KEY] = get_all_brokers()
        except Exception:
            st.session_state[TEST_EDITOR_BROKERS_KEY] = []
            st.error("Errore caricamento broker per test.")


def load_test_editor_queues_for_broker(broker_id: str, force: bool = False) -> list[dict]:
    broker_id_value = str(broker_id or "").strip()
    if not broker_id_value:
        return []

    queues_by_broker = st.session_state.setdefault(TEST_EDITOR_QUEUES_BY_BROKER_KEY, {})
    if not isinstance(queues_by_broker, dict):
        queues_by_broker = {}
        st.session_state[TEST_EDITOR_QUEUES_BY_BROKER_KEY] = queues_by_broker

    if force or broker_id_value not in queues_by_broker:
        try:
            queues_by_broker[broker_id_value] = get_queues_by_broker_id(broker_id_value)
        except Exception:
            queues_by_broker[broker_id_value] = []
            st.error("Errore caricamento queue per broker nello test editor.")

    queues = queues_by_broker.get(broker_id_value)
    return queues if isinstance(queues, list) else []


def load_test_editor_context(force: bool = False):
    load_test_editor_json_arrays(force=force)
    load_test_editor_database_datasources(force=force)
    load_test_editor_brokers(force=force)

