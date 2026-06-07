import json

import streamlit as st

from api_client import api_delete, api_post, api_put
from json_arrays.services.data_loader_service import load_json_arrays

SELECTED_JSON_ARRAY_ID_KEY = "selected_json_array_id"


def _parse_json_array(body_text: str) -> tuple[list[object] | None, str | None]:
    try:
        parsed = json.loads(body_text)
    except json.JSONDecodeError as exc:
        return None, f"JSON non valido: {str(exc)}"
    if not isinstance(parsed, list):
        return None, "Il body deve contenere un array JSON."
    return parsed, None


def _pretty_json(value: object) -> str:
    return json.dumps(value, indent=2)


@st.dialog("Aggiungi json-array", width="large")
def add_json_array_dialog():
    description = st.text_input("Description", key="add_json_array_description")
    body_key = "add_json_array_body"
    if body_key not in st.session_state:
        st.session_state[body_key] = "[]"

    if st.button(
        "Beautify",
        key="add_json_array_beautify",
        icon=":material/auto_fix_high:",
    ):
        payload, error = _parse_json_array(st.session_state.get(body_key, "[]"))
        if error:
            st.error(error)
        else:
            st.session_state[body_key] = _pretty_json(payload)

    st.text_area("Body", key=body_key, height=320)

    if not st.button(
        "Save",
        key="add_json_array_save",
        icon=":material/save:",
        use_container_width=True,
    ):
        return

    if not description.strip():
        st.error("Il campo Description e' obbligatorio.")
        return

    payload, error = _parse_json_array(st.session_state.get(body_key, "[]"))
    if error:
        st.error(error)
        return

    try:
        response = api_post(
            "/data-source/json-array",
            {
                "description": description,
                "payload": payload or [],
            },
        )
    except Exception as exc:
        st.error(f"Errore salvataggio json-array: {str(exc)}")
        return

    new_id = response.get("id") if isinstance(response, dict) else None
    if new_id:
        st.session_state[SELECTED_JSON_ARRAY_ID_KEY] = str(new_id)
    load_json_arrays(force=True)
    st.rerun()


@st.dialog("Modifica json-array", width="large")
def edit_json_array_dialog(json_array_item: dict):
    json_array_id = json_array_item.get("id", "")
    description = st.text_input(
        "Description",
        value=json_array_item.get("description", ""),
        key=f"edit_json_array_description_{json_array_id}",
    )
    body_key = f"edit_json_array_body_{json_array_id}"
    if body_key not in st.session_state:
        st.session_state[body_key] = _pretty_json(json_array_item.get("payload") or [])

    if st.button(
        "Beautify",
        key=f"edit_json_array_beautify_{json_array_id}",
        icon=":material/auto_fix_high:",
    ):
        payload, error = _parse_json_array(st.session_state.get(body_key, "[]"))
        if error:
            st.error(error)
        else:
            st.session_state[body_key] = _pretty_json(payload)

    st.text_area("Body", key=body_key, height=320)

    if not st.button(
        "Save changes",
        key=f"edit_json_array_save_{json_array_id}",
        icon=":material/save:",
        use_container_width=True,
    ):
        return

    if not json_array_id:
        st.error("Id json-array non valido.")
        return
    if not description.strip():
        st.error("Il campo Description e' obbligatorio.")
        return

    payload, error = _parse_json_array(st.session_state.get(body_key, "[]"))
    if error:
        st.error(error)
        return

    try:
        api_put(
            "/data-source/json-array",
            {
                "id": json_array_id,
                "description": description,
                "payload": payload or [],
            },
        )
    except Exception as exc:
        st.error(f"Errore aggiornamento json-array: {str(exc)}")
        return

    st.session_state[SELECTED_JSON_ARRAY_ID_KEY] = str(json_array_id)
    load_json_arrays(force=True)
    st.rerun()


@st.dialog("Conferma eliminazione")
def delete_json_array_dialog(json_array_item: dict):
    json_array_id = json_array_item.get("id", "")
    json_array_label = (
        json_array_item.get("description")
        or json_array_id
        or "-"
    )
    st.write(f"Eliminare il json-array '{json_array_label}'?")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Conferma", key=f"delete_json_array_confirm_{json_array_id}"):
            if not json_array_id:
                st.error("Id json-array non valido.")
                return
            try:
                api_delete(f"/data-source/json-array/{json_array_id}")
            except Exception as exc:
                st.error(f"Errore cancellazione json-array: {str(exc)}")
                return

            if str(st.session_state.get(SELECTED_JSON_ARRAY_ID_KEY)) == str(json_array_id):
                st.session_state.pop(SELECTED_JSON_ARRAY_ID_KEY, None)
            load_json_arrays(force=True)
            st.rerun()
    with col_cancel:
        st.button("Annulla", key=f"delete_json_array_cancel_{json_array_id}")
