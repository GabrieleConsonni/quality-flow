import streamlit as st

from elaborations_shared.services.data_loader_service import load_test_editor_context
from test_suites.components import suite_editor_component as shared
from test_suites.services.state_keys import (
    ADVANCED_SUITE_EDITOR_RETURN_LABEL_KEY,
    ADVANCED_SUITE_EDITOR_RETURN_PAGE_KEY,
    TEST_SUITES_PAGE_PATH,
)

HOOK_SECTIONS = [
    ("before-all", ":material/first_page: Before all"),
    ("before-each", ":material/skip_next: Before each test"),
    ("after-each", ":material/task_alt: After each test"),
    ("after-all", ":material/last_page: After all"),
]
ADVANCED_SUITE_EDITOR_SELECTED_HOOK_KEY = "advanced_suite_editor_selected_hook"


def _go_back():
    return_page = str(st.session_state.get(ADVANCED_SUITE_EDITOR_RETURN_PAGE_KEY) or TEST_SUITES_PAGE_PATH).strip()
    st.session_state.pop(ADVANCED_SUITE_EDITOR_RETURN_PAGE_KEY, None)
    st.session_state.pop(ADVANCED_SUITE_EDITOR_RETURN_LABEL_KEY, None)
    st.switch_page(return_page or TEST_SUITES_PAGE_PATH)


def render_advanced_suite_editor_settings_container():
    load_test_editor_context(force=False)

    suites = shared._load_test_suites(force=False)
    if not suites:
        st.info("No test suites configured.")
        return

    selected_suite_id = shared._ensure_selected_suite_id(suites)
    if not selected_suite_id:
        st.info("Select a test suite from the suites page.")
        return

    draft = shared._resolve_editor_draft(selected_suite_id)
    back_label = str(st.session_state.get(ADVANCED_SUITE_EDITOR_RETURN_LABEL_KEY) or "Back to suite").strip()

    if st.button(
        back_label,
        key="advanced_suite_editor_back_btn",
        icon=":material/arrow_back:",
        type="secondary",
    ):
        _go_back()

    hook_options = [section_title for _, section_title in HOOK_SECTIONS]
    selected_hook_label = shared._select_persisted_tab(
        hook_options,
        ADVANCED_SUITE_EDITOR_SELECTED_HOOK_KEY,
        default=hook_options[0] if hook_options else "",
    )
    selected_hook = next(
        (
            (hook_phase, section_title)
            for hook_phase, section_title in HOOK_SECTIONS
            if section_title == selected_hook_label
        ),
        HOOK_SECTIONS[0] if HOOK_SECTIONS else ("before-all", "Before all"),
    )
    shared._render_command_feedback()
    st.divider()
    shared._render_hook_section(draft, selected_hook[0], selected_hook[1], {})

    if shared._consume_add_operation_dialog_request():
        shared._render_add_operation_dialog(draft)

    if shared._consume_add_source_dialog_request():
        shared._render_add_source_dialog(draft)

    if shared._consume_hook_command_dialog_request():
        shared._render_add_hook_command_dialog(draft)

    if shared._consume_edit_command_dialog_request():
        shared._render_edit_command_dialog(draft)

    if bool(st.session_state.get(shared.COMMAND_REORDER_DIALOG_OPEN_KEY, False)):
        shared._render_reorder_command_dialog(draft)
