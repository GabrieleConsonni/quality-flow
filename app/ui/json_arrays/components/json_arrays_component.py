import csv
import io
import json

import streamlit as st

from api_client import api_post, api_put
from json_arrays.components.dialogs import (
    delete_json_array_dialog,
)
from json_arrays.services.data_loader_service import load_json_arrays


SELECTED_JSON_ARRAY_ID_KEY = "selected_json_array_id"
INLINE_EDIT_MODE_KEY = "inline_edit_json_array_mode"
INLINE_EDIT_JSON_ARRAY_ID_KEY = "inline_edit_json_array_id"
INLINE_EDIT_JSON_ARRAY_BODY_KEY = "inline_edit_json_array_body"
INLINE_EDIT_JSON_ARRAY_BODY_PENDING_KEY = "inline_edit_json_array_body_pending"
INLINE_EDIT_JSON_ARRAY_DESCRIPTION_KEY = "inline_edit_json_array_description"


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


def _decode_csv_bytes(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Encoding CSV non supportato.")


def _parse_csv_rows(raw: bytes) -> list[dict]:
    csv_text = _decode_csv_bytes(raw)
    if not csv_text.strip():
        return []

    sample = csv_text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(csv_text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("Header CSV non trovato.")

    rows: list[dict] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        cleaned_row = {
            str(key).strip(): (value if value is not None else "")
            for key, value in row.items()
            if key is not None and str(key).strip()
        }
        if any(str(value).strip() for value in cleaned_row.values()):
            rows.append(cleaned_row)
    return rows


@st.dialog("Import from CSV")
def import_csv_dialog():
    uploaded_file = st.file_uploader(
        "CSV file",
        type=["csv"],
        key="json_array_import_csv_file",
    )
    if not uploaded_file:
        return

    if not st.button(
        "Import",
        key="json_array_import_csv_confirm",
        icon=":material/upload_file:",
        use_container_width=True,
    ):
        return

    try:
        parsed_rows = _parse_csv_rows(uploaded_file.getvalue())
    except Exception as exc:
        st.error(f"Errore parsing CSV: {str(exc)}")
        return

    _queue_inline_body_update(_pretty_json(parsed_rows))
    st.rerun()


def _stop_inline_edit():
    st.session_state.pop(INLINE_EDIT_MODE_KEY, None)
    st.session_state.pop(INLINE_EDIT_JSON_ARRAY_ID_KEY, None)
    st.session_state.pop(INLINE_EDIT_JSON_ARRAY_BODY_KEY, None)
    st.session_state.pop(INLINE_EDIT_JSON_ARRAY_BODY_PENDING_KEY, None)
    st.session_state.pop(INLINE_EDIT_JSON_ARRAY_DESCRIPTION_KEY, None)


def _queue_inline_body_update(next_body: str):
    st.session_state[INLINE_EDIT_JSON_ARRAY_BODY_PENDING_KEY] = next_body


def _apply_pending_inline_body_update():
    next_body = st.session_state.pop(INLINE_EDIT_JSON_ARRAY_BODY_PENDING_KEY, None)
    if next_body is not None:
        st.session_state[INLINE_EDIT_JSON_ARRAY_BODY_KEY] = str(next_body)


def _start_inline_edit(selected_item: dict):
    selected_id = selected_item.get("id")
    if not selected_id:
        return
    st.session_state[INLINE_EDIT_MODE_KEY] = "edit"
    st.session_state[INLINE_EDIT_JSON_ARRAY_ID_KEY] = str(selected_id)
    st.session_state[INLINE_EDIT_JSON_ARRAY_BODY_KEY] = _pretty_json(
        selected_item.get("payload") or []
    )


def _start_inline_create():
    st.session_state[INLINE_EDIT_MODE_KEY] = "create"
    st.session_state[INLINE_EDIT_JSON_ARRAY_ID_KEY] = ""
    st.session_state[INLINE_EDIT_JSON_ARRAY_DESCRIPTION_KEY] = ""
    st.session_state[INLINE_EDIT_JSON_ARRAY_BODY_KEY] = "[]"


def _save_inline_edit(selected_item: dict):
    json_array_id = selected_item.get("id")
    description = selected_item.get("description") or ""
    if not json_array_id:
        st.error("Id json-array non valido.")
        return

    payload, error = _parse_json_array(
        st.session_state.get(INLINE_EDIT_JSON_ARRAY_BODY_KEY, "[]")
    )
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

    load_json_arrays(force=True)
    _stop_inline_edit()
    st.rerun()


def _save_inline_create():
    description = str(st.session_state.get(INLINE_EDIT_JSON_ARRAY_DESCRIPTION_KEY, "")).strip()
    if not description:
        st.error("Il campo Description e' obbligatorio.")
        return

    payload, error = _parse_json_array(
        st.session_state.get(INLINE_EDIT_JSON_ARRAY_BODY_KEY, "[]")
    )
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

    load_json_arrays(force=True)
    _stop_inline_edit()
    new_id = response.get("id") if isinstance(response, dict) else None
    if new_id:
        st.session_state[SELECTED_JSON_ARRAY_ID_KEY] = str(new_id)
    st.rerun()


def _resolve_selected_json_array_id(json_arrays: list[dict]) -> str | None:
    ids = [str(item.get("id")) for item in json_arrays if item.get("id")]
    current = st.session_state.get(SELECTED_JSON_ARRAY_ID_KEY)
    if not ids:
        st.session_state.pop(SELECTED_JSON_ARRAY_ID_KEY, None)
        return None
    if not current or str(current) not in ids:
        st.session_state[SELECTED_JSON_ARRAY_ID_KEY] = ids[0]
    return str(st.session_state.get(SELECTED_JSON_ARRAY_ID_KEY))


def _find_selected_json_array(json_arrays: list[dict], selected_id: str | None) -> dict | None:
    if not selected_id:
        return None
    return next(
        (
            item
            for item in json_arrays
            if isinstance(item, dict) and str(item.get("id")) == str(selected_id)
        ),
        None,
    )


def render_json_arrays_component(json_arrays: list[dict]):
    _apply_pending_inline_body_update()
    selected_id = _resolve_selected_json_array_id(json_arrays)
    selected_item = _find_selected_json_array(json_arrays, selected_id)
    if not selected_item and st.session_state.get(INLINE_EDIT_MODE_KEY) != "create":
        _stop_inline_edit()
    inline_mode = st.session_state.get(INLINE_EDIT_MODE_KEY)
    editing_selected_item = (
        inline_mode == "edit"
        and str(st.session_state.get(INLINE_EDIT_JSON_ARRAY_ID_KEY)) == str(selected_id)
    )
    creating_new_item = inline_mode == "create"
    editing_or_creating = creating_new_item or editing_selected_item
    show_import_button = creating_new_item

    list_col, preview_col = st.columns([2, 5], gap="medium", vertical_alignment="top")
    with list_col:
        with st.container(border=True):
            if not json_arrays:
                st.info("Nessun json-array configurato.")
            else:
                for idx, json_array_item in enumerate(json_arrays):
                    json_array_id = json_array_item.get("id")
                    code = json_array_item.get("code") or "-"
                    description = json_array_item.get("description") or code
                    is_selected = str(json_array_id) == str(selected_id)

                    row_cols = st.columns([10,1], gap="small", vertical_alignment="center")
                    with row_cols[0]:
                        if st.button(
                            description,
                            key=f"select_json_array_btn_{json_array_id or idx}",
                            type="primary" if is_selected else "secondary",
                            use_container_width=True,
                            help="Select json-array"
                        ):
                            st.session_state[SELECTED_JSON_ARRAY_ID_KEY] = str(json_array_id)
                            if (
                                st.session_state.get(INLINE_EDIT_JSON_ARRAY_ID_KEY)
                                and str(st.session_state.get(INLINE_EDIT_JSON_ARRAY_ID_KEY))
                                != str(json_array_id)
                            ) or creating_new_item:
                                _stop_inline_edit()
                                st.rerun()

                    with row_cols[1]:
                        if st.button(
                            "",
                            key=f"delete_json_array_btn_{json_array_id or idx}",
                            type="tertiary",
                            help="Delete json-array",
                            icon=":material/delete:",
                        ):
                            delete_json_array_dialog(json_array_item)  

        if st.button(
            "Add new json-array",
            key="add_json_array_btn",
            help="Add json-array",
            icon=":material/add:",
            use_container_width=True,
            type="tertiary"
        ):
            _start_inline_create()
            st.rerun()

    with preview_col:
        
        with st.container(border=True):
            if creating_new_item:
               st.text_input(
                   "Description",
                   key=INLINE_EDIT_JSON_ARRAY_DESCRIPTION_KEY,
               )
               st.text_area(
                   "Body",
                   key=INLINE_EDIT_JSON_ARRAY_BODY_KEY,
                   height=420,
               )
            elif not selected_item:
               st.info("Seleziona un json-array dalla lista a sinistra.")
            else:
               st.subheader(selected_item.get("description") or "-")
               if editing_selected_item:
                   st.text_area(
                       "Body",
                       key=INLINE_EDIT_JSON_ARRAY_BODY_KEY,
                       height=420,
                   )
               else:
                   st.json(selected_item.get("payload") or [], expanded=True)

        tool_cols = st.columns([3, 2, 1, 1], gap="small", vertical_alignment="bottom")
        with tool_cols[1]:
            if show_import_button and st.button(
                "Import CSV",
                key="json_array_import_from_csv",
                icon=":material/upload_file:",
                type="secondary",
                use_container_width=True,
            ):
                import_csv_dialog()
        with tool_cols[2]:
            if editing_or_creating and st.button(
                "Beautify",
                key=(
                    f"json_array_inline_beautify_{selected_id}"
                    if editing_selected_item
                    else "json_array_inline_beautify_create"
                ),
                icon=":material/auto_fix_high:",
                type="secondary",
                use_container_width=True,
            ):
                payload, error = _parse_json_array(
                    st.session_state.get(INLINE_EDIT_JSON_ARRAY_BODY_KEY, "[]")
                )
                if error:
                    st.error(error)
                else:
                    _queue_inline_body_update(_pretty_json(payload))
                    st.rerun()
        with tool_cols[3]:
            edit_btn_label = "Save" if editing_or_creating else ""
            edit_btn_icon = (
                ":material/save:" if editing_or_creating else ":material/edit:"
            )
            if st.button(
                edit_btn_label,
                key="edit_selected_json_array_btn",
                icon=edit_btn_icon,
                type="secondary",
                use_container_width=True,
                help=(
                    "Save json-array"
                    if editing_or_creating
                    else "Edit selected json-array"
                ),
                disabled=not bool(selected_item) and not creating_new_item,
            ):
                if creating_new_item:
                    _save_inline_create()
                elif editing_selected_item:
                    _save_inline_edit(selected_item or {})
                else:
                    _start_inline_edit(selected_item or {})
                    st.rerun()

