import streamlit as st

from database_connections.components.database_connections_component import (
    render_database_connections_component,
)
from database_connections.services.data_loader_service import load_database_connections

load_database_connections()

st.subheader("Database connections")
st.caption("Configure database connections for suites and database datasources.")
st.divider()

connections = st.session_state.get("database_connections", [])
render_database_connections_component(connections if isinstance(connections, list) else [])


