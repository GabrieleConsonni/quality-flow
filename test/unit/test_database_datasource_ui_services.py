import sys
import types
from pathlib import Path

import pytest


if "streamlit" not in sys.modules:
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = {}
    streamlit_stub.dialog = lambda *args, **kwargs: (lambda fn: fn)
    sys.modules["streamlit"] = streamlit_stub
elif not hasattr(sys.modules["streamlit"], "dialog"):
    sys.modules["streamlit"].dialog = lambda *args, **kwargs: (lambda fn: fn)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "app" / "ui"
if str(UI_ROOT) not in sys.path:
    sys.path.append(str(UI_ROOT))


from database_datasources.services import perimeter_service, state_keys, state_service


@pytest.fixture(autouse=True)
def clear_streamlit_state():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


def test_build_perimeter_payload_omits_blank_values_and_keeps_null_operators():
    payload = perimeter_service.build_perimeter_payload(
        ["id", " status ", ""],
        [
            {
                "name": "statusParam",
                "type": "string",
                "default_mode": "Literal",
                "default_value": '"READY"',
                "default_function": "",
                "description": "status",
            }
        ],
        "or",
        [
            {
                "field": "status",
                "operator": "eq",
                "value": {"kind": "parameter", "name": "statusParam"},
            },
            {"field": "deleted_at", "operator": "is_null", "value": ""},
            {"field": "", "operator": "", "value": ""},
        ],
        [
            {"field": "created_at", "direction": "DESC"},
            {"field": "", "direction": ""},
        ],
    )

    assert payload == {
        "selected_columns": ["id", "status"],
        "parameters": [
            {
                "name": "statusParam",
                "type": "string",
                "default_value": "READY",
                "description": "status",
            }
        ],
        "filter": {
            "logic": "OR",
            "items": [
                {
                    "kind": "condition",
                    "field": "status",
                    "operator": "eq",
                    "value": {"kind": "parameter", "name": "statusParam"},
                },
                {
                    "kind": "condition",
                    "field": "deleted_at",
                    "operator": "is_null",
                },
            ],
        },
        "sort": [
            {"field": "created_at", "direction": "desc"},
        ],
    }


def test_build_dataset_summary_maps_connection_and_object_metadata():
    summary = perimeter_service.build_dataset_summary(
        {
            "id": "dataset-1",
            "description": "Orders dataset",
            "payload": {
                "connection_id": "conn-1",
                "schema": "public",
                "object_name": "orders_view",
                "object_type": "view",
            },
        },
        {"conn-1": "Orders DB [postgres]"},
    )

    assert summary == {
        "id": "dataset-1",
        "description": "Orders dataset",
        "connection_id": "conn-1",
        "connection_label": "Orders DB [postgres]",
        "schema": "public",
        "object_type": "view",
        "object_name": "orders_view",
        "object_label": "VIEW orders_view",
    }


def test_build_perimeter_payload_serializes_function_defaults():
    payload = perimeter_service.build_perimeter_payload(
        ["created_at"],
        [
            {
                "name": "snapshotAt",
                "type": "datetime",
                "default_mode": "Function",
                "default_value": "",
                "default_function": "Now",
                "description": "runtime snapshot",
            }
        ],
        "AND",
        [],
        [],
    )

    assert payload == {
        "selected_columns": ["created_at"],
        "parameters": [
            {
                "name": "snapshotAt",
                "type": "datetime",
                "default_binding": {
                    "kind": "built_in",
                    "resolver": "$now",
                },
                "description": "runtime snapshot",
            }
        ],
    }


def test_default_parameter_rows_round_trip_function_defaults():
    rows = perimeter_service.default_parameter_rows(
        {
            "parameters": [
                {
                    "name": "currentDay",
                    "type": "date",
                    "default_binding": {
                        "kind": "built_in",
                        "resolver": "$today",
                    },
                }
            ]
        }
    )

    assert rows == [
        {
            "name": "currentDay",
            "type": "date",
            "default_mode": "Function",
            "default_value": None,
            "default_function": "Today",
            "description": None,
        }
    ]


def test_toggle_database_datasource_preview_updates_selected_and_open_state():
    assert state_service.toggle_database_datasource_preview("dataset-42") is True
    assert state_service.get_selected_database_datasource_id() == "dataset-42"
    assert sys.modules["streamlit"].session_state[state_keys.DATABASE_DATASOURCE_PREVIEW_VISIBLE_ID_KEY] == "dataset-42"
    assert state_service.is_database_datasource_open("dataset-42") is True

    assert state_service.toggle_database_datasource_preview("dataset-42") is False
    assert sys.modules["streamlit"].session_state[state_keys.DATABASE_DATASOURCE_PREVIEW_VISIBLE_ID_KEY] is None
    assert state_service.is_database_datasource_open("dataset-42") is False


def test_clear_database_datasource_selection_if_matches_resets_related_state():
    state_service.set_selected_database_datasource_id("dataset-5")
    state_service.set_database_datasource_perimeter_edit_id("dataset-5")
    state_service.toggle_database_datasource_preview("dataset-5")

    state_service.clear_database_datasource_selection_if_matches("dataset-5")

    assert state_service.get_selected_database_datasource_id() is None
    assert state_service.get_database_datasource_perimeter_edit_id() is None
    assert sys.modules["streamlit"].session_state.get(state_keys.DATABASE_DATASOURCE_PREVIEW_VISIBLE_ID_KEY) is None
    assert state_service.is_database_datasource_open("dataset-5") is False
