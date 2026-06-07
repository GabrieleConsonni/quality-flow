import streamlit as st

from brokers.components.common import format_count, format_last_update
from brokers.components.dialogs import (
    add_queue_dialog,
    queue_actions_dialog,
)
from brokers.services.data_loader_service import load_queues


def _open_queue_page(broker_id: str | None, queue_id: str | None):
    if not broker_id or not queue_id:
        st.error("Impossibile aprire il dettaglio della queue.")
        return
    st.session_state["selected_broker_id"] = broker_id
    st.session_state["nav_broker_id"] = broker_id
    st.session_state["nav_queue_id"] = queue_id
    st.switch_page("pages/QueueDetails.py")


def render_queues_component(broker: dict):
    if not broker:
        st.info("Nessun broker configurato.")
        return None

    

    broker_id = broker.get("id")
    load_queues(broker_id)
    queues = st.session_state.get("queues", [])

    if not queues:
        st.info("No queues configured for this broker.")
    else:
        for queue_item in queues:
            with st.container(border=True):
                row_cols = st.columns([2, 2, 2, 1, 1], gap="small", vertical_alignment="center")
                queue_label = queue_item.get("description") or queue_item.get("code") or "-"
                row_cols[0].write(queue_label)
                with row_cols[1]:
                    st.write("Approximante number of messages: " + format_count(queue_item.get("messages_sent")))
                with row_cols[2]:
                    st.write("Not visible messages: " + format_count(queue_item.get("messages_received")))
                with row_cols[3]:
                    if st.button(
                        "",
                        key=f"queue_open_{queue_item.get('id')}",
                        type="secondary",
                        use_container_width=True,
                        help="Open queue page",
                        icon=":material/clear_all:",
                    ):
                        _open_queue_page(broker_id, queue_item.get("id"))
                with row_cols[4]:
                    if st.button(
                        "",
                        key=f"queue_more_actions_{queue_item.get('id')}",
                        type="secondary",
                        use_container_width=True,
                        help="Edit queue",
                        icon=":material/more_vert:",
                    ):
                        queue_actions_dialog(broker_id, queue_item)

    loaded_at = st.session_state.get("queues_loaded_at")
    timestamp_label = format_last_update(loaded_at) if loaded_at else "-"
    footer_cols = st.columns([5, 2, 1, 1], gap="small", vertical_alignment="bottom")
    with footer_cols[0]:
        st.caption(f"Updated at: {timestamp_label}")
    with footer_cols[2]:
        st.button(
            "",
            key="refresh_queues_btn",
            on_click=lambda: load_queues(broker_id),
            use_container_width=True,
            icon=":material/refresh:",
        )
    with footer_cols[3]:
        if st.button(
            "",
            key="add_queue_btn",
            use_container_width=True,
            disabled=not bool(broker_id),
            icon=":material/add:",
        ):
            add_queue_dialog(broker)

