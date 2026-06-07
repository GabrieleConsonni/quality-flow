"""Guided value control for HTTP input nodes.

Provides a value editor with mode selector (Literal, Runtime value, Source, Built-in)
for use in key-value editors, auth fields, and body composer nodes.
"""

import json
from uuid import uuid4

import streamlit as st


VALUE_MODE_LITERAL = "literal"
VALUE_MODE_RUNTIME_VALUE = "runtimeValue"
VALUE_MODE_SOURCE = "source"
VALUE_MODE_BUILT_IN = "builtIn"

VALUE_MODE_OPTIONS = [
    VALUE_MODE_LITERAL,
    VALUE_MODE_RUNTIME_VALUE,
    VALUE_MODE_SOURCE,
    VALUE_MODE_BUILT_IN,
]

VALUE_MODE_LABELS = {
    VALUE_MODE_LITERAL: "Literal",
    VALUE_MODE_RUNTIME_VALUE: "Runtime value",
    VALUE_MODE_SOURCE: "Source",
    VALUE_MODE_BUILT_IN: "Built-in",
}

BUILT_IN_OPTIONS = ["now", "today"]

BUILT_IN_LABELS = {
    "now": "now — current datetime",
    "today": "today — current date",
}


def new_ui_key() -> str:
    return uuid4().hex[:10]


def _guided_key(prefix: str, field: str) -> str:
    return f"{prefix}_gv_{field}"


def node_to_guided_state(node: object) -> dict:
    if isinstance(node, dict):
        kind = str(node.get("kind") or "").strip()
        if kind == VALUE_MODE_LITERAL:
            raw_value = node.get("value")
            if isinstance(raw_value, str):
                text = raw_value
            elif raw_value is None:
                text = ""
            else:
                text = json.dumps(raw_value, ensure_ascii=True)
            return {"mode": VALUE_MODE_LITERAL, "text": text}
        if kind == VALUE_MODE_RUNTIME_VALUE:
            return {
                "mode": VALUE_MODE_RUNTIME_VALUE,
                "definitionId": str(node.get("definitionId") or ""),
                "fieldPath": str(node.get("fieldPath") or node.get("field_path") or ""),
            }
        if kind == VALUE_MODE_SOURCE:
            return {
                "mode": VALUE_MODE_SOURCE,
                "sourceCode": str(node.get("sourceCode") or ""),
            }
        if kind == VALUE_MODE_BUILT_IN:
            return {
                "mode": VALUE_MODE_BUILT_IN,
                "resolver": str(node.get("resolver") or ""),
            }
    if node is None:
        return {"mode": VALUE_MODE_LITERAL, "text": ""}
    if isinstance(node, str):
        return {"mode": VALUE_MODE_LITERAL, "text": node}
    return {"mode": VALUE_MODE_LITERAL, "text": json.dumps(node, ensure_ascii=True)}


def guided_state_to_node(state: dict) -> dict:
    mode = str(state.get("mode") or VALUE_MODE_LITERAL).strip()
    if mode == VALUE_MODE_RUNTIME_VALUE:
        node = {
            "kind": VALUE_MODE_RUNTIME_VALUE,
            "definitionId": str(state.get("definitionId") or "").strip(),
        }
        field_path = str(state.get("fieldPath") or "").strip()
        if field_path:
            node["fieldPath"] = field_path
        return node
    if mode == VALUE_MODE_SOURCE:
        return {
            "kind": VALUE_MODE_SOURCE,
            "sourceCode": str(state.get("sourceCode") or "").strip(),
        }
    if mode == VALUE_MODE_BUILT_IN:
        return {
            "kind": VALUE_MODE_BUILT_IN,
            "resolver": str(state.get("resolver") or "").strip(),
        }
    text = str(state.get("text") or "").strip()
    try:
        parsed = json.loads(text)
        return {"kind": VALUE_MODE_LITERAL, "value": parsed}
    except (json.JSONDecodeError, ValueError):
        return {"kind": VALUE_MODE_LITERAL, "value": text}


def initialize_guided_value_state(
    prefix: str,
    node: object,
) -> None:
    mode_key = _guided_key(prefix, "mode")
    if mode_key in st.session_state:
        return
    state = node_to_guided_state(node)
    st.session_state[mode_key] = state.get("mode", VALUE_MODE_LITERAL)
    st.session_state[_guided_key(prefix, "text")] = state.get("text", "")
    st.session_state[_guided_key(prefix, "definitionId")] = state.get("definitionId", "")
    st.session_state[_guided_key(prefix, "fieldPath")] = state.get("fieldPath", "")
    st.session_state[_guided_key(prefix, "sourceCode")] = state.get("sourceCode", "")
    st.session_state[_guided_key(prefix, "resolver")] = state.get("resolver", "")


def render_guided_value_control(
    prefix: str,
    *,
    available_constants: list[dict] | None = None,
    available_sources: list[dict] | None = None,
    allowed_modes: list[str] | None = None,
    label: str = "Value",
    show_label: bool = True,
    placeholder: str = "",
    text_area: bool = False,
    show_runtime_field_path: bool = False,
) -> None:
    mode_key = _guided_key(prefix, "mode")
    label_visibility = "visible" if show_label else "collapsed"
    mode_label_visibility = "visible" if show_label else "collapsed"
    mode_options = [
        mode
        for mode in (allowed_modes or VALUE_MODE_OPTIONS)
        if mode in VALUE_MODE_OPTIONS
    ] or [VALUE_MODE_LITERAL]

    current_mode = str(st.session_state.get(mode_key) or VALUE_MODE_LITERAL).strip()
    if current_mode not in mode_options:
        current_mode = mode_options[0]
        st.session_state[mode_key] = current_mode

    st.selectbox(
        "Mode",
        options=mode_options,
        key=mode_key,
        format_func=lambda m: VALUE_MODE_LABELS.get(m, m),
        label_visibility=mode_label_visibility,
    )

    current_mode = str(st.session_state.get(mode_key) or VALUE_MODE_LITERAL).strip()
    if current_mode == VALUE_MODE_LITERAL:
        if text_area:
            st.text_area(
                label,
                key=_guided_key(prefix, "text"),
                placeholder=placeholder,
                label_visibility=label_visibility,
                height=120,
            )
        else:
            st.text_input(
                label,
                key=_guided_key(prefix, "text"),
                placeholder=placeholder,
                label_visibility=label_visibility,
            )
    elif current_mode == VALUE_MODE_RUNTIME_VALUE:
        constants = available_constants or []
        options = [str(c.get("definitionId") or c.get("path") or "").strip() for c in constants if c]
        def_id_key = _guided_key(prefix, "definitionId")
        field_path_key = _guided_key(prefix, "fieldPath")
        current = str(st.session_state.get(def_id_key) or "").strip()
        if current and current not in options:
            options = [current] + options

        def _format_constant_option(opt):
            for c in constants:
                if str(c.get("definitionId") or c.get("path") or "").strip() == opt:
                    name = c.get("name") or opt
                    vtype = c.get("value_type") or ""
                    return f"{name} ({vtype})" if vtype else str(name)
            return str(opt)

        st.selectbox(
            label,
            options=options or [""],
            key=def_id_key,
            format_func=_format_constant_option,
            disabled=not bool(options),
            label_visibility=label_visibility,
        )
        if show_runtime_field_path:
            selected_option = str(st.session_state.get(def_id_key) or "").strip()
            selected_definition = next(
                (
                    item
                    for item in constants
                    if str(item.get("definitionId") or item.get("path") or "").strip() == selected_option
                ),
                None,
            )
            supports_field_path = str((selected_definition or {}).get("value_type") or "").strip() in {"json", "jsonArray"}
            if supports_field_path:
                st.text_input(
                    "Path",
                    key=field_path_key,
                    placeholder="payload.access_token, items[0].id or [0].id",
                    help="Relative path inside the selected runtime value.",
                )
            else:
                st.session_state[field_path_key] = ""
    elif current_mode == VALUE_MODE_SOURCE:
        sources = available_sources or []
        options = [str(s.get("sourceCode") or s.get("code") or "").strip() for s in sources if s]
        src_key = _guided_key(prefix, "sourceCode")
        current = str(st.session_state.get(src_key) or "").strip()
        if current and current not in options:
            options = [current] + options

        def _format_source_option(opt):
            for s in sources:
                if str(s.get("sourceCode") or s.get("code") or "").strip() == opt:
                    name = s.get("name") or opt
                    stype = s.get("sourceType") or s.get("value_type") or ""
                    return f"{name} ({stype})" if stype else str(name)
            return str(opt)

        st.selectbox(
            label,
            options=options or [""],
            key=src_key,
            format_func=_format_source_option,
            disabled=not bool(options),
            label_visibility=label_visibility,
        )
    elif current_mode == VALUE_MODE_BUILT_IN:
        resolver_key = _guided_key(prefix, "resolver")
        st.selectbox(
            label,
            options=BUILT_IN_OPTIONS,
            key=resolver_key,
            format_func=lambda r: BUILT_IN_LABELS.get(r, r),
            label_visibility=label_visibility,
        )


def collect_guided_value(prefix: str) -> tuple[dict, str | None]:
    mode_key = _guided_key(prefix, "mode")
    mode = str(st.session_state.get(mode_key) or VALUE_MODE_LITERAL).strip()

    if mode == VALUE_MODE_LITERAL:
        text = str(st.session_state.get(_guided_key(prefix, "text")) or "").strip()
        try:
            parsed = json.loads(text)
            return {"kind": VALUE_MODE_LITERAL, "value": parsed}, None
        except (json.JSONDecodeError, ValueError):
            return {"kind": VALUE_MODE_LITERAL, "value": text}, None

    if mode == VALUE_MODE_RUNTIME_VALUE:
        def_id = str(st.session_state.get(_guided_key(prefix, "definitionId")) or "").strip()
        if not def_id:
            return {}, "Runtime value is required."
        node = {"kind": VALUE_MODE_RUNTIME_VALUE, "definitionId": def_id}
        field_path = str(st.session_state.get(_guided_key(prefix, "fieldPath")) or "").strip()
        if field_path:
            node["fieldPath"] = field_path
        return node, None

    if mode == VALUE_MODE_SOURCE:
        src = str(st.session_state.get(_guided_key(prefix, "sourceCode")) or "").strip()
        if not src:
            return {}, "Source is required."
        return {"kind": VALUE_MODE_SOURCE, "sourceCode": src}, None

    if mode == VALUE_MODE_BUILT_IN:
        resolver = str(st.session_state.get(_guided_key(prefix, "resolver")) or "").strip()
        if not resolver:
            return {}, "Built-in resolver is required."
        return {"kind": VALUE_MODE_BUILT_IN, "resolver": resolver}, None

    return {}, f"Unsupported mode '{mode}'."


def validate_guided_value_node(
    node: dict,
    *,
    allowed_modes: list[str] | None = None,
    scalar_only: bool = False,
) -> str | None:
    kind = str((node or {}).get("kind") or "").strip()
    if allowed_modes is not None and kind not in allowed_modes:
        return f"Unsupported value type '{kind}'."
    if scalar_only and kind == VALUE_MODE_LITERAL and isinstance((node or {}).get("value"), (dict, list)):
        return "Only scalar literal values are supported."
    return None
