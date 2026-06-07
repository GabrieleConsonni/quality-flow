import json

import streamlit as st
import streamlit.components.v1 as components

from api_client import api_delete, api_get, api_post, api_put
from brokers.components.common import BROKER_TYPE_OPTIONS, pick_broker_type_label
from brokers.services.data_loader_service import load_brokers, load_queues


@st.dialog("Aggiungi broker")
def add_broker_dialog():
    description = st.text_input("Description", key="add_broker_description")
    broker_type_label = st.selectbox(
        "Type",
        options=list(BROKER_TYPE_OPTIONS.keys()),
        key="add_broker_type",
    )
    endpoint_url = st.text_input("Endpoint url", key="add_broker_endpoint")
    region = None
    secrets_access_key = None
    access_key_id = None
    if broker_type_label == "Amazon":
        region = st.text_input("Region", key="add_broker_region")
        secrets_access_key = st.text_input(
            "Secrets access key",
            type="password",
            key="add_broker_secret",
        )
        access_key_id = st.text_input("Access key id", key="add_broker_access")

    if not st.button("Salva", key="add_broker_save"):
        return

    errors = []
    if not description:
        errors.append("Il campo Description e' obbligatorio.")
    if not endpoint_url:
        errors.append("Il campo Endpoint url e' obbligatorio.")
    if broker_type_label == "Amazon":
        if not region:
            errors.append("Il campo Region e' obbligatorio per Amazon.")
        if not secrets_access_key:
            errors.append("Il campo Secrets access key e' obbligatorio per Amazon.")
        if not access_key_id:
            errors.append("Il campo Access key id e' obbligatorio per Amazon.")

    if errors:
        st.error(" ".join(errors))
        return

    payload = {
        "sourceType": BROKER_TYPE_OPTIONS[broker_type_label],
        "endpointUrl": endpoint_url,
    }
    if broker_type_label == "Amazon":
        payload.update(
            {
                "region": region,
                "secretsAccessKey": secrets_access_key,
                "accessKeyId": access_key_id,
            }
        )

    try:
        response = api_post(
            "/broker/connection",
            {
                "description": description,
                "payload": payload,
            },
        )
    except Exception:
        st.error("Errore salvataggio broker")
        return

    load_brokers(force=True)
    new_id = response.get("id")
    if new_id:
        st.session_state["selected_broker_id"] = new_id
    st.rerun()


@st.dialog("Modifica broker")
def edit_broker_dialog(broker_item: dict):
    broker_id = broker_item.get("id", "")
    payload = broker_item.get("payload") or {}
    description = st.text_input(
        "Description",
        value=broker_item.get("description", ""),
        key=f"edit_description_{broker_id}",
    )
    broker_type_label = st.selectbox(
        "Type",
        options=list(BROKER_TYPE_OPTIONS.keys()),
        index=list(BROKER_TYPE_OPTIONS.keys()).index(pick_broker_type_label(payload.get("sourceType"))),
        key=f"edit_type_{broker_id}",
    )
    endpoint_url = st.text_input(
        "Endpoint url",
        value=payload.get("endpointUrl", ""),
        key=f"edit_endpoint_{broker_id}",
    )
    region = None
    secrets_access_key = None
    access_key_id = None
    if broker_type_label == "Amazon":
        region = st.text_input(
            "Region",
            value=payload.get("region", ""),
            key=f"edit_region_{broker_id}",
        )
        secrets_access_key = st.text_input(
            "Secrets access key",
            type="password",
            value=payload.get("secretsAccessKey", ""),
            key=f"edit_secret_{broker_id}",
        )
        access_key_id = st.text_input(
            "Access key id",
            value=payload.get("accessKeyId", ""),
            key=f"edit_access_{broker_id}",
        )

    if not st.button("Salva modifiche", key=f"edit_save_{broker_id}"):
        return

    errors = []
    if not description:
        errors.append("Il campo Description e' obbligatorio.")
    if not endpoint_url:
        errors.append("Il campo Endpoint url e' obbligatorio.")
    if broker_type_label == "Amazon":
        if not region:
            errors.append("Il campo Region e' obbligatorio per Amazon.")
        if not secrets_access_key:
            errors.append("Il campo Secrets access key e' obbligatorio per Amazon.")
        if not access_key_id:
            errors.append("Il campo Access key id e' obbligatorio per Amazon.")

    if errors:
        st.error(" ".join(errors))
        return

    payload = {
        "sourceType": BROKER_TYPE_OPTIONS[broker_type_label],
        "endpointUrl": endpoint_url,
    }
    if broker_type_label == "Amazon":
        payload.update(
            {
                "region": region,
                "secretsAccessKey": secrets_access_key,
                "accessKeyId": access_key_id,
            }
        )

    try:
        api_put(
            "/broker/connection",
            {
                "id": broker_id,
                "description": description,
                "payload": payload,
            },
        )
    except Exception:
        st.error("Errore aggiornamento broker")
        return

    load_brokers(force=True)
    st.session_state["selected_broker_id"] = broker_id
    st.rerun()


@st.dialog("Conferma eliminazione")
def delete_broker_dialog(broker_item: dict):
    broker_id = broker_item.get("id", "")
    broker_description = broker_item.get("description", "No name")
    st.write(f"Eliminare il broker '{broker_description}'?")
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Conferma", key=f"delete_confirm_{broker_id}"):
            try:
                api_delete(f"/broker/connection/{broker_id}")
            except Exception:
                st.error("Errore cancellazione broker")
                return

            load_brokers(force=True)
            brokers_local = st.session_state.get("brokers", [])
            if brokers_local:
                st.session_state["selected_broker_id"] = brokers_local[0].get("id")
            else:
                st.session_state["selected_broker_id"] = None
            st.rerun()
    with col_cancel:
        st.button("Annulla", key=f"delete_cancel_{broker_id}")


@st.dialog("Aggiungi queue")
def add_queue_dialog(broker_item: dict):
    broker_id = broker_item.get("id", "")
    broker_payload = broker_item.get("payload") or {}
    source_type = broker_payload.get("sourceType", "elasticmq")
    type_label = pick_broker_type_label(source_type)

    code = st.text_input("Code", key=f"add_queue_code_{broker_id}")
    description = st.text_input("Description", key=f"add_queue_description_{broker_id}")
    st.text_input("Type", value=type_label, disabled=True, key=f"add_queue_type_{broker_id}")
    default_visibility = st.number_input(
        "Default visibility timeout (sec)",
        min_value=0,
        value=30,
        key=f"add_queue_visibility_{broker_id}",
    )
    receive_wait = st.number_input(
        "Receive message wait (sec)",
        min_value=0,
        value=0,
        key=f"add_queue_wait_{broker_id}",
    )

    fifo_queue = False
    content_based = False
    delay = 0
    if source_type == "elasticmq":
        fifo_queue = st.checkbox("FIFO queue", value=False, key=f"add_queue_fifo_{broker_id}")
        content_based = st.checkbox(
            "Content based deduplication",
            value=False,
            key=f"add_queue_dedupe_{broker_id}",
        )
        delay = st.number_input(
            "Delay (sec)",
            min_value=0,
            value=0,
            key=f"add_queue_delay_{broker_id}",
        )

    if not st.button("Salva", key=f"add_queue_save_{broker_id}"):
        return

    errors = []
    if not code:
        errors.append("Il campo Code e' obbligatorio.")
    if errors:
        st.error(" ".join(errors))
        return

    queue_config = {
        "sourceType": source_type,
        "defaultVisibilityTimeout": int(default_visibility),
        "receiveMessageWait": int(receive_wait),
    }
    if source_type == "elasticmq":
        queue_config.update(
            {
                "fifoQueue": fifo_queue,
                "contentBasedDeduplication": content_based,
                "delay": int(delay),
            }
        )

    try:
        api_post(
            f"/broker/{broker_id}/queue",
            {
                "code": code,
                "description": description,
                "queueConfiguration": queue_config,
                "save_on_db": True,
            },
        )
    except Exception:
        st.error("Errore salvataggio queue")
        return

    load_queues(broker_id)
    st.rerun()


@st.dialog("Impostazioni queue")
def queue_settings_dialog(broker_id: str, queue_id: str):
    try:
        queue = api_get(f"/broker/{broker_id}/queue/{queue_id}")
    except Exception:
        st.error("Errore caricamento queue")
        return

    config = queue.get("configurationQueue") or {}
    source_type = config.get("sourceType", "elasticmq")
    type_label = pick_broker_type_label(source_type)

    st.text_input("Code", value=queue.get("code", ""), disabled=True, key=f"settings_code_{queue_id}")
    st.text_input(
        "Description",
        value=queue.get("description", ""),
        disabled=True,
        key=f"settings_description_{queue_id}",
    )
    st.text_input("Type", value=type_label, disabled=True, key=f"settings_type_{queue_id}")
    st.text_input(
        "URL",
        value=config.get("url", ""),
        disabled=True,
        key=f"settings_url_{queue_id}",
    )
    st.text_input(
        "Default visibility timeout (sec)",
        value=str(config.get("defaultVisibilityTimeout", "")),
        disabled=True,
        key=f"settings_visibility_{queue_id}",
    )
    st.text_input(
        "Receive message wait (sec)",
        value=str(config.get("receiveMessageWait", "")),
        disabled=True,
        key=f"settings_wait_{queue_id}",
    )
    if source_type == "elasticmq":
        st.text_input(
            "FIFO queue",
            value=str(config.get("fifoQueue", False)),
            disabled=True,
            key=f"settings_fifo_{queue_id}",
        )
        st.text_input(
            "Content based deduplication",
            value=str(config.get("contentBasedDeduplication", False)),
            disabled=True,
            key=f"settings_dedupe_{queue_id}",
        )
        st.text_input(
            "Delay (sec)",
            value=str(config.get("delay", 0)),
            disabled=True,
            key=f"settings_delay_{queue_id}",
        )


@st.dialog("Modifica queue")
def queue_actions_dialog(broker_id: str, queue_item: dict):
    queue_id = str(queue_item.get("id") or "").strip()
    if not queue_id:
        st.error("Queue non valida.")
        return

    dialog_suffix = f"queue_actions_{queue_id}"
    queue_cfg = queue_item.get("configurationQueue") or {}
    queue_url = str(queue_cfg.get("url") or "").strip()
    queue_url_formatted = queue_url.replace("localhost", "[hostname]")
    st.text_input(
        "Code",
        key=f"{dialog_suffix}_code",
        value=str(queue_item.get("code") or ""),
    )
    st.text_input(
        "Description",
        key=f"{dialog_suffix}_description",
        value=str(queue_item.get("description") or ""),
    )

    if queue_url:
        st.warning(
            "Copy-paste URL in your application, replacing [hostname] with the actual hostname or IP address of the server running this application.",
            icon=":material/warning:",
        )
        st.text_input(
                "URL",
                key=f"{dialog_suffix}_url",
                value=queue_url_formatted,
                disabled=True,
            )

    st.divider()
    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"{dialog_suffix}_save",
            icon=":material/save:",
            use_container_width=True,
        ):
            code = str(st.session_state.get(f"{dialog_suffix}_code") or "").strip()
            description = str(st.session_state.get(f"{dialog_suffix}_description") or "")
            if not code:
                st.error("Il campo Code e' obbligatorio.")
                return
            try:
                api_put(
                    f"/broker/{broker_id}/queue/{queue_id}",
                    {
                        "code": code,
                        "description": description,
                    },
                )
            except Exception as exc:
                st.error(f"Errore aggiornamento queue: {str(exc)}")
                return

            load_queues(broker_id)
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Delete",
            key=f"{dialog_suffix}_delete",
            icon=":material/delete:",
            use_container_width=True,
        ):
            try:
                api_delete(f"/broker/{broker_id}/queue/{queue_id}")
            except Exception as exc:
                st.error(f"Errore cancellazione queue: {str(exc)}")
                return

            load_queues(broker_id)
            st.rerun()


@st.dialog("Conferma eliminazione queue")
def delete_queue_dialog(broker_id: str, queue_item: dict):
    queue_id = queue_item.get("id", "")
    queue_label = queue_item.get("description") or queue_item.get("code") or queue_id
    st.write(f"Eliminare la queue '{queue_label}'?")
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Conferma", key=f"delete_queue_confirm_{queue_id}"):
            try:
                api_delete(f"/broker/{broker_id}/queue/{queue_id}")
            except Exception:
                st.error("Errore cancellazione queue")
                return

            load_queues(broker_id)
            st.rerun()
    with col_cancel:
        st.button("Annulla", key=f"delete_queue_cancel_{queue_id}")
