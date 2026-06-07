from __future__ import annotations

import streamlit as st

from test_suites.services.api_service import get_test_suite_by_id
from test_suites.services.state_keys import (
    SELECTED_TEST_POSITION_KEY,
    SELECTED_TEST_SUITE_ID_KEY,
)


QUERY_PARAM_SUITE_ID = "suite_id"
QUERY_PARAM_TEST_POSITION = "test_position"
TEST_SUITES_NAV_SIGNATURE_KEY = "test_suites_nav_signature"


def _normalize_query_param(value: object) -> str:
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value or "").strip()


def _get_query_param(name: str) -> str:
    return _normalize_query_param(st.query_params.get(name))


def _set_query_param(name: str, value: str | None):
    normalized = str(value or "").strip()
    if normalized:
        st.query_params[name] = normalized
        return
    try:
        del st.query_params[name]
    except Exception:
        try:
            st.query_params.pop(name, None)
        except Exception:
            return


def coerce_test_position(value: object) -> int:
    try:
        position = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return position if position > 0 else 0


def build_navigation_signature(suite_id: str | None, test_position: int | None = None) -> str:
    normalized_suite_id = str(suite_id or "").strip()
    normalized_position = coerce_test_position(test_position)
    return f"{normalized_suite_id}|{normalized_position}"


def sync_test_suites_query_params(suite_id: str | None, test_position: int | None = None):
    normalized_suite_id = str(suite_id or "").strip()
    normalized_position = coerce_test_position(test_position)
    _set_query_param(QUERY_PARAM_SUITE_ID, normalized_suite_id or None)
    _set_query_param(
        QUERY_PARAM_TEST_POSITION,
        str(normalized_position) if normalized_suite_id and normalized_position else None,
    )
    st.session_state[TEST_SUITES_NAV_SIGNATURE_KEY] = build_navigation_signature(
        normalized_suite_id,
        normalized_position,
    )


def apply_test_suites_query_params(suites: list[dict]):
    requested_suite_id = _get_query_param(QUERY_PARAM_SUITE_ID)
    requested_position = coerce_test_position(_get_query_param(QUERY_PARAM_TEST_POSITION))
    requested_signature = build_navigation_signature(requested_suite_id, requested_position)
    if requested_signature == str(st.session_state.get(TEST_SUITES_NAV_SIGNATURE_KEY) or ""):
        return
    if not requested_suite_id:
        st.session_state[TEST_SUITES_NAV_SIGNATURE_KEY] = requested_signature
        return

    suite_ids = {str(item.get("id") or "").strip() for item in suites if isinstance(item, dict)}
    if requested_suite_id not in suite_ids:
        sync_test_suites_query_params(None, None)
        return

    st.session_state[SELECTED_TEST_SUITE_ID_KEY] = requested_suite_id
    if requested_position:
        st.session_state[SELECTED_TEST_POSITION_KEY] = requested_position
    else:
        st.session_state.pop(SELECTED_TEST_POSITION_KEY, None)
    sync_test_suites_query_params(requested_suite_id, requested_position)


def find_test_position_by_suite_item_id(suite_payload: dict | None, suite_item_id: str | None) -> int | None:
    target_suite_item_id = str(suite_item_id or "").strip()
    if not isinstance(suite_payload, dict) or not target_suite_item_id:
        return None
    tests = suite_payload.get("tests") or []
    for index, test in enumerate(tests, start=1):
        if not isinstance(test, dict):
            continue
        if str(test.get("id") or "").strip() != target_suite_item_id:
            continue
        position = coerce_test_position(test.get("position"))
        return position or index
    return None


def resolve_requested_test_position(test_suite_id: str | None, requested_test_id: str | None) -> int | None:
    normalized_suite_id = str(test_suite_id or "").strip()
    normalized_test_id = str(requested_test_id or "").strip()
    if not normalized_suite_id or not normalized_test_id:
        return None
    suite_payload = get_test_suite_by_id(normalized_suite_id)
    return find_test_position_by_suite_item_id(suite_payload, normalized_test_id)
