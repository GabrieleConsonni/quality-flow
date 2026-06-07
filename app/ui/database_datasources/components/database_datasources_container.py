import streamlit as st

from database_datasources.components.database_datasources_component import (
    render_database_datasources_component,
)
from database_datasources.components.dialogs import add_database_datasource_dialog
from database_datasources.services.data_loader_service import (
    load_database_connections,
    load_database_datasources,
)
from database_datasources.services.state_service import (
    ensure_selected_database_datasource_id,
    pop_database_datasource_feedback,
)


def _show_feedback():
    message, level = pop_database_datasource_feedback()
    if not message:
        return
    if level == "error":
        st.error(message)
        return
    if level == "warning":
        st.warning(message)
        return
    st.success(message)


def render_database_datasources_container():
    _show_feedback()

    toolbar_cols = st.columns([6, 2], gap="small", vertical_alignment="center")
    with toolbar_cols[1]:
        if st.button(
            "Add dataset",
            key="add_database_datasource_btn",
            icon=":material/add:",
            type="secondary",
            use_container_width=True,
        ):
            add_database_datasource_dialog()

    connections = load_database_connections(force=False)
    datasources = load_database_datasources(force=False)
    ensure_selected_database_datasource_id(datasources if isinstance(datasources, list) else [])
    render_database_datasources_component(
        datasources if isinstance(datasources, list) else [],
        connections if isinstance(connections, list) else [],
    )
