import streamlit as st

from database_datasources.services.state_keys import (
    DATABASE_DATASOURCE_FEEDBACK_KEY,
    DATABASE_DATASOURCE_FEEDBACK_LEVEL_KEY,
    DATABASE_DATASOURCE_OPEN_IDS_KEY,
    DATABASE_DATASOURCE_PERIMETER_EDIT_ID_KEY,
    DATABASE_DATASOURCE_PERIMETER_EDITOR_MODE_KEY,
    DATABASE_DATASOURCE_PERIMETER_RETURN_LABEL_KEY,
    DATABASE_DATASOURCE_PERIMETER_RETURN_PAGE_KEY,
    DATABASE_DATASOURCE_PERIMETER_SOURCE_CODE_KEY,
    DATABASE_DATASOURCE_PERIMETER_SOURCE_ITEM_UI_KEY,
    DATABASE_DATASOURCE_PREVIEW_VISIBLE_ID_KEY,
    SELECTED_DATABASE_DATASOURCE_ID_KEY,
)


def _normalize_open_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def get_selected_database_datasource_id() -> str | None:
    value = str(st.session_state.get(SELECTED_DATABASE_DATASOURCE_ID_KEY) or "").strip()
    return value or None


def set_selected_database_datasource_id(datasource_id: str | None):
    normalized = str(datasource_id or "").strip()
    st.session_state[SELECTED_DATABASE_DATASOURCE_ID_KEY] = normalized or None


def ensure_selected_database_datasource_id(datasources: list[dict]) -> str | None:
    datasource_ids = [str(item.get("id")) for item in datasources if item.get("id")]
    selected_id = get_selected_database_datasource_id()
    if not datasource_ids:
        set_selected_database_datasource_id(None)
        return None
    if not selected_id or selected_id not in datasource_ids:
        set_selected_database_datasource_id(datasource_ids[0])
        return datasource_ids[0]
    return selected_id


def mark_database_datasource_open(datasource_id: str | None, is_open: bool = True):
    normalized = str(datasource_id or "").strip()
    open_ids = _normalize_open_ids(st.session_state.get(DATABASE_DATASOURCE_OPEN_IDS_KEY))
    if not normalized:
        st.session_state[DATABASE_DATASOURCE_OPEN_IDS_KEY] = open_ids
        return
    if is_open and normalized not in open_ids:
        open_ids.append(normalized)
    if not is_open:
        open_ids = [item for item in open_ids if item != normalized]
    st.session_state[DATABASE_DATASOURCE_OPEN_IDS_KEY] = open_ids


def is_database_datasource_open(datasource_id: str | None) -> bool:
    normalized = str(datasource_id or "").strip()
    open_ids = _normalize_open_ids(st.session_state.get(DATABASE_DATASOURCE_OPEN_IDS_KEY))
    return bool(normalized and normalized in open_ids)


def toggle_database_datasource_preview(datasource_id: str | None) -> bool:
    normalized = str(datasource_id or "").strip()
    if not normalized:
        st.session_state[DATABASE_DATASOURCE_PREVIEW_VISIBLE_ID_KEY] = None
        return False

    current = str(st.session_state.get(DATABASE_DATASOURCE_PREVIEW_VISIBLE_ID_KEY) or "").strip()
    if current == normalized:
        st.session_state[DATABASE_DATASOURCE_PREVIEW_VISIBLE_ID_KEY] = None
        mark_database_datasource_open(normalized, is_open=False)
        return False

    st.session_state[DATABASE_DATASOURCE_PREVIEW_VISIBLE_ID_KEY] = normalized
    set_selected_database_datasource_id(normalized)
    mark_database_datasource_open(normalized, is_open=True)
    return True


def is_database_datasource_preview_visible(datasource_id: str | None) -> bool:
    normalized = str(datasource_id or "").strip()
    current = str(st.session_state.get(DATABASE_DATASOURCE_PREVIEW_VISIBLE_ID_KEY) or "").strip()
    return bool(normalized and normalized == current)


def set_database_datasource_perimeter_edit_id(datasource_id: str | None):
    normalized = str(datasource_id or "").strip()
    st.session_state[DATABASE_DATASOURCE_PERIMETER_EDIT_ID_KEY] = normalized or None
    st.session_state[DATABASE_DATASOURCE_PERIMETER_EDITOR_MODE_KEY] = "global_datasource"
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_SOURCE_ITEM_UI_KEY, None)
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_SOURCE_CODE_KEY, None)
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_RETURN_PAGE_KEY, None)
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_RETURN_LABEL_KEY, None)
    if normalized:
        set_selected_database_datasource_id(normalized)
        mark_database_datasource_open(normalized, is_open=True)


def get_database_datasource_perimeter_edit_id() -> str | None:
    value = str(st.session_state.get(DATABASE_DATASOURCE_PERIMETER_EDIT_ID_KEY) or "").strip()
    return value or None


def clear_database_datasource_perimeter_edit_id():
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_EDIT_ID_KEY, None)
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_EDITOR_MODE_KEY, None)
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_SOURCE_ITEM_UI_KEY, None)
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_SOURCE_CODE_KEY, None)
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_RETURN_PAGE_KEY, None)
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_RETURN_LABEL_KEY, None)


def open_test_source_perimeter_editor(
    *,
    item_ui_key: str,
    source_code: str,
    return_page: str,
    return_label: str,
):
    st.session_state[DATABASE_DATASOURCE_PERIMETER_EDITOR_MODE_KEY] = "test_source"
    st.session_state[DATABASE_DATASOURCE_PERIMETER_SOURCE_ITEM_UI_KEY] = str(item_ui_key or "").strip() or None
    st.session_state[DATABASE_DATASOURCE_PERIMETER_SOURCE_CODE_KEY] = str(source_code or "").strip() or None
    st.session_state[DATABASE_DATASOURCE_PERIMETER_RETURN_PAGE_KEY] = str(return_page or "").strip() or None
    st.session_state[DATABASE_DATASOURCE_PERIMETER_RETURN_LABEL_KEY] = str(return_label or "").strip() or None
    st.session_state.pop(DATABASE_DATASOURCE_PERIMETER_EDIT_ID_KEY, None)


def get_database_datasource_perimeter_editor_mode() -> str:
    return str(st.session_state.get(DATABASE_DATASOURCE_PERIMETER_EDITOR_MODE_KEY) or "global_datasource").strip()


def get_test_source_perimeter_target() -> tuple[str | None, str | None]:
    item_ui_key = str(st.session_state.get(DATABASE_DATASOURCE_PERIMETER_SOURCE_ITEM_UI_KEY) or "").strip()
    source_code = str(st.session_state.get(DATABASE_DATASOURCE_PERIMETER_SOURCE_CODE_KEY) or "").strip()
    return item_ui_key or None, source_code or None


def get_database_datasource_perimeter_return_target() -> tuple[str | None, str | None]:
    return_page = str(st.session_state.get(DATABASE_DATASOURCE_PERIMETER_RETURN_PAGE_KEY) or "").strip()
    return_label = str(st.session_state.get(DATABASE_DATASOURCE_PERIMETER_RETURN_LABEL_KEY) or "").strip()
    return return_page or None, return_label or None


def set_database_datasource_feedback(message: str, level: str = "success"):
    normalized_message = str(message or "").strip()
    if not normalized_message:
        st.session_state.pop(DATABASE_DATASOURCE_FEEDBACK_KEY, None)
        st.session_state.pop(DATABASE_DATASOURCE_FEEDBACK_LEVEL_KEY, None)
        return
    st.session_state[DATABASE_DATASOURCE_FEEDBACK_KEY] = normalized_message
    st.session_state[DATABASE_DATASOURCE_FEEDBACK_LEVEL_KEY] = str(level or "info").strip().lower()


def pop_database_datasource_feedback() -> tuple[str | None, str]:
    message = str(st.session_state.pop(DATABASE_DATASOURCE_FEEDBACK_KEY, "") or "").strip()
    level = str(st.session_state.pop(DATABASE_DATASOURCE_FEEDBACK_LEVEL_KEY, "info") or "info").strip().lower()
    return (message or None, level or "info")


def clear_database_datasource_selection_if_matches(datasource_id: str | None):
    normalized = str(datasource_id or "").strip()
    if normalized and get_selected_database_datasource_id() == normalized:
        set_selected_database_datasource_id(None)
    if normalized and is_database_datasource_preview_visible(normalized):
        st.session_state[DATABASE_DATASOURCE_PREVIEW_VISIBLE_ID_KEY] = None
    mark_database_datasource_open(normalized, is_open=False)
    if normalized and get_database_datasource_perimeter_edit_id() == normalized:
        clear_database_datasource_perimeter_edit_id()
