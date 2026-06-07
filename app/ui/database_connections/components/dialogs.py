import streamlit as st

from api_client import api_delete, api_post, api_put
from database_connections.components.common import (
    DATABASE_TYPE_OPTIONS,
    DEFAULT_PORT_BY_TYPE,
    pick_database_type_label,
)
from database_connections.services.data_loader_service import load_database_connections

SELECTED_DATABASE_CONNECTION_ID_KEY = "selected_database_connection_id"
TEST_CONNECTION_ICON = ":material/network_check:"


def _validate_connection_fields(
    description: str,
    host: str,
    port: int,
    database: str,
    db_schema: str,
    user: str,
    password: str,
) -> str | None:
    errors = []
    if not description:
        errors.append("Il campo Description e' obbligatorio.")
    if not host:
        errors.append("Il campo Host e' obbligatorio.")
    if port <= 0:
        errors.append("Il campo Port deve essere maggiore di zero.")
    if not database:
        errors.append("Il campo Database/Service e' obbligatorio.")
    if not db_schema:
        errors.append("Il campo Schema e' obbligatorio.")
    if not user:
        errors.append("Il campo User e' obbligatorio.")
    if not password:
        errors.append("Il campo Password e' obbligatorio.")
    return " ".join(errors) if errors else None


def _validate_connection_test_fields(
    host: str,
    port: int,
    database: str,
    db_schema: str,
    user: str,
    password: str,
) -> str | None:
    errors = []
    if not host:
        errors.append("Il campo Host e' obbligatorio per il test.")
    if port <= 0:
        errors.append("Il campo Port deve essere maggiore di zero.")
    if not database:
        errors.append("Il campo Database/Service e' obbligatorio per il test.")
    if not db_schema:
        errors.append("Il campo Schema e' obbligatorio per il test.")
    if not user:
        errors.append("Il campo User e' obbligatorio per il test.")
    if not password:
        errors.append("Il campo Password e' obbligatorio per il test.")
    return " ".join(errors) if errors else None


def _build_connection_payload(values: dict) -> dict:
    return {
        "database_type": values["database_type"],
        "host": values["host"].strip(),
        "port": values["port"],
        "database": values["database"].strip(),
        "db_schema": values["db_schema"].strip(),
        "user": values["user"].strip(),
        "password": values["password"],
    }


def _render_test_feedback(feedback: dict | None):
    if not isinstance(feedback, dict):
        return
    status = str(feedback.get("status") or "")
    message = str(feedback.get("message") or "")
    if not message:
        return
    if status == "success":
        st.success(message)
    elif status == "error":
        st.error(message)
    else:
        st.info(message)


def _render_connection_form(prefix: str, payload: dict | None = None) -> tuple[dict, str]:
    payload = payload or {}

    type_key = f"{prefix}_database_type"
    port_key = f"{prefix}_port"
    port_type_key = f"{prefix}_port_database_type"

    selected_type_label = st.selectbox(
        "Type",
        options=list(DATABASE_TYPE_OPTIONS.keys()),
        index=list(DATABASE_TYPE_OPTIONS.keys()).index(
            pick_database_type_label(payload.get("database_type"))
        ),
        key=type_key,
    )
    selected_type = DATABASE_TYPE_OPTIONS[selected_type_label]

    if (
        port_type_key not in st.session_state
        or st.session_state.get(port_type_key) != selected_type
    ):
        st.session_state[port_key] = int(
            payload.get("port") or DEFAULT_PORT_BY_TYPE.get(selected_type, 5432)
        )
        st.session_state[port_type_key] = selected_type

    st.divider()
    left_col, right_col = st.columns(2, gap="medium")

    with left_col:
        description = st.text_input("Description", key=f"{prefix}_description")
        host = st.text_input("Host", key=f"{prefix}_host")
        database = st.text_input(
            "Database / Service",
            key=f"{prefix}_database",
        )
        user = st.text_input("User", key=f"{prefix}_user")

    with right_col:
        port = int(
            st.number_input(
                "Port",
                min_value=1,
                key=port_key,
            )
        )
        db_schema = st.text_input("Schema", key=f"{prefix}_db_schema")
        password = st.text_input("Password", type="password", key=f"{prefix}_password")

    form_values = {
        "description": description,
        "database_type": selected_type,
        "host": host,
        "port": port,
        "database": database,
        "db_schema": db_schema,
        "user": user,
        "password": password,
    }
    return form_values, selected_type_label


@st.dialog("Aggiungi connessione database")
def add_database_connection_dialog():
    default_payload = {
        "database_type": "",
        "port": "",
        "host": "",
        "database": "",
        "db_schema": "public",
        "user": "",
        "password": "",
    }
    for field_name in ("description", "host", "database", "db_schema", "user", "password"):
        st.session_state.setdefault(f"add_db_conn_{field_name}", "")
        
    feedback_key = "add_db_conn_test_feedback"
    st.session_state.setdefault(feedback_key, None)

    values, _ = _render_connection_form("add_db_conn", payload=default_payload)

    action_cols = st.columns(2, gap="small")
    with action_cols[0]:
        if st.button(
            "Test connection",
            key="add_db_conn_test_btn",
            icon=TEST_CONNECTION_ICON,
            type="secondary",
            use_container_width=True,
        ):
            test_error = _validate_connection_test_fields(
                values["host"].strip(),
                values["port"],
                values["database"].strip(),
                values["db_schema"].strip(),
                values["user"].strip(),
                values["password"],
            )
            if test_error:
                st.session_state[feedback_key] = {
                    "status": "error",
                    "message": test_error,
                }
            else:
                try:
                    result = api_post(
                        "/database/connection/test",
                        {
                            "description": "test-connection",
                            "payload": _build_connection_payload(values),
                        },
                    )
                    message = (
                        result.get("message")
                        if isinstance(result, dict)
                        else "Test completato."
                    )
                    st.session_state[feedback_key] = {
                        "status": "success",
                        "message": message,
                    }
                except Exception as exc:
                    st.session_state[feedback_key] = {
                        "status": "error",
                        "message": f"Errore test connessione database: {str(exc)}",
                    }

    with action_cols[1]:
        if st.button(
            "Save",
            key="add_db_conn_save_btn",
            icon=":material/save:",
            use_container_width=True,
        ):
            validation_error = _validate_connection_fields(
                values["description"].strip(),
                values["host"].strip(),
                values["port"],
                values["database"].strip(),
                values["db_schema"].strip(),
                values["user"].strip(),
                values["password"],
            )
            if validation_error:
                st.error(validation_error)
                return

            try:
                response = api_post(
                    "/database/connection",
                    {
                        "description": values["description"],
                        "payload": _build_connection_payload(values),
                    },
                )
            except Exception as exc:
                st.error(f"Errore salvataggio connessione database: {str(exc)}")
                return

            st.session_state.pop(feedback_key, None)
            load_database_connections(force=True)
            new_id = response.get("id") if isinstance(response, dict) else None
            if new_id:
                st.session_state[SELECTED_DATABASE_CONNECTION_ID_KEY] = str(new_id)
            st.rerun()

    _render_test_feedback(st.session_state.get(feedback_key))


@st.dialog("Modifica connessione database")
def edit_database_connection_dialog(connection_item: dict):
    connection_id = str(connection_item.get("id") or "")
    payload = connection_item.get("payload") or {}

    defaults = {
        "description": str(connection_item.get("description") or ""),
        "host": str(payload.get("host") or ""),
        "database": str(payload.get("database") or ""),
        "db_schema": str(payload.get("db_schema") or ""),
        "user": str(payload.get("user") or ""),
        "password": str(payload.get("password") or ""),
    }
    for field_name, default_value in defaults.items():
        st.session_state.setdefault(f"edit_db_conn_{connection_id}_{field_name}", default_value)
    st.session_state.setdefault(
        f"edit_db_conn_{connection_id}_database_type",
        pick_database_type_label(payload.get("database_type")),
    )
    feedback_key = f"edit_db_conn_test_feedback_{connection_id}"
    st.session_state.setdefault(feedback_key, None)

    values, _ = _render_connection_form(
        f"edit_db_conn_{connection_id}",
        payload=payload,
    )

    action_cols = st.columns(2, gap="small")
    with action_cols[0]:
        if st.button(
            "Test connection",
            key=f"edit_db_conn_test_btn_{connection_id}",
            icon=TEST_CONNECTION_ICON,
            type="secondary",
            use_container_width=True,
        ):
            test_error = _validate_connection_test_fields(
                values["host"].strip(),
                values["port"],
                values["database"].strip(),
                values["db_schema"].strip(),
                values["user"].strip(),
                values["password"],
            )
            if test_error:
                st.session_state[feedback_key] = {
                    "status": "error",
                    "message": test_error,
                }
            else:
                try:
                    result = api_post(
                        "/database/connection/test",
                        {
                            "description": values["description"] or "test-connection",
                            "payload": _build_connection_payload(values),
                        },
                    )
                    message = (
                        result.get("message")
                        if isinstance(result, dict)
                        else "Test completato."
                    )
                    st.session_state[feedback_key] = {
                        "status": "success",
                        "message": message,
                    }
                except Exception as exc:
                    st.session_state[feedback_key] = {
                        "status": "error",
                        "message": f"Errore test connessione database: {str(exc)}",
                    }

    with action_cols[1]:
        if st.button(
            "Save changes",
            key=f"edit_db_conn_save_btn_{connection_id}",
            icon=":material/save:",
            use_container_width=True,
        ):
            validation_error = _validate_connection_fields(
                values["description"].strip(),
                values["host"].strip(),
                values["port"],
                values["database"].strip(),
                values["db_schema"].strip(),
                values["user"].strip(),
                values["password"],
            )
            if validation_error:
                st.error(validation_error)
                return

            try:
                api_put(
                    "/database/connection",
                    {
                        "id": connection_id,
                        "description": values["description"],
                        "payload": _build_connection_payload(values),
                    },
                )
            except Exception as exc:
                st.error(f"Errore aggiornamento connessione database: {str(exc)}")
                return

            st.session_state.pop(feedback_key, None)
            load_database_connections(force=True)
            st.session_state[SELECTED_DATABASE_CONNECTION_ID_KEY] = connection_id
            st.rerun()

    _render_test_feedback(st.session_state.get(feedback_key))


@st.dialog("Conferma eliminazione")
def delete_database_connection_dialog(connection_item: dict):
    connection_id = str(connection_item.get("id") or "")
    connection_label = (
        connection_item.get("description") or connection_id or "-"
    )
    st.write(f"Eliminare la connessione database '{connection_label}'?")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Conferma", key=f"delete_db_conn_confirm_{connection_id}"):
            try:
                api_delete(f"/database/connection/{connection_id}")
            except Exception as exc:
                st.error(f"Errore cancellazione connessione database: {str(exc)}")
                return

            load_database_connections(force=True)
            connections = st.session_state.get("database_connections", [])
            if connections:
                st.session_state[SELECTED_DATABASE_CONNECTION_ID_KEY] = str(
                    connections[0].get("id")
                )
            else:
                st.session_state.pop(SELECTED_DATABASE_CONNECTION_ID_KEY, None)
            st.rerun()
    with col_cancel:
        st.button("Annulla", key=f"delete_db_conn_cancel_{connection_id}")
