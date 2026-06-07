from __future__ import annotations

import pandas as pd
import streamlit as st

from home.services.home_service import (
    HOME_FILTER_STARTED_FROM_DATE_KEY,
    HOME_FILTER_STARTED_FROM_ENABLED_KEY,
    HOME_FILTER_STARTED_FROM_TIME_KEY,
    HOME_FILTER_STARTED_TO_DATE_KEY,
    HOME_FILTER_STARTED_TO_ENABLED_KEY,
    HOME_FILTER_STARTED_TO_TIME_KEY,
    HOME_FILTER_STATUS_KEY,
    HOME_FILTER_TEST_SUITE_KEY,
    HOME_PAGE_NUMBER_KEY,
    HOME_PAGE_SIZE_KEY,
    HOME_TOTAL_PAGES_KEY,
    build_chart_rows,
    build_table_rows,
    ensure_home_state,
    normalize_search_result,
    read_home_filters,
    reset_page_number_on_filter_change,
)
from test_suites.services.api_service import (
    get_all_test_suites,
    search_test_suite_executions,
)


def _load_test_suite_filter_options() -> list[dict]:
    try:
        suites = get_all_test_suites()
    except Exception as exc:
        st.error(f"Error loading test suites: {str(exc)}")
        return []
    return suites if isinstance(suites, list) else []


def _render_filters(test_suites: list[dict]):
    status_options = ["", "success", "running", "error"]
    suite_options = [""] + [
        str(item.get("id") or "").strip()
        for item in test_suites
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    suite_labels = {
        str(item.get("id") or "").strip(): str(item.get("description") or item.get("id") or "").strip()
        for item in test_suites
        if isinstance(item, dict)
    }

    st.markdown("#### Filters")
    st.selectbox(
        "Status",
        options=status_options,
        key=HOME_FILTER_STATUS_KEY,
        format_func=lambda value: "All" if not value else value,
    )
    st.selectbox(
        "Test suite",
        options=suite_options,
        key=HOME_FILTER_TEST_SUITE_KEY,
        format_func=lambda value: "All" if not value else suite_labels.get(value, value),
    )
    st.checkbox("From", key=HOME_FILTER_STARTED_FROM_ENABLED_KEY)
    st.date_input(
        "From date",
        key=HOME_FILTER_STARTED_FROM_DATE_KEY,
        disabled=not bool(st.session_state.get(HOME_FILTER_STARTED_FROM_ENABLED_KEY)),
        label_visibility="collapsed",
    )
    st.time_input(
        "From time",
        key=HOME_FILTER_STARTED_FROM_TIME_KEY,
        disabled=not bool(st.session_state.get(HOME_FILTER_STARTED_FROM_ENABLED_KEY)),
        label_visibility="collapsed",
    )
    st.checkbox("To", key=HOME_FILTER_STARTED_TO_ENABLED_KEY)
    st.date_input(
        "To date",
        key=HOME_FILTER_STARTED_TO_DATE_KEY,
        disabled=not bool(st.session_state.get(HOME_FILTER_STARTED_TO_ENABLED_KEY)),
        label_visibility="collapsed",
    )
    st.time_input(
        "To time",
        key=HOME_FILTER_STARTED_TO_TIME_KEY,
        disabled=not bool(st.session_state.get(HOME_FILTER_STARTED_TO_ENABLED_KEY)),
        label_visibility="collapsed",
    )
    st.number_input(
        "Page size",
        min_value=1,
        max_value=100,
        key=HOME_PAGE_SIZE_KEY,
        step=1,
    )
    st.number_input(
        "Page number",
        min_value=1,
        max_value=max(
            int(st.session_state.get(HOME_TOTAL_PAGES_KEY) or 1),
            int(st.session_state.get(HOME_PAGE_NUMBER_KEY) or 1),
            1,
        ),
        key=HOME_PAGE_NUMBER_KEY,
        step=1,
    )


def _render_chart(executions: list[dict]):
    chart_rows = build_chart_rows(executions)
    st.markdown("#### Execution Duration")
    if not chart_rows:
        st.info("No executions available for the selected filters.")
        return

    chart_data = pd.DataFrame(chart_rows)
    st.vega_lite_chart(
        chart_data,
        {
            "mark": {"type": "bar", "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
            "encoding": {
                "x": {
                    "field": "started_at_label",
                    "type": "nominal",
                    "title": "Start at",
                    "sort": {"field": "started_at_sort", "order": "ascending"},
                    "axis": {"labelAngle": -35},
                },
                "y": {
                    "field": "duration_seconds",
                    "type": "quantitative",
                    "title": "Duration (s)",
                },
                "color": {
                    "field": "status",
                    "type": "nominal",
                    "title": "Status",
                    "scale": {
                        "domain": ["success", "running", "error"],
                        "range": ["#76A379", "#E4E0E0", "#E49393"],
                    },
                },
                "tooltip": [
                    {"field": "test_name", "type": "nominal", "title": "Test"},
                    {"field": "status", "type": "nominal", "title": "Status"},
                    {"field": "duration_label", "type": "nominal", "title": "Duration"},
                    {"field": "started_at", "type": "temporal", "title": "Started at"},
                    {"field": "finished_at", "type": "temporal", "title": "Finished at"},
                    {"field": "error_message", "type": "nominal", "title": "Error"},
                ],
            },
        },
        use_container_width=True,
    )


def _render_table(executions: list[dict], total: int, page_number: int, total_pages: int):
    st.markdown("#### Executions")
    st.caption(
        f"Showing {len(executions)} execution(s) on page {page_number}/{max(total_pages, 1)}. Total: {total}."
    )
    if not executions:
        st.info("No test suite executions available.")
        return

    rows = pd.DataFrame(build_table_rows(executions))
    st.dataframe(
        rows,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Open suite": st.column_config.LinkColumn(
                "Open suite",
                display_text="Apri suite",
            )
        },
    )


st.title("Home")
st.caption("Test suite executions overview.")

ensure_home_state(st.session_state)
initial_filters = read_home_filters(st.session_state)
reset_page_number_on_filter_change(st.session_state, initial_filters)
test_suite_options = _load_test_suite_filter_options()

columns = st.columns([3,15], gap="medium")
with columns[0]:
    _render_filters(test_suite_options)
    filters = read_home_filters(st.session_state)

    search_result = normalize_search_result(
        search_test_suite_executions(
            test_suite_id=filters["test_suite_id"] or None,
            status=filters["status"] or None,
            started_from=filters["started_from"],
            started_to=filters["started_to"],
            page_size=filters["page_size"],
            page_number=filters["page_number"],
        )
    )

    st.session_state[HOME_TOTAL_PAGES_KEY] = search_result["total_pages"]

with columns[1]:
    _render_chart(search_result["items"])
    _render_table(
        search_result["items"],
        total=search_result["total"],
        page_number=search_result["page_number"],
        total_pages=search_result["total_pages"],
    )
