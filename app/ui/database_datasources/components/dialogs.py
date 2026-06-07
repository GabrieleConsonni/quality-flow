import streamlit as st

from database_datasources.services.api_service import (
    create_database_datasource,
    delete_database_datasource_by_id,
    update_database_datasource,
)
from database_datasources.services.data_loader_service import (
    invalidate_database_datasource_preview,
    load_database_connection_objects,
    load_database_connections,
    load_database_datasources,
)
from database_datasources.services.perimeter_service import (
    build_connection_label,
    build_dataset_payload,
)
from database_datasources.services.state_service import (
    clear_database_datasource_selection_if_matches,
    ensure_selected_database_datasource_id,
    mark_database_datasource_open,
    set_database_datasource_feedback,
    set_selected_database_datasource_id,
)


def _render_database_object_type_selector(
    key_prefix: str,
    current_object_type: str = "table",
) -> str:
    options = ["table", "view"]
    normalized = str(current_object_type or "table").strip().lower()
    index = options.index(normalized) if normalized in options else 0
    return st.selectbox(
        "Database object type",
        options=options,
        index=index,
        key=f"{key_prefix}_object_type_select",
    )


def _render_database_object_selector(
    objects_payload: dict,
    key_prefix: str,
    object_type: str,
    current_object_name: str = "",
) -> str:
    available_objects = (
        [str(item) for item in (objects_payload.get("tables") or []) if item]
        if str(object_type or "table").strip().lower() == "table"
        else [str(item) for item in (objects_payload.get("views") or []) if item]
    )
    options = [""] + available_objects
    index = options.index(current_object_name) if current_object_name in available_objects else 0
    return st.selectbox(
        "Database objects",
        options=options,
        index=index,
        key=f"{key_prefix}_object_name_select",
    )


def _render_connection_selector(
    key_prefix: str,
    connections: list[dict],
    current_connection_id: str = "",
) -> str:
    connection_ids = [str(item.get("id")) for item in connections if item.get("id")]
    if not connection_ids:
        st.info("Nessuna connessione database disponibile.")
        return ""

    index = 0
    if current_connection_id and current_connection_id in connection_ids:
        index = connection_ids.index(current_connection_id)

    return st.selectbox(
        "Connection",
        options=connection_ids,
        index=index,
        key=f"{key_prefix}_connection_select",
        format_func=lambda conn_id: build_connection_label(
            next(
                (item for item in connections if str(item.get("id")) == str(conn_id)),
                {},
            )
        ),
    )


def _refresh_datasource_state(selected_id: str | None = None):
    datasources = load_database_datasources(force=True)
    if selected_id:
        set_selected_database_datasource_id(selected_id)
        mark_database_datasource_open(selected_id, is_open=True)
        return
    ensure_selected_database_datasource_id(datasources if isinstance(datasources, list) else [])


@st.dialog("Aggiungi dataset", width="large")
def add_database_datasource_dialog():
    connections = load_database_connections(force=False)
    if not connections:
        st.info("Configura prima almeno una connessione database.")
        return

    description = st.text_input("Description", key="add_database_datasource_description")
    selected_connection_id = _render_connection_selector(
        "add_database_datasource",
        connections,
    )
    if not selected_connection_id:
        return

    objects_payload = load_database_connection_objects(selected_connection_id, force=False)
    selected_object_type = _render_database_object_type_selector(
        f"add_database_datasource_{selected_connection_id}",
        "table",
    )
    selected_object_name = _render_database_object_selector(
        objects_payload,
        key_prefix=f"add_database_datasource_{selected_connection_id}_{selected_object_type}",
        object_type=selected_object_type,
    )

    if not st.button(
        "Save",
        key="add_database_datasource_save",
        icon=":material/add:",
        use_container_width=True,
        disabled=not bool(str(selected_object_name or "").strip()),
    ):
        return

    if not description.strip():
        st.error("Il campo Description e' obbligatorio.")
        return
    if not selected_object_name or not selected_object_type:
        st.error("Seleziona un database object valido.")
        return

    try:
        response = create_database_datasource(
            {
                "description": description,
                "payload": build_dataset_payload(
                    selected_connection_id,
                    objects_payload.get("schema"),
                    selected_object_name,
                    selected_object_type,
                ),
            }
        )
    except Exception as exc:
        st.error(f"Errore salvataggio dataset: {str(exc)}")
        return

    invalidate_database_datasource_preview()
    created_id = str((response or {}).get("id") or "").strip()
    _refresh_datasource_state(created_id or None)
    set_database_datasource_feedback(response.get("message") or "Dataset creato.", level="success")
    st.rerun()


@st.dialog("Modifica dataset", width="large")
def edit_database_datasource_dialog(datasource_item: dict):
    datasource_id = str(datasource_item.get("id") or "").strip()
    payload = datasource_item.get("payload") if isinstance(datasource_item.get("payload"), dict) else {}
    current_connection_id = str(payload.get("connection_id") or "")
    current_object_name = str(payload.get("object_name") or "")
    current_object_type = str(payload.get("object_type") or "table")

    connections = load_database_connections(force=False)
    if not connections:
        st.info("Nessuna connessione database disponibile.")
        return

    description = st.text_input(
        "Description",
        value=str(datasource_item.get("description") or ""),
        key=f"edit_database_datasource_description_{datasource_id}",
    )

    selected_connection_id = _render_connection_selector(
        f"edit_database_datasource_{datasource_id}",
        connections,
        current_connection_id=current_connection_id,
    )
    if not selected_connection_id:
        return

    objects_payload = load_database_connection_objects(selected_connection_id, force=False)
    selected_object_type = _render_database_object_type_selector(
        f"edit_database_datasource_{datasource_id}_{selected_connection_id}",
        current_object_type=current_object_type,
    )
    selected_object_name = _render_database_object_selector(
        objects_payload,
        key_prefix=f"edit_database_datasource_{datasource_id}_{selected_connection_id}_{selected_object_type}",
        object_type=selected_object_type,
        current_object_name=current_object_name if selected_object_type == current_object_type else "",
    )

    if not st.button(
        "Save changes",
        key=f"edit_database_datasource_save_{datasource_id}",
        icon=":material/save:",
        use_container_width=True,
        disabled=not bool(str(selected_object_name or "").strip()),
    ):
        return

    if not datasource_id:
        st.error("Id datasource non valido.")
        return
    if not description.strip():
        st.error("Il campo Description e' obbligatorio.")
        return
    if not selected_object_name or not selected_object_type:
        st.error("Seleziona un database object valido.")
        return

    try:
        response = update_database_datasource(
            {
                "id": datasource_id,
                "description": description,
                "payload": build_dataset_payload(
                    selected_connection_id,
                    objects_payload.get("schema"),
                    selected_object_name,
                    selected_object_type,
                ),
            }
        )
    except Exception as exc:
        st.error(f"Errore aggiornamento dataset: {str(exc)}")
        return

    invalidate_database_datasource_preview(datasource_id)
    _refresh_datasource_state(datasource_id)
    set_database_datasource_feedback(response.get("message") or "Dataset aggiornato.", level="success")
    st.rerun()


@st.dialog("Delete dataset", width="medium")
def delete_database_datasource_dialog(datasource_item: dict):
    datasource_id = str(datasource_item.get("id") or "").strip()
    datasource_label = str(datasource_item.get("description") or datasource_id or "-").strip()

    st.caption(datasource_label)
    st.write("Delete this dataset?")

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Delete",
            key=f"delete_database_datasource_confirm_{datasource_id}",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            try:
                response = delete_database_datasource_by_id(datasource_id)
            except Exception as exc:
                st.error(f"Errore cancellazione dataset: {str(exc)}")
                return

            invalidate_database_datasource_preview(datasource_id)
            clear_database_datasource_selection_if_matches(datasource_id)
            datasources = load_database_datasources(force=True)
            ensure_selected_database_datasource_id(datasources if isinstance(datasources, list) else [])
            set_database_datasource_feedback(response.get("message") or "Dataset eliminato.", level="success")
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"delete_database_datasource_cancel_{datasource_id}",
            use_container_width=True,
        ):
            st.rerun()
