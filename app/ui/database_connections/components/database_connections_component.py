import streamlit as st

from database_connections.components.dialogs import (
    add_database_connection_dialog,
    delete_database_connection_dialog,
    edit_database_connection_dialog,
)


def render_database_connections_component(connections: list[dict]):
    if not connections:
        st.info("Nessuna connessione database configurata.")

    for idx, connection_item in enumerate(connections):
        connection_id = str(connection_item.get("id") or "")
        connection_label = (
            connection_item.get("description")
            or connection_id
            or "-"
        )
        with st.container(border=True):
            row_cols = st.columns([1, 7, 1, 1], gap="small", vertical_alignment="center")
            with row_cols[0]:
                st.markdown(f"[ {connection_item.get('payload', {}).get('database_type', '').upper()} ]")
                
            with row_cols[1]:
                st.markdown(f"{connection_label}")

            with row_cols[2]:
                if st.button(
                    "",
                    key=f"edit_database_connection_btn_{connection_id or idx}",
                    icon=":material/settings:",
                    help="Edit connection",
                    use_container_width=True,
                ):
                    edit_database_connection_dialog(connection_item)
            with row_cols[3]:
                if st.button(
                    "",
                    key=f"delete_database_connection_btn_{connection_id or idx}",
                    icon=":material/delete:",
                    help="Delete connection",
                    use_container_width=True,
                ):
                    delete_database_connection_dialog(connection_item)

    action_cols = st.columns([10, 1], gap="small", vertical_alignment="bottom")
    with action_cols[1]:
        if st.button(
            "",
            key="add_database_connection_btn",
            icon=":material/add:",
            help="Add database connection",
            use_container_width=True,
        ):
            add_database_connection_dialog()
