import streamlit as st

from elaborations_shared.services.data_loader_service import load_test_editor_context
from test_suites.components import suite_editor_component as shared
from test_suites.services.api_service import (
    create_test_suite,
    delete_test_suite_by_id,
    execute_test_suite_by_id,
    get_all_test_suites,
    get_test_suite_by_id,
    update_test_suite,
)
from test_suites.services.draft_mapper import (
    build_test_suite_draft,
    draft_to_test_suite_payload,
)
from test_suites.services.execution_stream_service import (
    get_execution_state,
    register_execution_listener,
)
from test_suites.services.navigation_service import (
    apply_test_suites_query_params,
    sync_test_suites_query_params,
)
from test_suites.services.state_keys import (
    ADVANCED_SUITE_EDITOR_PAGE_PATH,
    ADVANCED_SUITE_EDITOR_RETURN_LABEL_KEY,
    ADVANCED_SUITE_EDITOR_RETURN_PAGE_KEY,
    SELECTED_TEST_POSITION_KEY,
    SELECTED_TEST_SUITE_ID_KEY,
    TEST_EDITOR_PAGE_PATH,
    TEST_SUITES_KEY,
    TEST_SUITES_PAGE_PATH,
    TEST_SUITE_DRAFT_KEY,
    TEST_SUITE_LAST_EXECUTION_ID_KEY,
)


def _load_test_suites(force: bool = False) -> list[dict]:
    if force or TEST_SUITES_KEY not in st.session_state:
        st.session_state[TEST_SUITES_KEY] = get_all_test_suites()
    suites = st.session_state.get(TEST_SUITES_KEY, [])
    return suites if isinstance(suites, list) else []


def _select_test_suite(
    suite_id: str | None,
    *,
    clear_draft: bool = True,
    clear_test_position: bool = True,
    clear_execution_state: bool = True,
):
    st.session_state[SELECTED_TEST_SUITE_ID_KEY] = suite_id or None
    if clear_draft:
        st.session_state.pop(TEST_SUITE_DRAFT_KEY, None)
    if clear_test_position:
        st.session_state.pop(SELECTED_TEST_POSITION_KEY, None)
    if clear_execution_state:
        st.session_state.pop(TEST_SUITE_LAST_EXECUTION_ID_KEY, None)
        st.session_state.pop(shared.SELECTED_TEST_SUITE_EXECUTION_ID_KEY, None)
        st.session_state.pop(shared.PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY, None)
    selected_test_position = (
        st.session_state.get(SELECTED_TEST_POSITION_KEY)
        if not clear_test_position
        else None
    )
    sync_test_suites_query_params(suite_id, selected_test_position)


def _open_advanced_settings():
    st.session_state[ADVANCED_SUITE_EDITOR_RETURN_PAGE_KEY] = TEST_SUITES_PAGE_PATH
    st.session_state[ADVANCED_SUITE_EDITOR_RETURN_LABEL_KEY] = "Back to test suites"
    st.switch_page(ADVANCED_SUITE_EDITOR_PAGE_PATH)


def _clear_selected_suite_state(suite_id: str | None = None):
    selected_suite_id = str(st.session_state.get(SELECTED_TEST_SUITE_ID_KEY) or "").strip()
    target_suite_id = str(suite_id or "").strip()
    if not target_suite_id or selected_suite_id == target_suite_id:
        _select_test_suite(None)


def _find_suite_item(suite_id: str) -> dict | None:
    suites = st.session_state.get(TEST_SUITES_KEY) or []
    if not isinstance(suites, list):
        return None
    target = str(suite_id or "").strip()
    for suite in suites:
        if str(suite.get("id") or "").strip() == target:
            return suite
    return None


@st.dialog("New test suite", width="medium")
def _create_test_suite_dialog():
    dialog_suffix = "test_suite_create"
    st.text_input("Description", key=f"{dialog_suffix}_description")

    action_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"{dialog_suffix}_save",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            description = str(st.session_state.get(f"{dialog_suffix}_description") or "")
            if not description.strip():
                st.error("Description is required.")
                return
            try:
                response = create_test_suite(
                    {
                        "description": description,
                        "hooks": [],
                        "tests": [],
                    }
                )
            except Exception as exc:
                st.error(f"Error creating test suite: {str(exc)}")
                return

            created_id = str((response or {}).get("id") or "").strip()
            if not created_id:
                st.error("Error creating test suite: id not returned.")
                return

            _load_test_suites(force=True)
            _select_test_suite(created_id)
            st.session_state[shared.TEST_SUITE_FEEDBACK_KEY] = (
                response.get("message") or "Test suite created."
            )
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Cancel",
            key=f"{dialog_suffix}_cancel",
            use_container_width=True,
        ):
            st.rerun()


@st.dialog("Test suite actions", width="medium")
def _edit_test_suite_dialog(suite_item: dict):
    suite_id = str(suite_item.get("id") or "").strip()
    if not suite_id:
        st.error("Invalid test suite.")
        return

    dialog_suffix = f"test_suite_actions_{suite_id}"
    st.text_input(
        "Description",
        key=f"{dialog_suffix}_description",
        value=str(suite_item.get("description") or ""),
    )

    action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"{dialog_suffix}_save",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            description = str(st.session_state.get(f"{dialog_suffix}_description") or "")
            if not description.strip():
                st.error("Description is required.")
                return
            try:
                suite_detail = get_test_suite_by_id(suite_id)
                draft = build_test_suite_draft(suite_detail)
                draft["id"] = suite_id
                draft["description"] = description
                payload = draft_to_test_suite_payload(draft)
                payload["id"] = suite_id
                response = update_test_suite(payload)
            except Exception as exc:
                st.error(f"Error updating test suite: {str(exc)}")
                return

            _load_test_suites(force=True)
            _select_test_suite(
                suite_id,
                clear_draft=True,
                clear_test_position=False,
                clear_execution_state=False,
            )
            st.session_state[shared.TEST_SUITE_FEEDBACK_KEY] = (
                response.get("message") or "Test suite updated."
            )
            st.rerun()
    with action_cols[1]:
        if st.button(
            "Delete",
            key=f"{dialog_suffix}_delete",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            try:
                response = delete_test_suite_by_id(suite_id)
            except Exception as exc:
                st.error(f"Error deleting test suite: {str(exc)}")
                return

            _clear_selected_suite_state(suite_id)
            _load_test_suites(force=True)
            st.session_state[shared.TEST_SUITE_FEEDBACK_KEY] = (
                response.get("message") or "Test suite deleted."
            )
            st.rerun()
    with action_cols[2]:
        if st.button(
            "Cancel",
            key=f"{dialog_suffix}_cancel",
            use_container_width=True,
        ):
            st.rerun()


def _render_suite_selector_list(suites: list[dict], selected_suite_id: str):
    if not suites:
        st.info("No test suites configured.")
    else:
        with st.container(border=True):
            for idx, suite in enumerate(suites, start=1):
                suite_id = str(suite.get("id") or "").strip()
                description = str(suite.get("description") or "").strip() or "No description"
                is_selected = suite_id == selected_suite_id

                if st.button(
                    description,
                    key=f"select_test_suite_{suite_id or idx}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True,
                ):
                    _select_test_suite(suite_id)
                    st.rerun()
    if st.button(
        "Add new suite",
        key="test_suite_add_btn",
        icon=":material/add:",
        type="tertiary",
        use_container_width=True,
    ):
        _create_test_suite_dialog()


def _execution_status_icon(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in {"success", "finished", "completed"}:
        return ":material/check_circle:"
    if normalized == "error":
        return ":material/error:"
    if normalized == "running":
        return ":material/sync:"
    return ""


def _selected_execution_caption(executions: list[dict]) -> str:
    selected = shared._find_selected_execution(executions)
    if not selected:
        return ""
    return shared._format_execution_label(selected)


def _selected_execution_status(executions: list[dict]) -> str:
    selected = shared._find_selected_execution(executions)
    if not selected:
        return ""
    return str(selected.get("status") or "").strip()


def _get_execution_item_status(executions: list[dict]) -> dict[str, str]:
    selected = shared._find_selected_execution(executions)
    if not selected:
        return {}
    execution_id = str(selected.get("id") or "").strip()
    if not execution_id:
        return {}
    # Try live stream state first
    state = get_execution_state(execution_id)
    item_status = state.get("item_status") or {}
    if item_status:
        return item_status
    # Fall back to persisted item executions from API response
    items = selected.get("items") or []
    if items:
        return {
            str(item.get("suite_item_id") or ""): str(item.get("status") or "")
            for item in items
            if item.get("suite_item_id")
        }
    return {}


@st.dialog("Execution history", width="large")
def _execution_history_dialog(executions: list[dict]):
    if not executions:
        st.info("No executions available.")
        if st.button("Close", key="exec_history_close_empty", use_container_width=True):
            st.rerun()
        return

    header_cols = st.columns([3, 3, 2, 2], gap="small")
    with header_cols[0]:
        st.markdown("**Started at**")
    with header_cols[1]:
        st.markdown("**Status**")
    with header_cols[2]:
        st.markdown("**Item**")
    with header_cols[3]:
        st.markdown("**Select**")

    selected_execution_id = str(
        st.session_state.get(shared.SELECTED_TEST_SUITE_EXECUTION_ID_KEY) or ""
    ).strip()

    for exec_item in executions:
        exec_id = str(exec_item.get("id") or "").strip()
        started_at = str(exec_item.get("started_at") or "-")
        status = str(exec_item.get("status") or "-")
        requested_item = str(
            exec_item.get("requested_test_id")
            or exec_item.get("test_suite_description")
            or "-"
        )
        is_selected = exec_id == selected_execution_id

        row_cols = st.columns([3, 3, 2, 2], gap="small", vertical_alignment="center")
        with row_cols[0]:
            st.caption(started_at)
        with row_cols[1]:
            st.caption(status)
        with row_cols[2]:
            st.caption(requested_item)
        with row_cols[3]:
            if st.button(
                "Selected" if is_selected else "Select",
                key=f"exec_history_select_{exec_id}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
                disabled=is_selected,
            ):
                st.session_state[shared.SELECTED_TEST_SUITE_EXECUTION_ID_KEY] = exec_id
                st.rerun()


@st.dialog("Test actions", width="medium")
def _edit_test_dialog(test_item: dict):
    test_ui_key = str(test_item.get("_ui_key") or "").strip()
    if not test_ui_key:
        st.error("Invalid test.")
        return

    dialog_suffix = f"test_actions_{test_ui_key}"
    st.text_input(
        "Description",
        key=f"{dialog_suffix}_description",
        value=str(test_item.get("description") or ""),
    )

    action_cols = st.columns([1, 1, 1], gap="small", vertical_alignment="center")
    with action_cols[0]:
        if st.button(
            "Save",
            key=f"{dialog_suffix}_save",
            icon=":material/save:",
            type="secondary",
            use_container_width=True,
        ):
            description = str(st.session_state.get(f"{dialog_suffix}_description") or "").strip()
            draft = st.session_state.get(TEST_SUITE_DRAFT_KEY, {})
            if isinstance(draft, dict):
                test_ref = shared._find_test_by_ui_key(draft, test_ui_key)
                if test_ref:
                    test_ref["description"] = description
                    st.session_state[shared.TEST_SUITE_FEEDBACK_KEY] = "Test updated."
                    shared._persist_changes()
                else:
                    st.error("Test not found.")
            else:
                st.error("Draft not available.")
    with action_cols[1]:
        if st.button(
            "Delete",
            key=f"{dialog_suffix}_delete",
            icon=":material/delete:",
            type="secondary",
            use_container_width=True,
        ):
            draft = st.session_state.get(TEST_SUITE_DRAFT_KEY, {})
            if isinstance(draft, dict):
                shared._delete_test_by_ui_key(draft, test_ui_key)
            else:
                st.error("Draft not available.")
    with action_cols[2]:
        if st.button(
            "Cancel",
            key=f"{dialog_suffix}_cancel",
            use_container_width=True,
        ):
            st.rerun()


def _render_test_item_card(test: dict, index: int, item_status: dict[str, str]):
    current_test = shared._ensure_test_item(test, index)
    with st.container(border=False):
        test_label = shared._test_label(current_test, index)
        operations = current_test.get("operations") or []
        test_id = str(current_test.get("id") or "").strip()
        test_status = str(item_status.get(test_id) or "").strip()
        test_icon = _execution_status_icon(test_status)

        header_cols = st.columns([1, 14, 1, 1, 1] if test_icon else [15, 1, 1, 1], gap="small", vertical_alignment="center")
        col_offset = 0
        if test_icon:
            with header_cols[0]:
                st.markdown(test_icon)
            col_offset = 1
        with header_cols[col_offset]:
            st.markdown(f"**{test_label}**")
        with header_cols[col_offset + 1]:
            if st.button(
                "",
                key=f"test_suite_open_test_editor_{current_test.get('_ui_key')}",
                icon=":material/list:",
                help="Open test editor",
                type="secondary",
                use_container_width=True,
            ):
                st.session_state[SELECTED_TEST_POSITION_KEY] = shared._test_position(current_test, index)
                st.switch_page(TEST_EDITOR_PAGE_PATH)
        with header_cols[col_offset + 2]:
            if st.button(
                "",
                key=f"test_suite_test_actions_{current_test.get('_ui_key')}",
                icon=":material/more_vert:",
                help="Edit / Delete test",
                type="secondary",
                use_container_width=True,
            ):
                _edit_test_dialog(current_test)

        if operations:
            for op_idx, operation in enumerate(operations):
                shared._render_suite_command_card(
                    operation,
                    key_prefix=f"test_suite_cmd_{current_test.get('_ui_key')}_{op_idx}",
                )
        else:
            st.caption("Nessun command configurato.")


def _render_suite_detail_panel(selected_suite_id: str):
    draft = shared._resolve_editor_draft(selected_suite_id)
    suite_description = str(draft.get("description") or "").strip() or "Test suite"

    executions = shared._load_execution_history(selected_suite_id)
    suite_status = _selected_execution_status(executions)
    suite_icon = _execution_status_icon(suite_status)
    item_status = _get_execution_item_status(executions)

    header_cols = st.columns(
        [1, 8, 2, 2, 2, 2, 2] if suite_icon else [8, 2, 2, 2, 2, 2],
        gap="small",
        vertical_alignment="center",
    )
    col_offset = 0
    if suite_icon:
        with header_cols[0]:
            st.markdown(suite_icon)
        col_offset = 1

    with header_cols[col_offset]:
        st.markdown(f"##### {suite_description}")

    with header_cols[col_offset + 1]:
        if st.button(
            "",
            help="Add new test",
            key="suite_panel_add_test",
            icon=":material/add:",
            type="secondary",
            use_container_width=True,
        ):
            shared._open_add_test_dialog()
            st.rerun()

    with header_cols[col_offset + 2]:
        if st.button(
            "",
            help="Execution history",
            key="suite_panel_execution_history",
            icon=":material/today:",
            type="secondary",
            use_container_width=True,
        ):
            _execution_history_dialog(executions)

    with header_cols[col_offset + 3]:
        if st.button(
            "",
            help="Advanced settings",
            key="suite_panel_advanced_settings",
            icon=":material/settings:",
            type="secondary",
            use_container_width=True,
        ):
            _open_advanced_settings()

    with header_cols[col_offset + 4]:
        suite_item = _find_suite_item(selected_suite_id)
        if st.button(
            "",
            help="Edit / Delete suite",
            key="suite_panel_actions",
            icon=":material/more_vert:",
            type="secondary",
            use_container_width=True,
        ):
            if suite_item:
                _edit_test_suite_dialog(suite_item)

    with header_cols[col_offset + 5]:
        if st.button(
            "",
            help="Run test suite",
            key="run_suite",
            icon=":material/play_arrow:",
            type="primary",
            use_container_width=True,
        ):
            response = execute_test_suite_by_id(selected_suite_id)
            execution_id = str(response.get("execution_id") or "").strip()
            if execution_id:
                st.session_state[TEST_SUITE_LAST_EXECUTION_ID_KEY] = execution_id
                st.session_state[shared.PENDING_TEST_SUITE_EXECUTION_SELECTION_KEY] = execution_id
                register_execution_listener(execution_id, selected_suite_id)
                st.rerun()

    execution_caption = _selected_execution_caption(executions)
    if execution_caption:
        st.caption(execution_caption)

    tests = draft.get("tests") or []
    if tests:
        for index, test in enumerate(tests, start=1):
            st.divider()
            _render_test_item_card(test, index, item_status)
    else:
        st.caption("Nessun test configurato.")

    if bool(st.session_state.get(shared.ADD_TEST_DIALOG_OPEN_KEY, False)):
        shared._render_add_test_dialog(draft)


def render_test_suites_page():
    load_test_editor_context(force=False)

    suites = _load_test_suites(force=False)
    apply_test_suites_query_params(suites)
    selected_suite_id = shared._ensure_selected_suite_id(suites) if suites else ""

    shared._render_command_feedback()

    layout_cols = st.columns([4, 7], gap="small")
    with layout_cols[0]:
        _render_suite_selector_list(suites, selected_suite_id)
    with layout_cols[1]:
        if not suites:
            with st.container(border=True):
                st.markdown("#### Suite")
                st.info("Create a test suite to configure tests and commands.")
        elif not selected_suite_id:
            with st.container(border=True):
                st.markdown("#### Suite")
                st.info("Select a test suite from the list.")
        else:
            with st.container(border=True):
                _render_suite_detail_panel(selected_suite_id)

    if selected_suite_id:
        draft = shared._resolve_editor_draft(selected_suite_id)
        if shared._consume_add_source_dialog_request():
            shared._render_add_source_dialog(draft)
