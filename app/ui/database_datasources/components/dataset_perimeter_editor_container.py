import json

import pandas as pd
import streamlit as st

from elaborations_shared.components.test_command_component import find_draft_test_by_ui_key
from elaborations_shared.services.data_loader_service import load_test_editor_context
from database_datasources.services.api_service import update_database_datasource
from database_datasources.services.data_loader_service import (
    invalidate_database_datasource_preview,
    load_database_connections,
    load_database_datasource_preview,
    load_database_datasources,
    load_database_object_preview,
)
from database_datasources.services.perimeter_service import (
    PERIMETER_OPERATORS,
    PERIMETER_PARAMETER_DEFAULT_FUNCTION_OPTIONS,
    PERIMETER_PARAMETER_DEFAULT_MODE_OPTIONS,
    PERIMETER_PARAMETER_TYPES,
    build_connection_label,
    build_dataset_summary,
    build_perimeter_payload,
    build_perimeter_scope_key,
    default_filter_items,
    default_filter_logic,
    default_parameter_rows,
    default_selected_columns,
    default_sort_rows,
    normalize_filter_condition,
    normalize_filter_items,
    normalize_parameter_editor_rows,
    normalize_parameter_rows,
    normalize_filter_rows,
    normalize_sort_rows,
)
from database_datasources.services.state_service import (
    clear_database_datasource_perimeter_edit_id,
    get_database_datasource_perimeter_editor_mode,
    get_database_datasource_perimeter_return_target,
    get_database_datasource_perimeter_edit_id,
    get_test_source_perimeter_target,
    pop_database_datasource_feedback,
    set_selected_database_datasource_id,
)
from elaborations_shared.services.state_keys import TEST_EDITOR_DATABASE_DATASOURCES_KEY
from test_suites.services.api_service import (
    get_test_suite_by_id,
    preview_suite_source_via_api,
    update_test_suite,
)
from test_suites.services.draft_mapper import build_test_suite_draft, draft_to_test_suite_payload
from test_suites.services.state_keys import (
    SELECTED_TEST_SUITE_ID_KEY,
    TEST_SUITE_DRAFT_KEY,
    TEST_SUITE_FEEDBACK_KEY,
)

DATASETS_PAGE_PATH = "pages/Datasets.py"
FILTER_LOGIC_OPTIONS = ["AND", "OR"]
NULL_FILTER_OPERATORS = {"is_null", "is_not_null"}
SORT_DIRECTION_OPTIONS = ["asc", "desc"]
FILTER_VALUE_MODE_OPTIONS = ["literal", "parameter"]
TEST_SOURCE_PERIMETER_PREVIEW_CACHE_KEY = "test_source_perimeter_preview_cache"


def _set_selected_columns(scope_key: str, columns: list[str]):
    st.session_state[f"{scope_key}_selected_columns"] = list(columns)


def _show_feedback():
    message, level = pop_database_datasource_feedback()
    if not message:
        return
    if level == "error":
        st.error(message)
        return
    if level == "warning":
        st.warning(message)
        return
    st.success(message)


def _load_object_columns(
    connection_id: str,
    object_name: str,
    object_type: str,
    schema: str | None,
) -> tuple[list[str], str | None]:
    object_preview = load_database_object_preview(
        connection_id,
        object_name,
        object_type=object_type or "table",
        schema=schema,
        limit=1,
        force=False,
    )
    if isinstance(object_preview, dict) and object_preview.get("error"):
        return [], str(object_preview.get("error"))
    columns = object_preview.get("columns") if isinstance(object_preview, dict) else []
    return [str(column) for column in columns if column], None


def _render_selected_columns_editor(
    scope_key: str,
    available_columns: list[str],
    perimeter: dict | None,
) -> list[str]:
    selected_columns_key = f"{scope_key}_selected_columns"
    if selected_columns_key not in st.session_state:
        st.session_state[selected_columns_key] = default_selected_columns(perimeter, available_columns)

    selected_columns = st.multiselect(
        "Selected columns",
        options=available_columns,
        key=selected_columns_key,
        label_visibility="collapsed",
        help="Lascia vuoto per leggere tutte le colonne.",
    )

    action_cols = st.columns(2, gap="small")
    with action_cols[0]:
        st.button(
            "Select all columns",
            key=f"{scope_key}_select_all_columns_btn",
            type="secondary",
            use_container_width=True,
            on_click=_set_selected_columns,
            args=(scope_key, list(available_columns)),
        )
    with action_cols[1]:
        st.button(
            "Reset columns",
            key=f"{scope_key}_reset_columns_btn",
            type="secondary",
            use_container_width=True,
            on_click=_set_selected_columns,
            args=(scope_key, []),
        )
    return list(st.session_state.get(selected_columns_key) or selected_columns or [])


def _build_sort_condition_label(sort_condition: dict) -> str:
    field = str(sort_condition.get("field") or "").strip()
    direction = str(sort_condition.get("direction") or "asc").strip().lower() or "asc"
    return f"{field}[{direction}]"


def _close_sort_condition_dialog(scope_key: str):
    st.session_state[f"{scope_key}_sort_dialog_open"] = False
    st.session_state.pop(f"{scope_key}_sort_dialog_field", None)
    st.session_state.pop(f"{scope_key}_sort_dialog_direction", None)


@st.dialog("Add sort condition", width="medium")
def _render_add_sort_condition_dialog(scope_key: str, available_columns: list[str]):
    field_key = f"{scope_key}_sort_dialog_field"
    direction_key = f"{scope_key}_sort_dialog_direction"
    sort_conditions_key = f"{scope_key}_sort_conditions"

    if field_key not in st.session_state:
        st.session_state[field_key] = ""
    if direction_key not in st.session_state:
        st.session_state[direction_key] = "asc"

    st.selectbox(
        "Field",
        options=[""] + list(available_columns),
        key=field_key,
        format_func=lambda value: str(value or ""),
    )
    st.selectbox(
        "Type",
        options=SORT_DIRECTION_OPTIONS,
        key=direction_key,
    )

    action_cols = st.columns(2, gap="small")
    with action_cols[0]:
        if st.button(
            "Cancel",
            key=f"{scope_key}_sort_dialog_cancel_btn",
            type="secondary",
            use_container_width=True,
        ):
            _close_sort_condition_dialog(scope_key)
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Save",
            key=f"{scope_key}_sort_dialog_save_btn",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            selected_field = str(st.session_state.get(field_key) or "").strip()
            selected_direction = str(st.session_state.get(direction_key) or "asc").strip().lower() or "asc"
            if not selected_field:
                st.error("Field is required.")
                return

            sort_conditions = normalize_sort_rows(st.session_state.get(sort_conditions_key) or [])
            updated = False
            for sort_condition in sort_conditions:
                if str(sort_condition.get("field") or "").strip() != selected_field:
                    continue
                sort_condition["direction"] = selected_direction
                updated = True
                break
            if not updated:
                sort_conditions.append(
                    {
                        "field": selected_field,
                        "direction": selected_direction,
                    }
                )

            st.session_state[sort_conditions_key] = sort_conditions
            _close_sort_condition_dialog(scope_key)
            st.rerun()


def _render_sort_editor(scope_key: str, available_columns: list[str], perimeter: dict | None) -> list[dict]:
    sort_conditions_key = f"{scope_key}_sort_conditions"
    sort_selected_key = f"{scope_key}_sort_selected"
    sort_labels_key = f"{scope_key}_sort_labels"
    sort_dialog_open_key = f"{scope_key}_sort_dialog_open"

    if sort_conditions_key not in st.session_state:
        st.session_state[sort_conditions_key] = normalize_sort_rows(default_sort_rows(perimeter))

    if st.session_state.get(sort_dialog_open_key):
        _render_add_sort_condition_dialog(scope_key, available_columns)

    sort_conditions = normalize_sort_rows(st.session_state.get(sort_conditions_key) or [])
    st.session_state[sort_conditions_key] = sort_conditions
    sort_labels = [_build_sort_condition_label(sort_condition) for sort_condition in sort_conditions]

    if sort_selected_key not in st.session_state:
        st.session_state[sort_selected_key] = list(sort_labels)
    elif st.session_state.get(sort_labels_key) != sort_labels:
        st.session_state[sort_selected_key] = list(sort_labels)
    st.session_state[sort_labels_key] = list(sort_labels)

    selected_sort_labels = st.multiselect(
        "Sort conditions",
        options=sort_labels,
        key=sort_selected_key,
        label_visibility="collapsed",
        help="Rimuovi un valore per eliminare la sort condition corrispondente.",
    )
    if selected_sort_labels != sort_labels:
        remaining_conditions = [
            sort_condition
            for sort_condition in sort_conditions
            if _build_sort_condition_label(sort_condition) in selected_sort_labels
        ]
        st.session_state[sort_conditions_key] = remaining_conditions
        st.session_state[sort_selected_key] = list(selected_sort_labels)
        st.session_state[sort_labels_key] = list(selected_sort_labels)
        st.rerun()

    _, action_col = st.columns([8, 1], gap="small", vertical_alignment="center")
    with action_col:
        if st.button(
            "",
            key=f"{scope_key}_sort_add_btn",
            icon=":material/add:",
            help="Add sort condition",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state[sort_dialog_open_key] = True
            st.rerun()

    return sort_conditions


def _build_filter_editor_config(available_columns: list[str]) -> dict:
    return {
        "field": st.column_config.SelectboxColumn(
            "Field",
            options=available_columns,
            required=False,
        ),
        "operator": st.column_config.SelectboxColumn(
            "Operator",
            options=PERIMETER_OPERATORS,
            required=False,
        ),
        "value": st.column_config.TextColumn("Value"),
    }


def _available_parameter_names(scope_key: str) -> list[str]:
    parameters_key = f"{scope_key}_parameters"
    parameter_rows = normalize_parameter_editor_rows(st.session_state.get(parameters_key) or [])
    st.session_state[parameters_key] = parameter_rows
    return [
        str(item.get("name") or "").strip()
        for item in normalize_parameter_rows(parameter_rows)
        if str(item.get("name") or "").strip()
    ]


def _filter_condition_value_mode(condition: dict) -> str:
    value = condition.get("value")
    if isinstance(value, dict) and str(value.get("kind") or "").strip().lower() == "parameter":
        return "parameter"
    return "literal"


def _filter_condition_parameter_name(condition: dict) -> str:
    value = condition.get("value")
    if isinstance(value, dict) and str(value.get("kind") or "").strip().lower() == "parameter":
        return str(value.get("name") or "").strip()
    return ""


def _format_filter_condition_value(condition: dict) -> str:
    operator = str(condition.get("operator") or "").strip().lower()
    if operator in NULL_FILTER_OPERATORS:
        return "-"
    value = condition.get("value")
    if value is None:
        return "-"
    if isinstance(value, dict) and str(value.get("kind") or "").strip().lower() == "parameter":
        parameter_name = str(value.get("name") or "").strip()
        return f"${parameter_name}" if parameter_name else "-"
    return str(value)


def _format_filter_condition_text(condition: dict) -> str:
    field = str(condition.get("field") or "").strip() or "-"
    operator = str(condition.get("operator") or "").strip().lower() or "-"
    if operator in NULL_FILTER_OPERATORS:
        return f"*{field}* **{operator}**"
    value = condition.get("value")
    if isinstance(value, dict) and str(value.get("kind") or "").strip().lower() == "parameter":
        parameter_name = str(value.get("name") or "").strip()
        formatted_value = f"${parameter_name}" if parameter_name else "$?"
    elif isinstance(value, str):
        formatted_value = f"'{value}'"
    elif value is None:
        formatted_value = "null"
    else:
        formatted_value = str(value)
    return f"*{field}* **{operator}** {formatted_value}"


def _close_filter_condition_dialog(scope_key: str):
    st.session_state[f"{scope_key}_filter_condition_dialog_open"] = False
    st.session_state.pop(f"{scope_key}_filter_condition_dialog_field", None)
    st.session_state.pop(f"{scope_key}_filter_condition_dialog_operator", None)
    st.session_state.pop(f"{scope_key}_filter_condition_dialog_value_mode", None)
    st.session_state.pop(f"{scope_key}_filter_condition_dialog_value", None)
    st.session_state.pop(f"{scope_key}_filter_condition_dialog_parameter_name", None)


def _close_filter_group_dialog(scope_key: str):
    st.session_state[f"{scope_key}_filter_group_dialog_open"] = False
    st.session_state.pop(f"{scope_key}_filter_group_dialog_logic", None)
    st.session_state.pop(f"{scope_key}_filter_group_dialog_editor", None)


def _append_filter_item(scope_key: str, item: dict):
    filter_items_key = f"{scope_key}_filter_items"
    filter_items = normalize_filter_items(st.session_state.get(filter_items_key) or [])
    filter_items.append(item)
    st.session_state[filter_items_key] = filter_items


def _delete_filter_item(scope_key: str, item_index: int):
    filter_items_key = f"{scope_key}_filter_items"
    filter_items = normalize_filter_items(st.session_state.get(filter_items_key) or [])
    if 0 <= item_index < len(filter_items):
        filter_items.pop(item_index)
    st.session_state[filter_items_key] = filter_items


def _delete_filter_group_condition(scope_key: str, group_index: int, condition_index: int):
    filter_items_key = f"{scope_key}_filter_items"
    filter_items = normalize_filter_items(st.session_state.get(filter_items_key) or [])
    if not (0 <= group_index < len(filter_items)):
        return
    group_item = filter_items[group_index]
    if str(group_item.get("kind") or "") != "group":
        return

    conditions = list(group_item.get("conditions") or [])
    if not (0 <= condition_index < len(conditions)):
        return

    conditions.pop(condition_index)
    if conditions:
        group_item["conditions"] = conditions
        filter_items[group_index] = group_item
    else:
        filter_items.pop(group_index)
    st.session_state[filter_items_key] = filter_items


def _open_filter_condition_edit_dialog(
    scope_key: str,
    condition: dict,
    item_index: int,
    condition_index: int | None = None,
):
    st.session_state[f"{scope_key}_filter_condition_edit_dialog_open"] = True
    st.session_state[f"{scope_key}_filter_condition_edit_dialog_item_index"] = item_index
    st.session_state[f"{scope_key}_filter_condition_edit_dialog_condition_index"] = condition_index
    st.session_state[f"{scope_key}_filter_condition_edit_dialog_field"] = str(condition.get("field") or "").strip()
    st.session_state[f"{scope_key}_filter_condition_edit_dialog_operator"] = (
        str(condition.get("operator") or PERIMETER_OPERATORS[0]).strip().lower()
    )
    st.session_state[f"{scope_key}_filter_condition_edit_dialog_value_mode"] = _filter_condition_value_mode(condition)
    st.session_state[f"{scope_key}_filter_condition_edit_dialog_value"] = (
        ""
        if condition.get("value") is None or _filter_condition_value_mode(condition) == "parameter"
        else str(condition.get("value"))
    )
    st.session_state[f"{scope_key}_filter_condition_edit_dialog_parameter_name"] = _filter_condition_parameter_name(condition)


def _close_filter_condition_edit_dialog(scope_key: str):
    st.session_state[f"{scope_key}_filter_condition_edit_dialog_open"] = False
    st.session_state.pop(f"{scope_key}_filter_condition_edit_dialog_item_index", None)
    st.session_state.pop(f"{scope_key}_filter_condition_edit_dialog_condition_index", None)
    st.session_state.pop(f"{scope_key}_filter_condition_edit_dialog_field", None)
    st.session_state.pop(f"{scope_key}_filter_condition_edit_dialog_operator", None)
    st.session_state.pop(f"{scope_key}_filter_condition_edit_dialog_value_mode", None)
    st.session_state.pop(f"{scope_key}_filter_condition_edit_dialog_value", None)
    st.session_state.pop(f"{scope_key}_filter_condition_edit_dialog_parameter_name", None)


def _update_filter_condition(
    scope_key: str,
    item_index: int,
    updated_condition: dict,
    condition_index: int | None = None,
):
    filter_items_key = f"{scope_key}_filter_items"
    filter_items = normalize_filter_items(st.session_state.get(filter_items_key) or [])
    if not (0 <= item_index < len(filter_items)):
        return
    if condition_index is None:
        filter_items[item_index] = {
            "kind": "condition",
            **updated_condition,
        }
        st.session_state[filter_items_key] = filter_items
        return

    target_item = filter_items[item_index]
    if str(target_item.get("kind") or "") != "group":
        return
    conditions = list(target_item.get("conditions") or [])
    if not (0 <= condition_index < len(conditions)):
        return
    conditions[condition_index] = updated_condition
    target_item["conditions"] = conditions
    filter_items[item_index] = target_item
    st.session_state[filter_items_key] = filter_items


@st.dialog("Add condition", width="medium")
def _render_add_filter_condition_dialog(
    scope_key: str,
    available_columns: list[str],
    available_parameter_names: list[str],
):
    field_key = f"{scope_key}_filter_condition_dialog_field"
    operator_key = f"{scope_key}_filter_condition_dialog_operator"
    value_mode_key = f"{scope_key}_filter_condition_dialog_value_mode"
    value_key = f"{scope_key}_filter_condition_dialog_value"
    parameter_name_key = f"{scope_key}_filter_condition_dialog_parameter_name"

    if field_key not in st.session_state:
        st.session_state[field_key] = ""
    if operator_key not in st.session_state:
        st.session_state[operator_key] = PERIMETER_OPERATORS[0]
    if value_mode_key not in st.session_state:
        st.session_state[value_mode_key] = FILTER_VALUE_MODE_OPTIONS[0]
    if value_key not in st.session_state:
        st.session_state[value_key] = ""
    if parameter_name_key not in st.session_state:
        st.session_state[parameter_name_key] = ""

    st.selectbox(
        "Field",
        options=[""] + list(available_columns),
        key=field_key,
        format_func=lambda value: str(value or ""),
    )
    st.selectbox(
        "Operator",
        options=PERIMETER_OPERATORS,
        key=operator_key,
    )
    is_null_operator = str(st.session_state.get(operator_key) or "").strip().lower() in NULL_FILTER_OPERATORS
    st.selectbox(
        "Value type",
        options=FILTER_VALUE_MODE_OPTIONS,
        key=value_mode_key,
        disabled=is_null_operator,
        format_func=lambda value: "Parameter" if str(value or "").strip() == "parameter" else "Literal",
    )
    if str(st.session_state.get(value_mode_key) or "literal").strip().lower() == "parameter":
        st.selectbox(
            "Parameter",
            options=available_parameter_names or [""],
            key=parameter_name_key,
            disabled=is_null_operator or not bool(available_parameter_names),
            format_func=lambda value: str(value or ""),
        )
        if not available_parameter_names:
            st.info("Define at least one parameter before using parameter references in filters.")
    else:
        st.text_input(
            "Value",
            key=value_key,
            disabled=is_null_operator,
        )

    action_cols = st.columns(2, gap="small")
    with action_cols[0]:
        if st.button(
            "Cancel",
            key=f"{scope_key}_filter_condition_dialog_cancel_btn",
            type="secondary",
            use_container_width=True,
        ):
            _close_filter_condition_dialog(scope_key)
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Save",
            key=f"{scope_key}_filter_condition_dialog_save_btn",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            operator = str(st.session_state.get(operator_key) or "").strip().lower()
            raw_condition = {
                "field": str(st.session_state.get(field_key) or "").strip(),
                "operator": operator,
            }
            if operator not in NULL_FILTER_OPERATORS:
                value_mode = str(st.session_state.get(value_mode_key) or "literal").strip().lower()
                if value_mode == "parameter":
                    parameter_name = str(st.session_state.get(parameter_name_key) or "").strip()
                    if not parameter_name:
                        st.error("Parameter is required for the selected value type.")
                        return
                    raw_condition["value"] = {
                        "kind": "parameter",
                        "name": parameter_name,
                    }
                else:
                    value = st.session_state.get(value_key)
                    if not str(value or "").strip():
                        st.error("Value is required for the selected operator.")
                        return
                    raw_condition["value"] = value

            condition = normalize_filter_condition(raw_condition)
            if not condition:
                st.error("Field and operator are required.")
                return

            _append_filter_item(
                scope_key,
                {
                    "kind": "condition",
                    **condition,
                },
            )
            _close_filter_condition_dialog(scope_key)
            st.rerun()


@st.dialog("Edit condition", width="medium")
def _render_edit_filter_condition_dialog(
    scope_key: str,
    available_columns: list[str],
    available_parameter_names: list[str],
):
    field_key = f"{scope_key}_filter_condition_edit_dialog_field"
    operator_key = f"{scope_key}_filter_condition_edit_dialog_operator"
    value_mode_key = f"{scope_key}_filter_condition_edit_dialog_value_mode"
    value_key = f"{scope_key}_filter_condition_edit_dialog_value"
    parameter_name_key = f"{scope_key}_filter_condition_edit_dialog_parameter_name"
    item_index_key = f"{scope_key}_filter_condition_edit_dialog_item_index"
    condition_index_key = f"{scope_key}_filter_condition_edit_dialog_condition_index"

    st.selectbox(
        "Field",
        options=[""] + list(available_columns),
        key=field_key,
        format_func=lambda value: str(value or ""),
    )
    st.selectbox(
        "Operator",
        options=PERIMETER_OPERATORS,
        key=operator_key,
    )
    is_null_operator = str(st.session_state.get(operator_key) or "").strip().lower() in NULL_FILTER_OPERATORS
    st.selectbox(
        "Value type",
        options=FILTER_VALUE_MODE_OPTIONS,
        key=value_mode_key,
        disabled=is_null_operator,
        format_func=lambda value: "Parameter" if str(value or "").strip() == "parameter" else "Literal",
    )
    if str(st.session_state.get(value_mode_key) or "literal").strip().lower() == "parameter":
        st.selectbox(
            "Parameter",
            options=available_parameter_names or [""],
            key=parameter_name_key,
            disabled=is_null_operator or not bool(available_parameter_names),
            format_func=lambda value: str(value or ""),
        )
        if not available_parameter_names:
            st.info("Define at least one parameter before using parameter references in filters.")
    else:
        st.text_input(
            "Value",
            key=value_key,
            disabled=is_null_operator,
        )

    action_cols = st.columns(2, gap="small")
    with action_cols[0]:
        if st.button(
            "Cancel",
            key=f"{scope_key}_filter_condition_edit_dialog_cancel_btn",
            type="secondary",
            use_container_width=True,
        ):
            _close_filter_condition_edit_dialog(scope_key)
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Save changes",
            key=f"{scope_key}_filter_condition_edit_dialog_save_btn",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            operator = str(st.session_state.get(operator_key) or "").strip().lower()
            raw_condition = {
                "field": str(st.session_state.get(field_key) or "").strip(),
                "operator": operator,
            }
            if operator not in NULL_FILTER_OPERATORS:
                value_mode = str(st.session_state.get(value_mode_key) or "literal").strip().lower()
                if value_mode == "parameter":
                    parameter_name = str(st.session_state.get(parameter_name_key) or "").strip()
                    if not parameter_name:
                        st.error("Parameter is required for the selected value type.")
                        return
                    raw_condition["value"] = {
                        "kind": "parameter",
                        "name": parameter_name,
                    }
                else:
                    value = st.session_state.get(value_key)
                    if not str(value or "").strip():
                        st.error("Value is required for the selected operator.")
                        return
                    raw_condition["value"] = value

            condition = normalize_filter_condition(raw_condition)
            if not condition:
                st.error("Field and operator are required.")
                return

            _update_filter_condition(
                scope_key,
                item_index=int(st.session_state.get(item_index_key)),
                updated_condition=condition,
                condition_index=(
                    None
                    if st.session_state.get(condition_index_key) is None
                    else int(st.session_state.get(condition_index_key))
                ),
            )
            _close_filter_condition_edit_dialog(scope_key)
            st.rerun()


@st.dialog("Add filter group", width="large")
def _render_add_filter_group_dialog(scope_key: str, available_columns: list[str]):
    logic_key = f"{scope_key}_filter_group_dialog_logic"
    editor_key = f"{scope_key}_filter_group_dialog_editor"

    if logic_key not in st.session_state:
        st.session_state[logic_key] = "AND"

    st.selectbox(
        "Type",
        options=FILTER_LOGIC_OPTIONS,
        key=logic_key,
    )
    group_editor = st.data_editor(
        pd.DataFrame([{"field": "", "operator": "eq", "value": ""}]),
        key=editor_key,
        num_rows="dynamic",
        use_container_width=True,
        column_config=_build_filter_editor_config(available_columns),
    )

    action_cols = st.columns(2, gap="small")
    with action_cols[0]:
        if st.button(
            "Cancel",
            key=f"{scope_key}_filter_group_dialog_cancel_btn",
            type="secondary",
            use_container_width=True,
        ):
            _close_filter_group_dialog(scope_key)
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Save",
            key=f"{scope_key}_filter_group_dialog_save_btn",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            conditions = normalize_filter_rows(group_editor)
            if not conditions:
                st.error("Add at least one valid condition.")
                return

            _append_filter_item(
                scope_key,
                {
                    "kind": "group",
                    "logic": str(st.session_state.get(logic_key) or "AND").strip().upper(),
                    "conditions": conditions,
                },
            )
            _close_filter_group_dialog(scope_key)
            st.rerun()


def _render_filter_condition_line(condition: dict, edit_button_key: str, delete_button_key: str) -> tuple[bool, bool]:
    condition_cols = st.columns([20, 1, 1], gap="small", vertical_alignment="center")
    with condition_cols[0]:
        with st.container(border=True):
            st.markdown(_format_filter_condition_text(condition))
    with condition_cols[1]:
        edit_clicked = st.button(
            "",
            key=edit_button_key,
            icon=":material/edit:",
            type="tertiary",
            use_container_width=True,
        )
    with condition_cols[2]:
        delete_clicked = st.button(
            "",
            key=delete_button_key,
            icon=":material/close:",
            type="tertiary",
            use_container_width=True,
        )
    return edit_clicked, delete_clicked


def _render_parameters_editor(scope_key: str, perimeter: dict | None) -> list[dict]:
    parameters_key = f"{scope_key}_parameters"
    if parameters_key not in st.session_state:
        st.session_state[parameters_key] = default_parameter_rows(perimeter)

    edited_rows = st.data_editor(
        pd.DataFrame(
            normalize_parameter_editor_rows(st.session_state.get(parameters_key) or []),
            columns=["name", "type", "default_mode", "default_value", "default_function", "description"],
        ),
        key=f"{scope_key}_parameters_editor",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "name": st.column_config.TextColumn("Name"),
            "type": st.column_config.SelectboxColumn("Type", options=PERIMETER_PARAMETER_TYPES),
            "default_mode": st.column_config.SelectboxColumn(
                "Default mode",
                options=PERIMETER_PARAMETER_DEFAULT_MODE_OPTIONS,
            ),
            "default_value": st.column_config.TextColumn("Default value"),
            "default_function": st.column_config.SelectboxColumn(
                "Default function",
                options=PERIMETER_PARAMETER_DEFAULT_FUNCTION_OPTIONS,
            ),
            "description": st.column_config.TextColumn("Description"),
        },
    )
    normalized_parameters = normalize_parameter_editor_rows(edited_rows)
    st.session_state[parameters_key] = normalized_parameters
    return normalized_parameters


def _render_filters_editor(
    scope_key: str,
    available_columns: list[str],
    perimeter: dict | None,
    available_parameter_names: list[str],
) -> tuple[str, list[dict]]:
    filter_logic_key = f"{scope_key}_filter_logic"
    filter_items_key = f"{scope_key}_filter_items"
    filter_condition_dialog_key = f"{scope_key}_filter_condition_dialog_open"
    filter_condition_edit_dialog_key = f"{scope_key}_filter_condition_edit_dialog_open"
    filter_group_dialog_key = f"{scope_key}_filter_group_dialog_open"

    if filter_logic_key not in st.session_state:
        st.session_state[filter_logic_key] = default_filter_logic(perimeter)
    if filter_items_key not in st.session_state:
        st.session_state[filter_items_key] = default_filter_items(perimeter)

    st.session_state[filter_items_key] = normalize_filter_items(st.session_state.get(filter_items_key) or [])

    if st.session_state.get(filter_group_dialog_key):
        _render_add_filter_group_dialog(scope_key, available_columns)
    if st.session_state.get(filter_condition_dialog_key):
        _render_add_filter_condition_dialog(scope_key, available_columns, available_parameter_names)
    if st.session_state.get(filter_condition_edit_dialog_key):
        _render_edit_filter_condition_dialog(scope_key, available_columns, available_parameter_names)

    filter_logic = st.selectbox(
        "",
        options=FILTER_LOGIC_OPTIONS,
        index=0 if st.session_state.get(filter_logic_key, "AND") == "AND" else 1,
        key=filter_logic_key,
    )

    filter_items = normalize_filter_items(st.session_state.get(filter_items_key) or [])
    st.session_state[filter_items_key] = filter_items

    if filter_items:
        for item_index, item in enumerate(filter_items):
            _, filter_container_col,_ = st.columns([1, 14, 1], gap="small")
            if str(item.get("kind") or "") == "group":
                with filter_container_col:
                    with st.container(border=True):
                        group_header_cols = st.columns([9, 1], gap="small", vertical_alignment="center")
                        with group_header_cols[0]:
                            st.markdown(f"**Group [{str(item.get('logic') or 'AND').strip().upper()}]**")
                        with group_header_cols[1]:
                            if st.button(
                                "",
                                key=f"{scope_key}_filter_group_delete_{item_index}",
                                icon=":material/close:",
                                type="tertiary",
                                use_container_width=True,
                            ):
                                _delete_filter_item(scope_key, item_index)
                                st.rerun()

                        for condition_index, condition in enumerate(item.get("conditions") or []):
                            edit_clicked, delete_clicked = _render_filter_condition_line(
                                condition,
                                edit_button_key=f"{scope_key}_filter_group_{item_index}_condition_edit_{condition_index}",
                                delete_button_key=f"{scope_key}_filter_group_{item_index}_condition_delete_{condition_index}",
                            )
                            if edit_clicked:
                                _open_filter_condition_edit_dialog(scope_key, condition, item_index, condition_index)
                                st.rerun()
                            if delete_clicked:
                                _delete_filter_group_condition(scope_key, item_index, condition_index)
                                st.rerun()
                continue

            with filter_container_col:
                edit_clicked, delete_clicked = _render_filter_condition_line(
                    item,
                    edit_button_key=f"{scope_key}_filter_condition_edit_{item_index}",
                    delete_button_key=f"{scope_key}_filter_condition_delete_{item_index}",
                )
                if edit_clicked:
                    _open_filter_condition_edit_dialog(scope_key, item, item_index)
                    st.rerun()
                if delete_clicked:
                    _delete_filter_item(scope_key, item_index)
                    st.rerun()
    else:
        st.info("No filter conditions configured.")

    button_cols = st.columns([2, 4, 4, 2], gap="small", vertical_alignment="center")
    with button_cols[1]:
        if st.button(
            "Add condition group",
            key=f"{scope_key}_add_filter_group_btn",
            icon=":material/add:",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state[filter_group_dialog_key] = True
            st.rerun()
    with button_cols[2]:
        if st.button(
            "Add condition",
            key=f"{scope_key}_add_filter_condition_btn",
            icon=":material/add:",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state[filter_condition_dialog_key] = True
            st.rerun()

    return filter_logic, filter_items


def _render_preview_header(save_disabled: bool, save_button_key: str) -> bool:
    header_col, action_col = st.columns([8, 2], gap="small", vertical_alignment="center")
    with header_col:
        st.markdown("#### Preview")
    with action_col:
        return st.button(
            "Refresh",
            key=save_button_key,
            icon=":material/refresh:",
            type="secondary",
            use_container_width=True,
            disabled=save_disabled,
        )


def _render_preview_content(datasource_id: str, force: bool = False):
    preview_payload = load_database_datasource_preview(datasource_id, force=force)
    if isinstance(preview_payload, dict) and preview_payload.get("error"):
        st.error(f"Errore preview: {preview_payload.get('error')}")
        return
    rows = preview_payload.get("rows") if isinstance(preview_payload, dict) else []
    if rows:
        st.dataframe(rows, use_container_width=True, height=360)
        return
    st.info("Nessun dato disponibile per la preview.")


def _render_test_source_preview_content(source: dict, force: bool = False):
    cache = st.session_state.get(TEST_SOURCE_PERIMETER_PREVIEW_CACHE_KEY)
    if not isinstance(cache, dict):
        cache = {}
        st.session_state[TEST_SOURCE_PERIMETER_PREVIEW_CACHE_KEY] = cache

    cache_key = json.dumps(source or {}, sort_keys=True, ensure_ascii=True)
    if force or cache_key not in cache:
        try:
            cache[cache_key] = preview_suite_source_via_api(source=source)
        except Exception as exc:
            cache[cache_key] = {"error": str(exc)}
        st.session_state[TEST_SOURCE_PERIMETER_PREVIEW_CACHE_KEY] = cache

    preview_payload = cache.get(cache_key)
    if isinstance(preview_payload, dict) and preview_payload.get("error"):
        st.error(f"Errore preview: {preview_payload.get('error')}")
        return
    rows = preview_payload.get("rows") if isinstance(preview_payload, dict) else []
    if rows:
        st.dataframe(rows, use_container_width=True, height=360)
        return
    st.info("Nessun dato disponibile per la preview.")


def _serialize_perimeter_payload(perimeter_payload: dict | None) -> str:
    return json.dumps(perimeter_payload or {}, sort_keys=True, ensure_ascii=True)


def _autosave_perimeter(
    datasource_id: str,
    datasource_item: dict,
    payload: dict,
    perimeter_payload: dict | None,
    scope_key: str,
) -> bool:
    autosave_snapshot_key = f"{scope_key}_autosave_snapshot"
    current_snapshot = _serialize_perimeter_payload(perimeter_payload)
    if autosave_snapshot_key not in st.session_state:
        st.session_state[autosave_snapshot_key] = current_snapshot
        return False
    if st.session_state.get(autosave_snapshot_key) == current_snapshot:
        return False

    try:
        update_database_datasource(
            {
                "id": datasource_id,
                "description": datasource_item.get("description") or "",
                "payload": payload,
                "perimeter": perimeter_payload,
            }
        )
    except Exception as exc:
        st.error(f"Errore autosalvataggio perimetro dataset: {str(exc)}")
        return False

    load_database_datasources(force=True)
    invalidate_database_datasource_preview(str(datasource_id))
    set_selected_database_datasource_id(str(datasource_id))
    st.session_state[autosave_snapshot_key] = current_snapshot
    return True


def _autosave_test_source_perimeter(
    draft: dict,
    item: dict,
    source_code: str,
    perimeter_payload: dict | None,
    scope_key: str,
) -> bool:
    autosave_snapshot_key = f"{scope_key}_autosave_snapshot"
    current_snapshot = _serialize_perimeter_payload(perimeter_payload)
    if autosave_snapshot_key not in st.session_state:
        st.session_state[autosave_snapshot_key] = current_snapshot
        return False
    if st.session_state.get(autosave_snapshot_key) == current_snapshot:
        return False

    sources = item.get("sources")
    if isinstance(sources, list):
        for source in sources:
            if str(source.get("sourceCode") or "").strip() == source_code:
                source["perimeter"] = perimeter_payload
                break

    suite_id = str(draft.get("id") or "").strip()
    if suite_id:
        try:
            payload = draft_to_test_suite_payload(draft)
            payload["id"] = suite_id
            update_test_suite(payload)
            fresh = get_test_suite_by_id(suite_id)
            st.session_state[TEST_SUITE_DRAFT_KEY] = build_test_suite_draft(fresh)
        except Exception as exc:
            st.error(f"Errore autosalvataggio perimetro source: {str(exc)}")
            return False

    st.session_state[autosave_snapshot_key] = current_snapshot
    st.session_state.pop(TEST_SOURCE_PERIMETER_PREVIEW_CACHE_KEY, None)
    return True


def _render_back_button():
    mode = get_database_datasource_perimeter_editor_mode()
    if mode == "test_source":
        return_page, return_label = get_database_datasource_perimeter_return_target()
        back_label = return_label or "Back"
        target_page = return_page or DATASETS_PAGE_PATH
    else:
        back_label = "Back to datasets"
        target_page = DATASETS_PAGE_PATH

    back_cols = st.columns([2, 8], gap="small", vertical_alignment="center")
    with back_cols[0]:
        if st.button(
            back_label,
            key="dataset_perimeter_back_btn",
            icon=":material/arrow_back:",
            use_container_width=True,
        ):
            clear_database_datasource_perimeter_edit_id()
            st.switch_page(target_page)


def _find_test_source_in_draft(
    draft: dict,
    item_ui_key: str,
    source_code: str,
) -> tuple[dict | None, dict | None]:
    item = find_draft_test_by_ui_key(draft, item_ui_key)
    if not isinstance(item, dict):
        return None, None
    for source in item.get("sources") or []:
        if str(source.get("sourceCode") or "").strip() == source_code:
            return item, source
    return item, None


def _render_global_datasource_perimeter_editor():
    datasources = load_database_datasources(force=False)
    connections = load_database_connections(force=False)
    datasource_id = get_database_datasource_perimeter_edit_id()
    datasource_item = next(
        (
            item
            for item in datasources
            if isinstance(item, dict) and str(item.get("id") or "").strip() == str(datasource_id or "").strip()
        ),
        None,
    )

    if not datasource_item:
        st.info("Seleziona un dataset dalla pagina Datasets.")
        return

    connection_labels = {
        str(item.get("id")): build_connection_label(item)
        for item in connections
        if item.get("id")
    }
    summary = build_dataset_summary(datasource_item, connection_labels)
    payload = datasource_item.get("payload") if isinstance(datasource_item.get("payload"), dict) else {}
    perimeter = datasource_item.get("perimeter") if isinstance(datasource_item.get("perimeter"), dict) else None

    st.subheader(f"Dataset perimeter: {summary['description']}")

    connection_id = str(payload.get("connection_id") or "").strip()
    object_name = str(payload.get("object_name") or "").strip()
    object_type = str(payload.get("object_type") or "table").strip().lower() or "table"
    schema = payload.get("schema")

    available_columns, columns_error = _load_object_columns(
        connection_id,
        object_name,
        object_type,
        schema,
    )
    scope_key = build_perimeter_scope_key(
        "dataset_perimeter",
        str(datasource_id or ""),
        connection_id,
        schema,
        object_type,
        object_name,
    )

    if columns_error:
        st.error(f"Errore caricamento colonne: {columns_error}")
        return
    if not available_columns:
        st.info("Seleziona una tabella o view valida per configurare il perimetro.")
        return

    selected_columns_tab, parameters_tab, filters_tab, sort_tab = st.tabs(
        ["📋 Selected columns", "🧩 Parameters", "🔎 Filters", "↕️ Sort"]
    )
    with selected_columns_tab:
        selected_columns = _render_selected_columns_editor(scope_key, available_columns, perimeter)
    with parameters_tab:
        parameter_rows = _render_parameters_editor(scope_key, perimeter)
        st.caption("Use parameters to bind dataset filters at runtime with None, Literal or Function defaults.")
    available_parameter_names = _available_parameter_names(scope_key)
    with filters_tab:
        filter_logic, filter_items = _render_filters_editor(
            scope_key,
            available_columns,
            perimeter,
            available_parameter_names,
        )
    with sort_tab:
        sort_editor = _render_sort_editor(scope_key, available_columns, perimeter)

    perimeter_payload = build_perimeter_payload(
        selected_columns,
        filter_logic,
        filter_items,
        sort_editor,
    )
    perimeter_payload = build_perimeter_payload(
        selected_columns,
        parameter_rows,
        filter_logic,
        filter_items,
        sort_editor,
    )
    _autosave_perimeter(
        str(datasource_id),
        datasource_item,
        payload,
        perimeter_payload,
        scope_key,
    )

    st.divider()
    preview_clicked = _render_preview_header(
        save_disabled=not bool(datasource_id and connection_id and object_name),
        save_button_key=f"{scope_key}_refresh_preview_btn",
    )
    _render_preview_content(str(datasource_id), force=preview_clicked)


def _render_test_source_perimeter_editor():
    item_ui_key, source_code = get_test_source_perimeter_target()
    if not item_ui_key or not source_code:
        st.info("Nessun source selezionato.")
        return

    draft = st.session_state.get(TEST_SUITE_DRAFT_KEY)
    if not isinstance(draft, dict) or not str(draft.get("id") or "").strip():
        st.info("Nessuna suite selezionata.")
        return

    load_test_editor_context(force=False)
    datasources = load_database_datasources(force=False)
    connections = load_database_connections(force=False)

    item, source = _find_test_source_in_draft(draft, item_ui_key, source_code)
    if not isinstance(source, dict):
        st.info("Source non trovato nella suite corrente.")
        return

    dataset_id = str(source.get("datasetId") or "").strip()
    datasource_item = next(
        (
            ds
            for ds in datasources
            if isinstance(ds, dict) and str(ds.get("id") or "").strip() == dataset_id
        ),
        None,
    )
    if not datasource_item:
        st.info("Dataset di riferimento non trovato.")
        return

    connection_labels = {
        str(c.get("id")): build_connection_label(c)
        for c in connections
        if c.get("id")
    }
    summary = build_dataset_summary(datasource_item, connection_labels)
    ds_payload = datasource_item.get("payload") if isinstance(datasource_item.get("payload"), dict) else {}
    perimeter = source.get("perimeter") if isinstance(source.get("perimeter"), dict) else None

    st.subheader(f"Source perimeter: {source_code} ({summary['description']})")

    connection_id = str(ds_payload.get("connection_id") or "").strip()
    object_name = str(ds_payload.get("object_name") or "").strip()
    object_type = str(ds_payload.get("object_type") or "table").strip().lower() or "table"
    schema = ds_payload.get("schema")

    available_columns, columns_error = _load_object_columns(
        connection_id,
        object_name,
        object_type,
        schema,
    )
    scope_key = build_perimeter_scope_key(
        "test_source_perimeter",
        f"{item_ui_key}_{source_code}",
        connection_id,
        schema,
        object_type,
        object_name,
    )

    if columns_error:
        st.error(f"Errore caricamento colonne: {columns_error}")
        return
    if not available_columns:
        st.info("Seleziona una tabella o view valida per configurare il perimetro.")
        return

    selected_columns_tab, parameters_tab, filters_tab, sort_tab = st.tabs(
        ["📋 Selected columns", "🧩 Parameters", "🔎 Filters", "↕️ Sort"]
    )
    with selected_columns_tab:
        selected_columns = _render_selected_columns_editor(scope_key, available_columns, perimeter)
    with parameters_tab:
        parameter_rows = _render_parameters_editor(scope_key, perimeter)
        st.caption("Use parameters to bind dataset filters at runtime with None, Literal or Function defaults.")
    available_parameter_names = _available_parameter_names(scope_key)
    with filters_tab:
        filter_logic, filter_items = _render_filters_editor(
            scope_key,
            available_columns,
            perimeter,
            available_parameter_names,
        )
    with sort_tab:
        sort_editor = _render_sort_editor(scope_key, available_columns, perimeter)

    perimeter_payload = build_perimeter_payload(
        selected_columns,
        parameter_rows,
        filter_logic,
        filter_items,
        sort_editor,
    )
    _autosave_test_source_perimeter(
        draft,
        item,
        source_code,
        perimeter_payload,
        scope_key,
    )

    st.divider()
    preview_clicked = _render_preview_header(
        save_disabled=not bool(connection_id and object_name),
        save_button_key=f"{scope_key}_refresh_preview_btn",
    )
    preview_source = {
        **source,
        "perimeter": perimeter_payload,
    }
    _render_test_source_preview_content(preview_source, force=preview_clicked)


def render_dataset_perimeter_editor_container():
    _show_feedback()
    _render_back_button()

    mode = get_database_datasource_perimeter_editor_mode()
    if mode == "test_source":
        _render_test_source_perimeter_editor()
    else:
        _render_global_datasource_perimeter_editor()
