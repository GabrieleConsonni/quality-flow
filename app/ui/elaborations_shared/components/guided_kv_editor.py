"""Guided key-value editor for HTTP input nodes.

Each row has a key (text) and a guided value control (Literal/Runtime value/Source/Built-in).
Used for queryParams, headers, and pathParams in API commands.
"""

import json
from uuid import uuid4

import streamlit as st

from elaborations_shared.components.guided_value_control import (
    collect_guided_value,
    initialize_guided_value_state,
    render_guided_value_control,
    validate_guided_value_node,
)


def new_ui_key() -> str:
    return uuid4().hex[:10]


def guided_dict_to_rows(source: dict | None) -> list[dict]:
    if not isinstance(source, dict):
        return []
    rows: list[dict] = []
    for key, node in source.items():
        rows.append({
            "row_id": new_ui_key(),
            "key": str(key),
            "node": node if isinstance(node, dict) else {"kind": "literal", "value": node},
        })
    return rows


def ensure_guided_kv_state(editor_state_key: str, source: dict | None):
    if editor_state_key not in st.session_state or not isinstance(
        st.session_state.get(editor_state_key), list,
    ):
        st.session_state[editor_state_key] = guided_dict_to_rows(source)


def render_guided_kv_rows_container(
    *,
    editor_state_key: str,
    key_prefix: str,
    use_container: bool = True,
    available_constants: list[dict] | None = None,
    available_sources: list[dict] | None = None,
    allowed_modes: list[str] | None = None,
    show_runtime_field_path: bool = False,
):
    rows = st.session_state.get(editor_state_key)
    if not isinstance(rows, list):
        rows = []
        st.session_state[editor_state_key] = rows

    body_container = st.container(border=True) if use_container else st.container()
    with body_container:
        if not rows:
            st.caption("No items configured.")

        for idx, row in enumerate(rows):
            row_id = str(row.get("row_id") or new_ui_key())
            row["row_id"] = row_id
            key_input_key = f"{key_prefix}_key_{row_id}"
            value_prefix = f"{key_prefix}_val_{row_id}"

            if key_input_key not in st.session_state:
                st.session_state[key_input_key] = str(row.get("key") or "")

            node = row.get("node") or {"kind": "literal", "value": ""}
            initialize_guided_value_state(value_prefix, node)

            row_cols = st.columns([3, 8, 1], gap="small", vertical_alignment="top")
            with row_cols[0]:
                st.text_input(
                    "Key",
                    key=key_input_key,
                    label_visibility="collapsed",
                    placeholder=f"key_{idx + 1}",
                )
            with row_cols[1]:
                render_guided_value_control(
                    value_prefix,
                    available_constants=available_constants,
                    available_sources=available_sources,
                    allowed_modes=allowed_modes,
                    show_label=False,
                    placeholder='e.g. "abc", 1, true',
                    show_runtime_field_path=show_runtime_field_path,
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

        add_cols = st.columns([8, 1], gap="small", vertical_alignment="center")
        with add_cols[1]:
            if st.button(
                "",
                key=f"{key_prefix}_add",
                icon=":material/add:",
                help="Add row",
                use_container_width=True,
            ):
                rows.append({
                    "row_id": new_ui_key(),
                    "key": "",
                    "node": {"kind": "literal", "value": ""},
                })
                st.session_state[editor_state_key] = rows
                st.rerun()

    return rows


def collect_guided_kv_rows(
    rows: list[dict],
    key_prefix: str,
    field_label: str,
    *,
    allowed_modes: list[str] | None = None,
    scalar_only: bool = False,
) -> tuple[dict | None, str | None]:
    if not isinstance(rows, list) or not rows:
        return {}, None

    result: dict = {}
    seen_keys: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        row_id = str((row or {}).get("row_id") or "")
        key = str((row or {}).get("key") or "").strip()
        if not key:
            return None, f"{field_label}: key is required at row {idx}."
        if key in seen_keys:
            return None, f"{field_label}: duplicate key '{key}' at row {idx}."

        value_prefix = f"{key_prefix}_val_{row_id}"
        node, error = collect_guided_value(value_prefix)
        if error:
            return None, f"{field_label} row {idx}: {error}"
        node_error = validate_guided_value_node(
            node,
            allowed_modes=allowed_modes,
            scalar_only=scalar_only,
        )
        if node_error:
            return None, f"{field_label} row {idx}: {node_error}"

        seen_keys.add(key)
        result[key] = node

    return result, None
