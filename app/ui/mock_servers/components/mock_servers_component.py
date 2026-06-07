import streamlit as st

from mock_servers.services.data_loader_service import MOCK_SERVERS_KEY, load_mock_servers
from mock_servers.services.mock_server_api_service import (
    activate_mock_server,
    create_mock_server,
    deactivate_mock_server,
    delete_mock_server,
    update_mock_server,
)
from mock_servers.services.state_keys import SELECTED_MOCK_SERVER_ID_KEY


def _normalize_endpoint(raw_value: object) -> str:
    return str(raw_value or "").strip().strip("/")


def _serialize_operation(operation: dict) -> dict:
    configuration_json = (
        operation.get("configuration_json")
        if isinstance(operation.get("configuration_json"), dict)
        else {}
    )
    return {
        "order": int(operation.get("order") or 0),
        "description": str(operation.get("description") or ""),
        "cfg": configuration_json,
    }


def _serialize_api(api_entry: dict) -> dict:
    configuration_json = (
        api_entry.get("configuration_json")
        if isinstance(api_entry.get("configuration_json"), dict)
        else {}
    )
    method = str(
        configuration_json.get("method")
        or api_entry.get("method")
        or "GET"
    ).strip().upper()
    path = str(
        configuration_json.get("path")
        or api_entry.get("path")
        or "/"
    ).strip()
    if not path.startswith("/"):
        path = f"/{path}"
    cfg = {**configuration_json, "method": method, "path": path}
    return {
        "order": int(api_entry.get("order") or 0),
        "description": str(api_entry.get("description") or ""),
        "cfg": cfg,
        "commands": [
            _serialize_operation(item)
            for item in (api_entry.get("commands") or api_entry.get("operations") or [])
            if isinstance(item, dict)
        ],
    }


def _serialize_queue(queue_entry: dict) -> dict:
    configuration_json = (
        queue_entry.get("configuration_json")
        if isinstance(queue_entry.get("configuration_json"), dict)
        else {}
    )
    return {
        "order": int(queue_entry.get("order") or 0),
        "description": str(queue_entry.get("description") or ""),
        "queue_id": str(queue_entry.get("queue_id") or "").strip(),
        "cfg": configuration_json,
        "commands": [
            _serialize_operation(item)
            for item in (queue_entry.get("commands") or queue_entry.get("operations") or [])
            if isinstance(item, dict)
        ],
    }


def _build_update_payload(
    server_item: dict,
    *,
    description: str,
    endpoint: str,
) -> tuple[dict | None, str | None]:
    server_id = str(server_item.get("id") or "").strip()
    normalized_endpoint = _normalize_endpoint(endpoint)
    if not server_id:
        return None, "Mock server non valido."
    if not normalized_endpoint:
        return None, "Il campo Endpoint e' obbligatorio."
    if not str(description or "").strip():
        return None, "Il campo Description e' obbligatorio."
    server_cfg = (
        server_item.get("configuration_json")
        if isinstance(server_item.get("configuration_json"), dict)
        else {}
    )

    payload = {
        "id": server_id,
        "description": description,
        "cfg": {
            "endpoint": normalized_endpoint,
            "authorization": server_cfg.get("authorization") if isinstance(server_cfg.get("authorization"), dict) else {},
        },
        "apis": [
            _serialize_api(item)
            for item in (server_item.get("apis") or [])
            if isinstance(item, dict)
        ],
        "queues": [
            _serialize_queue(item)
            for item in (server_item.get("queues") or [])
            if isinstance(item, dict)
        ],
        "is_active": bool(server_item.get("is_active")),
    }
    return payload, None


@st.dialog("Add mock server", width="medium")
def add_mock_server_dialog():
    dialog_suffix = "mock_server_create"
    st.text_input("Description", key=f"{dialog_suffix}_description")
    st.text_input(
        "Endpoint",
        key=f"{dialog_suffix}_endpoint",
        help="Runtime route: /mock/{endpoint}/...",
    )
    if st.button(
        "Save",
        key="mock_server_create_save_btn",
        icon=":material/save:",
        use_container_width=True,
    ):
        description = str(st.session_state.get(f"{dialog_suffix}_description") or "")
        endpoint = _normalize_endpoint(st.session_state.get(f"{dialog_suffix}_endpoint"))
        if not description.strip():
            st.error("Il campo Description e' obbligatorio.")
            return
        if not endpoint:
            st.error("Il campo Endpoint e' obbligatorio.")
            return
        payload = {
            "description": description,
            "cfg": {"endpoint": endpoint, "authorization": {}},
            "apis": [],
            "queues": [],
            "is_active": False,
        }
        try:
            create_mock_server(payload)
        except Exception as exc:
            st.error(f"Errore creazione mock server: {str(exc)}")
            return
        load_mock_servers(force=True)
        st.rerun()


@st.dialog("Mock server actions", width="medium")
def mock_server_actions_dialog(server_item: dict):
    server_id = str(server_item.get("id") or "")
    if not server_id:
        st.error("Mock server non valido.")
        return
    dialog_suffix = f"mock_server_actions_{server_id}"
    is_active = bool(server_item.get("is_active"))
    endpoint_value = str(server_item.get("endpoint") or "")
    st.caption(
        "Modifica disponibile solo se il server e' disattivato."
        if is_active
        else "Il server e' disattivato: puoi modificare descrizione e endpoint."
    )
    st.text_input(
        "Description",
        key=f"{dialog_suffix}_description",
        value=str(server_item.get("description") or ""),
        disabled=is_active,
    )
    st.text_input(
        "Endpoint",
        key=f"{dialog_suffix}_endpoint",
        value=endpoint_value,
        help="Runtime route: /mock/{endpoint}/...",
        disabled=is_active,
    )
    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"{dialog_suffix}_save",
            icon=":material/save:",
            use_container_width=True,
            disabled=is_active,
        ):
            payload, validation_error = _build_update_payload(
                server_item,
                description=str(st.session_state.get(f"{dialog_suffix}_description") or ""),
                endpoint=str(st.session_state.get(f"{dialog_suffix}_endpoint") or ""),
            )
            if validation_error:
                st.error(validation_error)
                return
            try:
                update_mock_server(payload or {})
            except Exception as exc:
                st.error(f"Errore aggiornamento mock server: {str(exc)}")
                return
            load_mock_servers(force=True)
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Delete",
            key=f"{dialog_suffix}_delete",
            icon=":material/delete:",
            use_container_width=True,
        ):
            try:
                delete_mock_server(server_id)
            except Exception as exc:
                st.error(f"Errore cancellazione mock server: {str(exc)}")
                return
            if str(st.session_state.get(SELECTED_MOCK_SERVER_ID_KEY) or "") == server_id:
                st.session_state.pop(SELECTED_MOCK_SERVER_ID_KEY, None)
            load_mock_servers(force=True)
            st.rerun()


def render_mock_servers_component():
    load_mock_servers(force=False)
    servers = st.session_state.get(MOCK_SERVERS_KEY, [])
    if not isinstance(servers, list):
        servers = []

    header_cols = st.columns([9, 1], gap="small", vertical_alignment="center")
    with header_cols[1]:
        if st.button(
            "",
            key="mock_server_add_btn",
            icon=":material/add:",
            help="Add mock server",
            use_container_width=True,
        ):
            add_mock_server_dialog()

    if not servers:
        st.info("Nessun mock server configurato.")
        return

    for idx, server_item in enumerate(servers):
        server_id = str(server_item.get("id") or "")
        endpoint = _normalize_endpoint(server_item.get("endpoint")) or "-"
        label = str(server_item.get("description") or server_id or "-")
        is_active = bool(server_item.get("is_active"))
        with st.container(border=True):
            row = st.columns([8, 1, 1, 1], gap="small", vertical_alignment="center")
            with row[0]:
                st.write(label)
                st.caption(f"/mock/{endpoint}")
            with row[1]:
                toggled_state = st.toggle(
                    "Active",
                    key=f"mock_server_active_{server_id or idx}",
                    value=is_active,
                    label_visibility="collapsed",
                    help="Activate/Deactivate",
                )
                if toggled_state != is_active:
                    try:
                        if toggled_state:
                            activate_mock_server(server_id)
                        else:
                            deactivate_mock_server(server_id)
                    except Exception as exc:
                        st.error(f"Errore aggiornamento stato mock server: {str(exc)}")
                    else:
                        load_mock_servers(force=True)
                        st.rerun()
            with row[2]:
                if st.button(
                    "",
                    key=f"mock_server_open_editor_{server_id or idx}",
                    icon=":material/settings:",
                    use_container_width=True,
                    help="Open editor",
                ):
                    if not server_id:
                        st.error("Mock server non valido.")
                    else:
                        st.session_state[SELECTED_MOCK_SERVER_ID_KEY] = server_id
                        st.switch_page("pages/MockServerEditor.py")
            with row[3]:
                if st.button(
                    "",
                    key=f"mock_server_more_actions_{server_id or idx}",
                    icon=":material/more_vert:",
                    use_container_width=True,
                    help="Actions",
                ):
                    mock_server_actions_dialog(server_item)
