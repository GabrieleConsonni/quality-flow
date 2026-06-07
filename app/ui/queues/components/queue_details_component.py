import streamlit as st
import json

from brokers.components.common import format_count
from queues.services.queue_service import (
    load_json_arrays,
    receive_queue_messages,
    save_json_array,
    send_queue_messages,
    test_queue_connection,
    receive_queue_messages_ack
)


def _send_body_key(queue_id: str) -> str:
    return f"queue_send_body_{queue_id}"


def _send_results_key(queue_id: str) -> str:
    return f"queue_send_results_{queue_id}"


def _send_write_dialog_open_key(queue_id: str) -> str:
    return f"queue_send_write_open_{queue_id}"


def _send_write_body_key(queue_id: str) -> str:
    return f"queue_send_write_body_{queue_id}"


def _receive_messages_key(queue_id: str) -> str:
    return f"queue_receive_messages_data_{queue_id}"


def _receive_messages_acked_key(queue_id: str) -> str:
    return f"queue_receive_messages_acked_{queue_id}"


def _apply_tab_label_style():
    st.markdown(
        """
        <style>
        button[data-baseweb="tab"] p {
            font-size: 1.05rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _parse_json_array(body_text: str) -> tuple[list[object] | None, str | None]:
    try:
        parsed = json.loads(body_text)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {str(exc)}"
    if not isinstance(parsed, list):
        return None, "Body must contain a JSON array."
    return parsed, None


def _pretty_json(value: object) -> str:
    return json.dumps(value, indent=2)


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _is_fifo_content_dedup_enabled(queue_cfg: dict) -> bool:
    return _as_bool(queue_cfg.get("fifoQueue")) and _as_bool(
        queue_cfg.get("contentBasedDeduplication")
    )


def _extract_json_array_from_messages(messages: list[object]) -> tuple[list[object] | None, str | None]:
    extracted: list[object] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            return None, f"Invalid message at index {index + 1}."
        body_value = message.get("Body")
        if body_value is None:
            return None, f"Message {index + 1} is missing the Body field."
        if isinstance(body_value, str):
            try:
                body_value = json.loads(body_value)
            except json.JSONDecodeError as exc:
                return None, f"Invalid Body in message {index + 1}: {str(exc)}"
        extracted.append(body_value)
    return extracted, None


def _open_write_json_array_dialog(queue_id: str):
    st.session_state[_send_write_body_key(queue_id)] = st.session_state.get(_send_body_key(queue_id), "[]")
    st.session_state[_send_write_dialog_open_key(queue_id)] = True


@st.dialog("Test connection")
def queue_test_connection_dialog(broker_id: str, queue_id: str):
    try:
        with st.spinner("Testing connection..."):
            result = test_queue_connection(broker_id, queue_id)
    except Exception as exc:
        st.error(f"Connection test error: {str(exc)}")
        return

    message = str(result.get("message", "Test completed."))
    if "not valid" in message.lower():
        st.error(message)
    else:
        st.success(message)
    st.json(result)


@st.dialog("Select datasource",width="large")
def open_select_json_array_dialog(queue_id: str):
    try:
        json_arrays = load_json_arrays()
    except Exception as exc:
        st.error(f"Error loading json-array: {str(exc)}")
        return

    if not json_arrays:
        st.info("No json-array available.")
        return

    options = list(range(len(json_arrays)))
    selected_idx = st.selectbox(
        "Json arrays",
        options=options,
        format_func=lambda idx: json_arrays[idx].get("description") or "-",
        key=f"queue_send_datasource_{queue_id}",
    )
    selected_item = json_arrays[selected_idx]
    st.json(selected_item.get("payload") or [], expanded=False)

    if st.button("Use datasource", key=f"use_queue_send_datasource_{queue_id}"):
        st.session_state[_send_body_key(queue_id)] = _pretty_json(selected_item.get("payload") or [])
        st.rerun()


@st.dialog("Write json-array", width="large")
def queue_write_json_array_dialog(queue_id: str):
    write_body_key = _send_write_body_key(queue_id)
    if write_body_key not in st.session_state:
        st.session_state[write_body_key] = st.session_state.get(_send_body_key(queue_id), "[]")
    action_cols = st.columns([1, 1], gap="small")
    with action_cols[0]:
        if st.button(
            "Beautify",
            key=f"queue_write_beautify_{queue_id}",
            icon=":material/auto_fix_high:",
            use_container_width=True,
        ):
            payload, error = _parse_json_array(st.session_state.get(write_body_key, "[]"))
            if error:
                st.error(error)
            else:
                st.session_state[write_body_key] = _pretty_json(payload)

    st.text_area(
        "Body",
        key=write_body_key,
        height=360,
    )

    with action_cols[1]:
        if st.button(
            "OK",
            key=f"queue_write_ok_{queue_id}",
            icon=":material/check:",
            use_container_width=True,
        ):
            st.session_state[_send_body_key(queue_id)] = st.session_state.get(write_body_key, "[]")
            st.session_state[_send_write_dialog_open_key(queue_id)] = False
            st.rerun()


@st.dialog("Save json-array")
def open_save_json_array_dialog(queue_id: str):
    body = st.session_state.get(_send_body_key(queue_id), "[]")
    payload, error = _parse_json_array(body)
    if error:
        st.error(error)
        return

    description = st.text_input("Description", key=f"queue_save_array_description_{queue_id}")
    st.caption("Preview")
    st.json(payload, expanded=False)

    if not st.button("Save", key=f"queue_save_array_submit_{queue_id}"):
        return
    if not description.strip():
        st.error("The Description field is required.")
        return

    try:
        save_json_array(description=description, payload=payload or [])
    except Exception as exc:
        st.error(f"Error saving json-array: {str(exc)}")
        return

    st.success("Json-array saved successfully.")
    st.rerun()


@st.dialog("Extract json-array", width="large")
def queue_extract_json_array_dialog(queue_id: str):
    received_messages = st.session_state.get(_receive_messages_key(queue_id), [])
    extracted_payload, error = _extract_json_array_from_messages(received_messages)
    if error:
        st.error(error)
        return

    description = st.text_input("Description", key=f"queue_extract_array_description_{queue_id}")
    st.caption("Preview")
    st.json(extracted_payload or [], expanded=False)

    if not st.button("Save", key=f"queue_extract_array_submit_{queue_id}"):
        return
    if not description.strip():
        st.error("The Description field is required.")
        return

    try:
        save_json_array(description=description, payload=extracted_payload or [])
    except Exception as exc:
        st.error(f"Error saving json-array: {str(exc)}")
        return

    st.success("Json-array saved successfully.")
    st.rerun()


@st.dialog("Results", width="large")
def queue_send_results_dialog(queue_id: str):
    results_key = _send_results_key(queue_id)
    results = st.session_state.get(results_key, [])
    if results:
        st.dataframe(results, use_container_width=True, hide_index=True)
    else:
        st.caption("No results available.")


@st.dialog("Receive messages")
def queue_receive_results_dialog(messages_count: int):
    st.success("Messages received successfully.")
    st.write(f"Messages read: **{messages_count}**")

@st.dialog("Ack messages")
def queue_ack_received_messages_dialog(messages_count: int):
    st.success("Messages confirmed successfully.")
    st.write(f"Messages confirmed: **{messages_count}**")


@st.dialog("Receive and ack messages")
def queue_receive_and_ack_messages_dialog(received_count: int, acked_count: int):
    st.success("Messages received and confirmed successfully.")
    st.write(f"Messages read: **{received_count}**")
    st.write(f"Messages confirmed: **{acked_count}**")


def render_queue_details_component(queue_data: dict, broker_id: str, queue_id: str):
    
    queue_label = queue_data.get("description") or queue_data.get("code") or queue_id
    queue_cfg = queue_data.get("configurationQueue") or {}
    st.header(f"Queue [{queue_label}]")
    st.caption("Send and receive messages, test connection and manage json-array datasources.")

    with st.container(border=True):
        col_sent, col_received, col_empty, col_refresh, col_test = st.columns(
            [3, 3, 1, 1, 2], gap="small", vertical_alignment="center"
        )
        with col_sent:
            st.metric("Approximate number of messages", format_count(queue_data.get("messages_sent")))
        with col_received:
            st.metric("Not visible messages", format_count(queue_data.get("messages_received"))) 
        with col_refresh:
            if st.button(
                "Refresh",
                key=f"queue_refresh_metrics_{queue_id}",
                icon=":material/refresh:",
                use_container_width=True,
            ):
                st.rerun()
        with col_test:
            if st.button("Test connection",
                         key=f"queue_test_connection_{queue_id}", 
                         icon=":material/network_check:",
                         use_container_width=True):
                queue_test_connection_dialog(broker_id, queue_id)

    with st.container(border=True):
        _apply_tab_label_style()

        tab_send, tab_receive = st.tabs(
            [":material/send: Send", ":material/check: Receive"]
        )
        with tab_send:
            body_key = _send_body_key(queue_id)
            results_key = _send_results_key(queue_id)
            write_open_key = _send_write_dialog_open_key(queue_id)
            if body_key not in st.session_state:
                st.session_state[body_key] = "[]"
            if results_key not in st.session_state:
                st.session_state[results_key] = []
            if write_open_key not in st.session_state:
                st.session_state[write_open_key] = False

            if st.session_state.get(write_open_key):
                queue_write_json_array_dialog(queue_id)

            if _is_fifo_content_dedup_enabled(queue_cfg):
                st.warning(
                    "FIFO + content-based deduplication are enabled: if you resend the same message "
                    "within the deduplication window, the broker can ignore it even after ACK."
                )

            col_buttons, col_preview, col_send = st.columns([1, 4, 1], gap="small",vertical_alignment="top")
        
            with col_buttons:
                st.caption("Create or import json-array")
                body_text = st.session_state.get(body_key, "[]")
                payload, error = _parse_json_array(body_text)
                body_has_value = body_text.strip() not in ("", "[]")
                if st.button(
                    "",
                    key=f"queue_send_edit_body_{queue_id}",
                    icon=":material/edit:" if body_has_value else ":material/add:",
                    help="Edit json-array" if body_has_value else "Create json-array",
                    use_container_width=True,
                ):
                    _open_write_json_array_dialog(queue_id)
                    st.rerun()
                
                if st.button(
                    "",
                    key=f"queue_send_select_datasource_{queue_id}",
                    icon=":material/download:",
                    use_container_width=True,
                    help="Select json-array from datasource",
                ):
                    open_select_json_array_dialog(queue_id)

                if st.button(
                    "",
                    key=f"queue_send_save_array_{queue_id}",
                    icon=":material/save:",
                    use_container_width=True,
                    help="Save json-array to datasource",
                ):
                    open_save_json_array_dialog(queue_id)

            with col_preview:
                st.caption("Preview")
                if error:
                    st.error(error)
                else:
                    st.json(payload)

            with col_send:
                st.caption("Send messages")
                if st.button(
                    "",
                    key=f"queue_send_messages_{queue_id}",
                    icon=":material/send:",
                    use_container_width=True,
                    help="Send messages to queue",
                ):
                    payload, error = _parse_json_array(st.session_state.get(body_key, "[]"))
                    if error:
                        st.error(error)
                    else:
                        st.session_state[results_key] = []
                        try:
                            with st.spinner("Sending messages..."):
                                results = send_queue_messages(broker_id, queue_id, payload or [])
                        except Exception as exc:
                            st.error(f"Error sending messages: {str(exc)}")
                        else:
                            st.session_state[results_key] = results if isinstance(results, list) else [results]
                            st.session_state[body_key] = "[]"
                            st.rerun()
                if st.button(
                        "",
                        key=f"queue_view_results_{queue_id}",
                        icon=":material/search_check:",
                        use_container_width=True,
                        help="View send results",
                    ):
                    queue_send_results_dialog(queue_id)
                send_body_has_value = st.session_state.get(body_key, "[]").strip() not in ("", "[]")
                if st.button(
                    "",
                    key=f"queue_send_clean_preview_{queue_id}",
                    icon=":material/delete_sweep:",
                    help="Clean preview",
                    disabled=not send_body_has_value,
                    use_container_width=True,
                ):
                    st.session_state[body_key] = "[]"
                    st.rerun()
        

        with tab_receive:
            received_messages_key = _receive_messages_key(queue_id)
            received_messages_acked_key = _receive_messages_acked_key(queue_id)
            if received_messages_key not in st.session_state:
                st.session_state[received_messages_key] = []
            if received_messages_acked_key not in st.session_state:
                st.session_state[received_messages_acked_key] = False

            receive_cols = st.columns([1, 4, 1], gap="small", vertical_alignment="top")
            with receive_cols[0]:
                st.caption("Receive messages")
                if st.button(
                    "",
                    key=f"queue_receive_messages_{queue_id}",
                    icon=":material/mark_as_unread:",
                    help="Receive messages from queue",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("Receiving messages..."):
                            received = receive_queue_messages(broker_id, queue_id, count=10)
                    except Exception as exc:
                        st.error(f"Error receiving messages: {str(exc)}")
                    else:
                        st.session_state[received_messages_key] = (
                            received if isinstance(received, list) else [received]
                        )
                        st.session_state[received_messages_acked_key] = False
                        st.rerun()
                if st.button(
                    "",
                    key=f"queue_receive_ack_messages_{queue_id}",
                    icon=":material/done_all:",
                    help="Receive and ack messages",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("Receiving and acknowledging messages..."):
                            received = receive_queue_messages(broker_id, queue_id, count=10)
                            received_items = received if isinstance(received, list) else [received]
                            if not received_items:
                                st.session_state[received_messages_key] = []
                                st.session_state[received_messages_acked_key] = False
                                st.info("No messages available.")
                                return
                            ack_results = receive_queue_messages_ack(
                                broker_id,
                                queue_id,
                                received_items,
                            )
                    except Exception as exc:
                        st.error(f"Error while receiving and acknowledging messages: {str(exc)}")
                    else:
                        acked_items = ack_results if isinstance(ack_results, list) else []
                        received_count = len(received_items)
                        acked_count = len(acked_items)
                        if acked_count != received_count:
                            st.session_state[received_messages_key] = received_items
                            st.session_state[received_messages_acked_key] = False
                            st.error(
                                f"Partial ACK: received {received_count}, acknowledged {acked_count}."
                            )
                            return
                        st.session_state[received_messages_key] = received_items
                        st.session_state[received_messages_acked_key] = True
                        queue_receive_and_ack_messages_dialog(received_count, acked_count)
                        st.rerun()

            with receive_cols[1]:
                st.caption("Preview")
                st.json(st.session_state.get(received_messages_key, []))

            with receive_cols[2]:
                st.caption("Actions")
                has_messages = bool(st.session_state.get(received_messages_key))
                messages_already_acked = bool(st.session_state.get(received_messages_acked_key))
                
                if st.button(
                    "",
                    key=f"queue_ack_{queue_id}",
                    icon=":material/check:",
                    help="Ack received messages",
                    disabled=(not has_messages) or messages_already_acked,
                    use_container_width=True,
                ):
                    messages_to_ack = st.session_state.get(received_messages_key, [])
                    try:
                        with st.spinner("Acknowledging messages..."):
                            ack_results = receive_queue_messages_ack(broker_id, queue_id, messages_to_ack)
                    except Exception as exc:
                        st.error(f"Error acknowledging messages: {str(exc)}")
                    else:
                        acked_items = ack_results if isinstance(ack_results, list) else []
                        acked_count = len(acked_items)
                        requested_count = len(messages_to_ack)
                        if acked_count != requested_count:
                            st.error(
                                f"Partial ACK: requested {requested_count}, acknowledged {acked_count}."
                            )
                            return
                        st.session_state[_receive_messages_key(queue_id)] = []
                        st.session_state[received_messages_acked_key] = False
                        queue_ack_received_messages_dialog(acked_count)
                        st.rerun()
                
                if st.button(
                    "",
                    key=f"queue_extract_array_{queue_id}",
                    icon=":material/output:",
                    help="Extract json-array",
                    disabled=not has_messages,
                    use_container_width=True,
                ):
                    queue_extract_json_array_dialog(queue_id)
                
                if st.button(
                    "",
                    key=f"queue_receive_clean_{queue_id}",
                    icon=":material/delete_sweep:",
                    help="Clean preview",
                    disabled=not has_messages,
                    use_container_width=True,
                ):
                    st.session_state[received_messages_key] = []
                    st.session_state[received_messages_acked_key] = False
                    st.rerun()

