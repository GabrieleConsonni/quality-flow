import streamlit as st

from brokers.components.dialogs import (
    add_broker_dialog,
    delete_broker_dialog,
    edit_broker_dialog,
)


def _open_queues_page(broker_id: str | None):
    if not broker_id:
        st.error("Impossibile aprire la lista queue.")
        return
    st.session_state["selected_broker_id"] = broker_id
    st.session_state["queues_filter_broker_id"] = broker_id
    st.session_state["nav_broker_id"] = broker_id
    st.switch_page("pages/Queues.py")


def render_brokers_component(brokers: list[dict]):
    for idx, broker_item in enumerate(brokers):
        broker_id = broker_item.get("id")
        broker_description = broker_item.get("description", "No name")
        with st.container(border=True):
            row_cols = st.columns([1,6, 1, 1, 1], gap="small", vertical_alignment="center")

            with row_cols[0]:
                st.markdown(f"[ {broker_item.get('payload', {}).get('sourceType', '').upper()} ]")
                
            with row_cols[1]:
                st.markdown(f" {broker_description}")

            with row_cols[2]:
                if st.button(
                    "",
                    key=f"open_queues_btn_{idx}",
                    type="secondary",
                    use_container_width=True,
                    help="Open queues",
                    icon=":material/list_alt:",
                ):
                    _open_queues_page(broker_id)
            with row_cols[3]:
                if st.button(
                    "",
                    key=f"edit_broker_btn_{idx}",
                    type="secondary",
                    use_container_width=True,
                    help="Edit broker",
                    icon=":material/settings:",
                ):
                    edit_broker_dialog(broker_item)
            with row_cols[4]:
                if st.button(
                    "",
                    key=f"delete_broker_btn_{idx}",
                    type="secondary",
                    use_container_width=True,
                    help="Delete broker",
                    icon=":material/delete:",
                ):
                    delete_broker_dialog(broker_item)

    action_cols = st.columns([10, 1], gap="small", vertical_alignment="bottom")
    with action_cols[1]:
        if st.button(
            "",
            key="add_broker_btn",
            help="Add broker connection",
            use_container_width=True,
            icon=":material/add:",
        ):
            add_broker_dialog()

