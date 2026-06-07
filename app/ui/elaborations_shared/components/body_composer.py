"""Recursive body composer for HTTP request body.

Supports object, array, and value nodes. Value nodes use guided value controls.
Used in writeApi command editor Body tab.
"""

import json
from uuid import uuid4

import streamlit as st

from elaborations_shared.components.guided_value_control import (
    collect_guided_value,
    initialize_guided_value_state,
    render_guided_value_control,
)


BODY_NODE_OBJECT = "object"
BODY_NODE_ARRAY = "array"
BODY_NODE_VALUE = "value"

BODY_NODE_OPTIONS = [BODY_NODE_VALUE, BODY_NODE_OBJECT, BODY_NODE_ARRAY]

BODY_NODE_LABELS = {
    BODY_NODE_OBJECT: "Object",
    BODY_NODE_ARRAY: "Array",
    BODY_NODE_VALUE: "Value",
}


def new_ui_key() -> str:
    return uuid4().hex[:10]


def _body_key(prefix: str, field: str) -> str:
    return f"{prefix}_bc_{field}"


def body_payload_to_tree(payload: object) -> dict:
    if payload is None:
        return {"type": BODY_NODE_VALUE, "node": {"kind": "literal", "value": ""}, "ui_key": new_ui_key()}
    if isinstance(payload, dict):
        kind = str(payload.get("kind") or "").strip()
        if kind in {"literal", "runtimeValue", "source", "builtIn"}:
            return {"type": BODY_NODE_VALUE, "node": payload, "ui_key": new_ui_key()}
        entries = []
        for key, value in payload.items():
            entries.append({
                "key": str(key),
                "child": body_payload_to_tree(value),
                "ui_key": new_ui_key(),
            })
        return {"type": BODY_NODE_OBJECT, "entries": entries, "ui_key": new_ui_key()}
    if isinstance(payload, list):
        items = [{"child": body_payload_to_tree(item), "ui_key": new_ui_key()} for item in payload]
        return {"type": BODY_NODE_ARRAY, "items": items, "ui_key": new_ui_key()}
    return {"type": BODY_NODE_VALUE, "node": {"kind": "literal", "value": payload}, "ui_key": new_ui_key()}


def tree_to_payload(tree: dict) -> object:
    node_type = str(tree.get("type") or BODY_NODE_VALUE).strip()
    if node_type == BODY_NODE_OBJECT:
        result = {}
        for entry in tree.get("entries") or []:
            key = str(entry.get("key") or "").strip()
            if key:
                result[key] = tree_to_payload(entry.get("child") or {})
        return result
    if node_type == BODY_NODE_ARRAY:
        return [tree_to_payload(item.get("child") or {}) for item in tree.get("items") or []]
    return tree.get("node") or {"kind": "literal", "value": ""}


def initialize_body_composer_state(prefix: str, payload: object) -> None:
    tree_key = _body_key(prefix, "tree")
    if tree_key not in st.session_state:
        st.session_state[tree_key] = body_payload_to_tree(payload)


def _render_tree_node(
    prefix: str,
    tree: dict,
    depth: int = 0,
    *,
    available_constants: list[dict] | None = None,
    available_sources: list[dict] | None = None,
) -> dict:
    ui_key = str(tree.get("ui_key") or new_ui_key())
    node_type = str(tree.get("type") or BODY_NODE_VALUE).strip()
    node_prefix = f"{prefix}_{ui_key}"

    type_key = f"{node_prefix}_type"
    if type_key not in st.session_state:
        st.session_state[type_key] = node_type

    current_type = str(st.session_state.get(type_key) or BODY_NODE_VALUE).strip()

    if current_type == BODY_NODE_VALUE:
        node = tree.get("node") or {"kind": "literal", "value": ""}
        val_prefix = f"{node_prefix}_val"
        initialize_guided_value_state(val_prefix, node)
        type_cols = st.columns([2, 8], gap="small", vertical_alignment="center")
        with type_cols[0]:
            st.selectbox(
                "Type",
                options=BODY_NODE_OPTIONS,
                key=type_key,
                format_func=lambda t: BODY_NODE_LABELS.get(t, t),
                label_visibility="collapsed",
            )
        with type_cols[1]:
            render_guided_value_control(
                val_prefix,
                available_constants=available_constants,
                available_sources=available_sources,
                show_label=False,
            )
        return {"type": BODY_NODE_VALUE, "node": node, "ui_key": ui_key}

    if current_type == BODY_NODE_OBJECT:
        entries = tree.get("entries") or [] if node_type == BODY_NODE_OBJECT else []
        entries_key = f"{node_prefix}_entries"
        if entries_key not in st.session_state:
            st.session_state[entries_key] = entries

        entries = st.session_state[entries_key]

        type_cols = st.columns([2, 7, 1], gap="small", vertical_alignment="center")
        with type_cols[0]:
            st.selectbox(
                "Type",
                options=BODY_NODE_OPTIONS,
                key=type_key,
                format_func=lambda t: BODY_NODE_LABELS.get(t, t),
                label_visibility="collapsed",
            )
        with type_cols[2]:
            if st.button("", key=f"{node_prefix}_add_entry", icon=":material/add:", use_container_width=True):
                entries.append({
                    "key": "",
                    "child": {"type": BODY_NODE_VALUE, "node": {"kind": "literal", "value": ""}, "ui_key": new_ui_key()},
                    "ui_key": new_ui_key(),
                })
                st.session_state[entries_key] = entries
                st.rerun()

        with st.container():
            for idx, entry in enumerate(entries):
                entry_ui_key = str(entry.get("ui_key") or new_ui_key())
                entry["ui_key"] = entry_ui_key
                entry_prefix = f"{node_prefix}_e_{entry_ui_key}"
                entry_key_input = f"{entry_prefix}_key"
                if entry_key_input not in st.session_state:
                    st.session_state[entry_key_input] = str(entry.get("key") or "")

                entry_cols = st.columns([3, 8, 1], gap="small", vertical_alignment="top")
                with entry_cols[0]:
                    st.text_input(
                        "Key",
                        key=entry_key_input,
                        label_visibility="collapsed",
                        placeholder=f"field_{idx + 1}",
                    )
                with entry_cols[1]:
                    child = entry.get("child") or {"type": BODY_NODE_VALUE, "node": {"kind": "literal", "value": ""}, "ui_key": new_ui_key()}
                    entry["child"] = _render_tree_node(
                        entry_prefix,
                        child,
                        depth=depth + 1,
                        available_constants=available_constants,
                        available_sources=available_sources,
                    )
                with entry_cols[2]:
                    if st.button("", key=f"{entry_prefix}_del", icon=":material/delete:", use_container_width=True):
                        entries.pop(idx)
                        st.session_state[entries_key] = entries
                        st.rerun()

                entry["key"] = str(st.session_state.get(entry_key_input) or "")

        return {"type": BODY_NODE_OBJECT, "entries": entries, "ui_key": ui_key}

    if current_type == BODY_NODE_ARRAY:
        items = tree.get("items") or [] if node_type == BODY_NODE_ARRAY else []
        items_key = f"{node_prefix}_items"
        if items_key not in st.session_state:
            st.session_state[items_key] = items

        items = st.session_state[items_key]

        type_cols = st.columns([2, 7, 1], gap="small", vertical_alignment="center")
        with type_cols[0]:
            st.selectbox(
                "Type",
                options=BODY_NODE_OPTIONS,
                key=type_key,
                format_func=lambda t: BODY_NODE_LABELS.get(t, t),
                label_visibility="collapsed",
            )
        with type_cols[2]:
            if st.button("", key=f"{node_prefix}_add_item", icon=":material/add:", use_container_width=True):
                items.append({
                    "child": {"type": BODY_NODE_VALUE, "node": {"kind": "literal", "value": ""}, "ui_key": new_ui_key()},
                    "ui_key": new_ui_key(),
                })
                st.session_state[items_key] = items
                st.rerun()

        with st.container():
            for idx, item in enumerate(items):
                item_ui_key = str(item.get("ui_key") or new_ui_key())
                item["ui_key"] = item_ui_key
                item_prefix = f"{node_prefix}_i_{item_ui_key}"

                item_cols = st.columns([1, 10, 1], gap="small", vertical_alignment="top")
                with item_cols[0]:
                    st.caption(f"[{idx}]")
                with item_cols[1]:
                    child = item.get("child") or {"type": BODY_NODE_VALUE, "node": {"kind": "literal", "value": ""}, "ui_key": new_ui_key()}
                    item["child"] = _render_tree_node(
                        item_prefix,
                        child,
                        depth=depth + 1,
                        available_constants=available_constants,
                        available_sources=available_sources,
                    )
                with item_cols[2]:
                    if st.button("", key=f"{item_prefix}_del", icon=":material/delete:", use_container_width=True):
                        items.pop(idx)
                        st.session_state[items_key] = items
                        st.rerun()

        return {"type": BODY_NODE_ARRAY, "items": items, "ui_key": ui_key}

    return tree


def render_body_composer(
    prefix: str,
    *,
    available_constants: list[dict] | None = None,
    available_sources: list[dict] | None = None,
) -> None:
    tree_key = _body_key(prefix, "tree")
    tree = st.session_state.get(tree_key) or body_payload_to_tree(None)
    updated = _render_tree_node(
        prefix,
        tree,
        available_constants=available_constants,
        available_sources=available_sources,
    )
    st.session_state[tree_key] = updated


def _collect_tree_node(prefix: str, tree: dict) -> tuple[object, str | None]:
    ui_key = str(tree.get("ui_key") or "")
    node_prefix = f"{prefix}_{ui_key}"
    type_key = f"{node_prefix}_type"
    current_type = str(st.session_state.get(type_key) or BODY_NODE_VALUE).strip()

    if current_type == BODY_NODE_VALUE:
        val_prefix = f"{node_prefix}_val"
        node, error = collect_guided_value(val_prefix)
        if error:
            return None, error
        return node, None

    if current_type == BODY_NODE_OBJECT:
        entries = tree.get("entries") or []
        result = {}
        seen_keys: set[str] = set()
        for idx, entry in enumerate(entries, start=1):
            key = str(entry.get("key") or "").strip()
            if not key:
                return None, f"Body object: key is required at entry {idx}."
            if key in seen_keys:
                return None, f"Body object: duplicate key '{key}' at entry {idx}."
            seen_keys.add(key)
            entry_ui_key = str(entry.get("ui_key") or "")
            entry_prefix = f"{node_prefix}_e_{entry_ui_key}"
            child_value, child_error = _collect_tree_node(
                entry_prefix,
                entry.get("child") or {},
            )
            if child_error:
                return None, child_error
            result[key] = child_value
        return result, None

    if current_type == BODY_NODE_ARRAY:
        items = tree.get("items") or []
        result_list = []
        for idx, item in enumerate(items):
            item_ui_key = str(item.get("ui_key") or "")
            item_prefix = f"{node_prefix}_i_{item_ui_key}"
            child_value, child_error = _collect_tree_node(
                item_prefix,
                item.get("child") or {},
            )
            if child_error:
                return None, child_error
            result_list.append(child_value)
        return result_list, None

    return None, f"Unknown body node type '{current_type}'."


def collect_body_composer_value(prefix: str) -> tuple[object, str | None]:
    tree_key = _body_key(prefix, "tree")
    tree = st.session_state.get(tree_key) or {}
    return _collect_tree_node(prefix, tree)
