import streamlit as st

from brokers.services.data_loader_service import load_brokers
from mock_servers.services.data_loader_service import load_mock_servers
from mock_servers.services.state_keys import SELECTED_MOCK_SERVER_ID_KEY

st.set_page_config(page_title="Quality Flow", layout="wide", page_icon=":material/construction:")

home = st.Page("pages/Home.py", title="Home")
brokers_page = st.Page("pages/Brokers.py", title="Brokers")
database_connections_page = st.Page(
    "pages/DatabaseConnections.py",
    title="Database Connections",
)
mock_servers_page = st.Page("pages/MockServers.py", title="Mock Servers")
mock_server_editor_page = st.Page("pages/MockServerEditor.py", title="Mock Server editor")
queues_page = st.Page("pages/Queues.py", title="Queues", url_path="queues")
queue_details = st.Page("pages/QueueDetails.py", title="Queue details")
json_array = st.Page("pages/JsonArray.py", title="Json Array")
datasets_page = st.Page("pages/Datasets.py", title="Datasets")
dataset_perimeter_editor = st.Page("pages/DatasetPerimeterEditor.py", title="Dataset perimeter editor")
test_suites = st.Page("pages/TestSuites.py", title="Test Suites", url_path="test-suites")
test_editor = st.Page("pages/TestEditor.py", title="Test editor")
advanced_suite_editor_settings = st.Page(
    "pages/AdvancedSuiteEditorSettings.py",
    title="Advanced suite editor settings",
)
test_suite_schedules = st.Page("pages/TestSuiteSchedules.py", title="Test Suite Scheduler")
tools = st.Page("pages/Tools.py", title="Tools")
logs = st.Page("pages/Logs.py", title="Logs")


def _sidebar_nav_button(label: str, page_path: str, key: str, icon: str = ":material/check:"):
    _, label_col = st.sidebar.columns([1, 10], gap="small", vertical_alignment="center")
    with label_col:
        if st.button(label, key=key, icon=icon, type="tertiary"):
            st.switch_page(page_path)

load_brokers()
load_mock_servers()
brokers = st.session_state.get("brokers", [])
mock_servers = st.session_state.get("mock_servers", [])

st.sidebar.title("Quality Flow")
_sidebar_nav_button(
    label="Home",
    page_path="pages/Home.py",
    key="nav_home_page",
    icon=":material/home:",
)
st.sidebar.subheader("Configurations")
_sidebar_nav_button(
    label="SQS broker connections",
    page_path="pages/Brokers.py",
    key="nav_brokers_page",
    icon=":material/cell_tower:",
)
_sidebar_nav_button(
    label="Database connections (Beta)",
    page_path="pages/DatabaseConnections.py",
    key="nav_database_connections_page",
    icon=":material/database:",
)
_sidebar_nav_button(
    label="Mock servers (Beta)",
    page_path="pages/MockServers.py",
    key="nav_mock_servers_page",
    icon=":material/deployed_code:",
)

st.sidebar.subheader("SQS brokers")
for broker in brokers:
    broker_id = broker.get("id")
    if broker_id:
        _, label_col = st.sidebar.columns([1, 10], gap="small", vertical_alignment="center")
        with label_col:
            if st.button(
                f"{broker.get('description') or broker.get('code') or broker_id}",
                key=f"open_queues_sidebar_{broker_id}",
                icon=":material/clear_all:",
                type="tertiary"
            ):
                st.session_state["selected_broker_id"] = broker_id
                st.session_state["queues_filter_broker_id"] = broker_id
                st.session_state["nav_broker_id"] = broker_id
                st.switch_page("pages/Queues.py")

st.sidebar.subheader("Datasources")
_sidebar_nav_button(
    label="Json Array",
    page_path="pages/JsonArray.py",
    key="nav_json_array_page",
    icon=":material/data_array:",
)
_sidebar_nav_button(
    label="Datasets (Beta)",
    page_path="pages/Datasets.py",
    key="nav_database_datasources_page",
    icon=":material/table:",
)
st.sidebar.subheader("Test")
_sidebar_nav_button(
    label="Test suites (Beta)",
    page_path="pages/TestSuites.py",
    key="nav_test_suites_page",
    icon=":material/experiment:",
)
_sidebar_nav_button(
    label="Test suite scheduler (Beta)",
    page_path="pages/TestSuiteSchedules.py",
    key="nav_test_suite_schedules_page",
    icon=":material/schedule:",
)
st.sidebar.subheader("Mock Servers (Beta)")
for server in mock_servers if isinstance(mock_servers, list) else []:
    server_id = str(server.get("id") or "").strip()
    endpoint = str(server.get("endpoint") or "").strip()
    if not server_id:
        continue
    label = str(server.get("description") or server.get("code") or endpoint or server_id)
    icon = ":material/play_circle:" if bool(server.get("is_active")) else ":material/pause_circle:"
    _, label_col = st.sidebar.columns([1, 10], gap="small", vertical_alignment="center")
    with label_col:
        if st.button(
            label,
            key=f"open_mock_server_sidebar_{server_id}",
            icon=icon,
            type="tertiary",
        ):
            st.session_state[SELECTED_MOCK_SERVER_ID_KEY] = server_id
            st.switch_page("pages/MockServerEditor.py")
st.sidebar.subheader("Logs")
_sidebar_nav_button(
    label="Logs",
    page_path="pages/Logs.py",
    key="nav_logs_page",
    icon=":material/article:",
)


pg = st.navigation(
    {
        "Home": [home],
        "Configurations": [brokers_page, database_connections_page, mock_servers_page],
        "Brokers & Queues": [queues_page, queue_details],
        "Data Sources": [json_array, datasets_page, dataset_perimeter_editor],
        "Test Suites": [
            test_suites,
            test_editor,
            advanced_suite_editor_settings,
            test_suite_schedules,
        ],
        "Mock Servers": [mock_server_editor_page],
        "Logs & Tools": [logs, tools]
    },
    position="hidden",
)

pg.run()
