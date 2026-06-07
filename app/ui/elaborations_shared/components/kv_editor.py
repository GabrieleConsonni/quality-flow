"""Shared key-value editor helpers for Streamlit UIs.

Provides row-based KV editors that store state in ``st.session_state``
and render add/delete/edit controls.
"""

import json
from uuid import uuid4

import streamlit as st


def new_ui_key() -> str:
    return uuid4().hex[:10]


def _parse_json_literal(
    raw_value: str,
    *,
    field_label: str,
    row_idx: int,
) -> tuple[object | None, str | None]:
    raw_text = str(raw_value or "").strip()
    if not raw_text:
        return None, f"{field_label}: valore obbligatorio alla riga {row_idx}."
    try:
        return json.loads(raw_text), None
    except json.JSONDecodeError as exc:
        return (
            None,
            (
                f"{field_label}: valore JSON non valido alla riga {row_idx} "
                f"({str(exc)})."
            ),
        )


def _json_literal_to_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=True)


def dict_to_rows(source: dict) -> list[dict]:
    if not isinstance(source, dict):
        return []
    rows: list[dict] = []
    for key, value in source.items():
        rows.append(
            {
                "row_id": new_ui_key(),
                "key": str(key),
                "value_text": _json_literal_to_text(value),
            }
        )
    return rows


def ensure_kv_editor_state(editor_state_key: str, source: dict):
    if editor_state_key not in st.session_state or not isinstance(
        st.session_state.get(editor_state_key),
        list,
    ):
        st.session_state[editor_state_key] = dict_to_rows(source)


def render_kv_rows_container(
    *,
    editor_state_key: str,
    key_prefix: str,
    use_container: bool = True,
):
    rows = st.session_state.get(editor_state_key)
    if not isinstance(rows, list):
        rows = []
        st.session_state[editor_state_key] = rows

    body_container = st.container(border=True) if use_container else st.container()
    with body_container:
        st.caption(
            'Inserire JSON literal (es: `"abc"`, 1, true, null, {"a":1}, [1,2]).'
        )
        if not rows:
            st.caption("Nessun elemento configurato.")

        for idx, row in enumerate(rows):
            row_id = str(row.get("row_id") or new_ui_key())
            row["row_id"] = row_id
            key_input_key = f"{key_prefix}_key_{row_id}"
            value_input_key = f"{key_prefix}_value_{row_id}"
            if key_input_key not in st.session_state:
                st.session_state[key_input_key] = str(row.get("key") or "")
            if value_input_key not in st.session_state:
                st.session_state[value_input_key] = str(row.get("value_text") or "")

            row_cols = st.columns([3, 5, 1], gap="small", vertical_alignment="center")
            with row_cols[0]:
                st.text_input(
                    "Key",
                    key=key_input_key,
                    label_visibility="collapsed",
                    placeholder=f"key_{idx + 1}",
                )
            with row_cols[1]:
                st.text_input(
                    "Value",
                    key=value_input_key,
                    label_visibility="collapsed",
                    placeholder='es: "abc", 1, true, null, {"a":1}, [1,2]',
                )
            with row_cols[2]:
                if st.button(
                    "",
                    key=f"{key_prefix}_delete_{row_id}",
                    icon=":material/delete:",
                    help="Delete row",
                    use_container_width=True,
                ):
                    rows.pop(idx)
                    st.session_state[editor_state_key] = rows
                    st.rerun()

            row["key"] = str(st.session_state.get(key_input_key) or "")
            row["value_text"] = str(st.session_state.get(value_input_key) or "")

        add_cols = st.columns([8, 1], gap="small", vertical_alignment="center")
        with add_cols[1]:
            if st.button(
                "",
                key=f"{key_prefix}_add",
                icon=":material/add:",
                help="Add row",
                use_container_width=True,
            ):
                rows.append(
                    {
                        "row_id": new_ui_key(),
                        "key": "",
                        "value_text": "",
                    }
                )
                st.session_state[editor_state_key] = rows
                st.rerun()

    return rows


def rows_to_dict(rows: list[dict], field_label: str) -> tuple[dict | None, str | None]:
    if not isinstance(rows, list) or not rows:
        return {}, None

    result: dict = {}
    seen_keys: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        key = str((row or {}).get("key") or "").strip()
        if not key:
            return None, f"{field_label}: chiave obbligatoria alla riga {idx}."
        if key in seen_keys:
            return None, f"{field_label}: chiave duplicata '{key}' alla riga {idx}."

        value, parse_error = _parse_json_literal(
            str((row or {}).get("value_text") or ""),
            field_label=field_label,
            row_idx=idx,
        )
        if parse_error:
            return None, parse_error

        seen_keys.add(key)
        result[key] = value

    return result, None
