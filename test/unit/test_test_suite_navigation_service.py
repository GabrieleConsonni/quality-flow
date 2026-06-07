import sys
import types
from pathlib import Path

import pytest


if "streamlit" not in sys.modules:
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = {}
    streamlit_stub.query_params = {}
    sys.modules["streamlit"] = streamlit_stub
else:
    sys.modules["streamlit"].session_state = getattr(sys.modules["streamlit"], "session_state", {})
    sys.modules["streamlit"].query_params = getattr(sys.modules["streamlit"], "query_params", {})

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "app" / "ui"
if str(UI_ROOT) not in sys.path:
    sys.path.append(str(UI_ROOT))


from ui.test_suites.services import navigation_service
from ui.test_suites.services.state_keys import (
    SELECTED_TEST_POSITION_KEY,
    SELECTED_TEST_SUITE_ID_KEY,
)


@pytest.fixture(autouse=True)
def clear_streamlit_state():
    sys.modules["streamlit"].session_state.clear()
    sys.modules["streamlit"].query_params.clear()
    yield
    sys.modules["streamlit"].session_state.clear()
    sys.modules["streamlit"].query_params.clear()


def test_find_test_position_by_suite_item_id_uses_declared_position_or_fallback():
    assert navigation_service.find_test_position_by_suite_item_id(
        {
            "tests": [
                {"id": "test-1", "position": 7},
                {"id": "test-2"},
            ]
        },
        "test-1",
    ) == 7
    assert navigation_service.find_test_position_by_suite_item_id(
        {
            "tests": [
                {"id": "test-1", "position": 7},
                {"id": "test-2"},
            ]
        },
        "test-2",
    ) == 2


def test_sync_test_suites_query_params_updates_query_state():
    navigation_service.sync_test_suites_query_params("suite-1", 4)

    assert sys.modules["streamlit"].query_params == {
        "suite_id": "suite-1",
        "test_position": "4",
    }
    assert sys.modules["streamlit"].session_state[navigation_service.TEST_SUITES_NAV_SIGNATURE_KEY] == "suite-1|4"


def test_apply_test_suites_query_params_syncs_suite_and_test_selection():
    sys.modules["streamlit"].query_params["suite_id"] = "suite-2"
    sys.modules["streamlit"].query_params["test_position"] = "3"

    navigation_service.apply_test_suites_query_params(
        [
            {"id": "suite-1", "description": "Suite 1"},
            {"id": "suite-2", "description": "Suite 2"},
        ]
    )

    assert sys.modules["streamlit"].session_state[SELECTED_TEST_SUITE_ID_KEY] == "suite-2"
    assert sys.modules["streamlit"].session_state[SELECTED_TEST_POSITION_KEY] == 3


def test_resolve_requested_test_position_reads_suite_payload(monkeypatch):
    monkeypatch.setattr(
        navigation_service,
        "get_test_suite_by_id",
        lambda suite_id: {
            "id": suite_id,
            "tests": [
                {"id": "test-1", "position": 1},
                {"id": "test-2", "position": 5},
            ],
        },
    )

    position = navigation_service.resolve_requested_test_position("suite-9", "test-2")

    assert position == 5
