"""Unit tests for guided value control, guided KV editor, and body composer round-trips."""

import sys
import types
from pathlib import Path


if "streamlit" not in sys.modules:
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = {}
    streamlit_stub.dialog = lambda *args, **kwargs: (lambda fn: fn)
    sys.modules["streamlit"] = streamlit_stub

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "app" / "ui"
if str(UI_ROOT) not in sys.path:
    sys.path.append(str(UI_ROOT))


from ui.elaborations_shared.components.guided_value_control import (
    collect_guided_value,
    guided_state_to_node,
    initialize_guided_value_state,
    node_to_guided_state,
    validate_guided_value_node,
)
from ui.elaborations_shared.components.guided_kv_editor import (
    collect_guided_kv_rows,
    guided_dict_to_rows,
)
from ui.elaborations_shared.components.body_composer import (
    body_payload_to_tree,
    tree_to_payload,
)
from ui.elaborations_shared.components.auth_editor import (
    collect_guided_auth_value,
    initialize_guided_auth_state,
)


def _reset_session_state():
    sys.modules["streamlit"].session_state.clear()


# ---------------------------------------------------------------------------
# Guided value control
# ---------------------------------------------------------------------------


class TestGuidedValueControl:
    def test_node_to_state_literal_string(self):
        state = node_to_guided_state({"kind": "literal", "value": "hello"})
        assert state["mode"] == "literal"
        assert state["text"] == "hello"

    def test_node_to_state_literal_number(self):
        state = node_to_guided_state({"kind": "literal", "value": 42})
        assert state["mode"] == "literal"
        assert state["text"] == "42"

    def test_node_to_state_runtime_value(self):
        state = node_to_guided_state({"kind": "runtimeValue", "definitionId": "def-1"})
        assert state["mode"] == "runtimeValue"
        assert state["definitionId"] == "def-1"

    def test_node_to_state_runtime_value_with_field_path(self):
        state = node_to_guided_state(
            {"kind": "runtimeValue", "definitionId": "def-1", "fieldPath": "payload.access_token"}
        )
        assert state["mode"] == "runtimeValue"
        assert state["definitionId"] == "def-1"
        assert state["fieldPath"] == "payload.access_token"

    def test_node_to_state_source(self):
        state = node_to_guided_state({"kind": "source", "sourceCode": "src-1"})
        assert state["mode"] == "source"
        assert state["sourceCode"] == "src-1"

    def test_node_to_state_built_in(self):
        state = node_to_guided_state({"kind": "builtIn", "resolver": "today"})
        assert state["mode"] == "builtIn"
        assert state["resolver"] == "today"

    def test_node_to_state_plain_string(self):
        state = node_to_guided_state("hello")
        assert state["mode"] == "literal"
        assert state["text"] == "hello"

    def test_node_to_state_none(self):
        state = node_to_guided_state(None)
        assert state["mode"] == "literal"
        assert state["text"] == ""

    def test_state_to_node_literal(self):
        node = guided_state_to_node({"mode": "literal", "text": '"hello"'})
        assert node == {"kind": "literal", "value": "hello"}

    def test_state_to_node_literal_number(self):
        node = guided_state_to_node({"mode": "literal", "text": "42"})
        assert node == {"kind": "literal", "value": 42}

    def test_state_to_node_literal_plain_text(self):
        node = guided_state_to_node({"mode": "literal", "text": "not-json"})
        assert node == {"kind": "literal", "value": "not-json"}

    def test_state_to_node_runtime_value(self):
        node = guided_state_to_node({"mode": "runtimeValue", "definitionId": "def-1"})
        assert node == {"kind": "runtimeValue", "definitionId": "def-1"}

    def test_state_to_node_runtime_value_with_field_path(self):
        node = guided_state_to_node(
            {
                "mode": "runtimeValue",
                "definitionId": "def-1",
                "fieldPath": "payload.access_token",
            }
        )
        assert node == {
            "kind": "runtimeValue",
            "definitionId": "def-1",
            "fieldPath": "payload.access_token",
        }

    def test_state_to_node_source(self):
        node = guided_state_to_node({"mode": "source", "sourceCode": "src-1"})
        assert node == {"kind": "source", "sourceCode": "src-1"}

    def test_state_to_node_built_in(self):
        node = guided_state_to_node({"mode": "builtIn", "resolver": "now"})
        assert node == {"kind": "builtIn", "resolver": "now"}

    def test_round_trip_literal(self):
        original = {"kind": "literal", "value": "test"}
        state = node_to_guided_state(original)
        result = guided_state_to_node(state)
        assert result == original

    def test_round_trip_runtime_value(self):
        original = {"kind": "runtimeValue", "definitionId": "def-abc"}
        state = node_to_guided_state(original)
        result = guided_state_to_node(state)
        assert result == original

    def test_round_trip_source(self):
        original = {"kind": "source", "sourceCode": "orders"}
        state = node_to_guided_state(original)
        result = guided_state_to_node(state)
        assert result == original

    def test_round_trip_built_in(self):
        original = {"kind": "builtIn", "resolver": "today"}
        state = node_to_guided_state(original)
        result = guided_state_to_node(state)
        assert result == original

    def test_collect_literal_via_session_state(self):
        _reset_session_state()
        ss = sys.modules["streamlit"].session_state
        ss["test_gv_mode"] = "literal"
        ss["test_gv_text"] = '"hello"'
        node, error = collect_guided_value("test")
        assert error is None
        assert node == {"kind": "literal", "value": "hello"}

    def test_collect_runtime_value_via_session_state(self):
        _reset_session_state()
        ss = sys.modules["streamlit"].session_state
        ss["test_gv_mode"] = "runtimeValue"
        ss["test_gv_definitionId"] = "def-123"
        node, error = collect_guided_value("test")
        assert error is None
        assert node == {"kind": "runtimeValue", "definitionId": "def-123"}

    def test_collect_runtime_value_with_field_path_via_session_state(self):
        _reset_session_state()
        ss = sys.modules["streamlit"].session_state
        ss["test_gv_mode"] = "runtimeValue"
        ss["test_gv_definitionId"] = "def-123"
        ss["test_gv_fieldPath"] = "payload.access_token"
        node, error = collect_guided_value("test")
        assert error is None
        assert node == {
            "kind": "runtimeValue",
            "definitionId": "def-123",
            "fieldPath": "payload.access_token",
        }

    def test_collect_runtime_value_empty_returns_error(self):
        _reset_session_state()
        ss = sys.modules["streamlit"].session_state
        ss["test_gv_mode"] = "runtimeValue"
        ss["test_gv_definitionId"] = ""
        node, error = collect_guided_value("test")
        assert error is not None
        assert "required" in error.lower()

    def test_collect_source_via_session_state(self):
        _reset_session_state()
        ss = sys.modules["streamlit"].session_state
        ss["test_gv_mode"] = "source"
        ss["test_gv_sourceCode"] = "orders"
        node, error = collect_guided_value("test")
        assert error is None
        assert node == {"kind": "source", "sourceCode": "orders"}

    def test_collect_built_in_via_session_state(self):
        _reset_session_state()
        ss = sys.modules["streamlit"].session_state
        ss["test_gv_mode"] = "builtIn"
        ss["test_gv_resolver"] = "now"
        node, error = collect_guided_value("test")
        assert error is None
        assert node == {"kind": "builtIn", "resolver": "now"}

    def test_validate_guided_value_node_rejects_non_scalar_literal_when_requested(self):
        error = validate_guided_value_node(
            {"kind": "literal", "value": {"nested": True}},
            scalar_only=True,
        )
        assert error == "Only scalar literal values are supported."


# ---------------------------------------------------------------------------
# Guided KV editor
# ---------------------------------------------------------------------------


class TestGuidedKvEditor:
    def test_dict_to_rows_literal(self):
        rows = guided_dict_to_rows({"key1": {"kind": "literal", "value": "val1"}})
        assert len(rows) == 1
        assert rows[0]["key"] == "key1"
        assert rows[0]["node"]["kind"] == "literal"

    def test_dict_to_rows_plain_value(self):
        rows = guided_dict_to_rows({"key1": "val1"})
        assert len(rows) == 1
        assert rows[0]["node"]["kind"] == "literal"
        assert rows[0]["node"]["value"] == "val1"

    def test_dict_to_rows_none(self):
        rows = guided_dict_to_rows(None)
        assert rows == []

    def test_collect_guided_kv_rows_preserves_runtime_field_path(self):
        _reset_session_state()
        rows = [
            {
                "row_id": "row-1",
                "key": "access_token",
                "node": {
                    "kind": "runtimeValue",
                    "definitionId": "def-json",
                    "fieldPath": "payload.access_token",
                },
            }
        ]
        initialize_guided_value_state(
            "form_fields_val_row-1",
            rows[0]["node"],
        )

        payload, error = collect_guided_kv_rows(
            rows,
            "form_fields",
            "Form fields",
            allowed_modes=["literal", "runtimeValue", "builtIn"],
            scalar_only=True,
        )

        assert error is None
        assert payload == {
            "access_token": {
                "kind": "runtimeValue",
                "definitionId": "def-json",
                "fieldPath": "payload.access_token",
            }
        }


# ---------------------------------------------------------------------------
# Body composer
# ---------------------------------------------------------------------------


class TestBodyComposer:
    def test_payload_to_tree_none(self):
        tree = body_payload_to_tree(None)
        assert tree["type"] == "value"

    def test_payload_to_tree_literal_node(self):
        tree = body_payload_to_tree({"kind": "literal", "value": "hello"})
        assert tree["type"] == "value"
        assert tree["node"]["kind"] == "literal"

    def test_payload_to_tree_object(self):
        tree = body_payload_to_tree({"name": "test", "age": 30})
        assert tree["type"] == "object"
        assert len(tree["entries"]) == 2
        assert tree["entries"][0]["key"] == "name"

    def test_payload_to_tree_array(self):
        tree = body_payload_to_tree([1, 2, 3])
        assert tree["type"] == "array"
        assert len(tree["items"]) == 3

    def test_payload_to_tree_scalar(self):
        tree = body_payload_to_tree("hello")
        assert tree["type"] == "value"
        assert tree["node"]["kind"] == "literal"
        assert tree["node"]["value"] == "hello"

    def test_tree_to_payload_value(self):
        tree = {"type": "value", "node": {"kind": "literal", "value": "hello"}, "ui_key": "x"}
        payload = tree_to_payload(tree)
        assert payload == {"kind": "literal", "value": "hello"}

    def test_tree_to_payload_object(self):
        tree = {
            "type": "object",
            "entries": [
                {
                    "key": "name",
                    "child": {"type": "value", "node": {"kind": "literal", "value": "test"}, "ui_key": "c1"},
                    "ui_key": "e1",
                },
            ],
            "ui_key": "root",
        }
        payload = tree_to_payload(tree)
        assert isinstance(payload, dict)
        assert "name" in payload
        assert payload["name"] == {"kind": "literal", "value": "test"}

    def test_tree_to_payload_array(self):
        tree = {
            "type": "array",
            "items": [
                {
                    "child": {"type": "value", "node": {"kind": "literal", "value": 1}, "ui_key": "c1"},
                    "ui_key": "i1",
                },
                {
                    "child": {"type": "value", "node": {"kind": "literal", "value": 2}, "ui_key": "c2"},
                    "ui_key": "i2",
                },
            ],
            "ui_key": "root",
        }
        payload = tree_to_payload(tree)
        assert isinstance(payload, list)
        assert len(payload) == 2

    def test_round_trip_simple_object(self):
        original = {
            "name": {"kind": "literal", "value": "test"},
            "count": {"kind": "literal", "value": 42},
        }
        tree = body_payload_to_tree(original)
        result = tree_to_payload(tree)
        assert isinstance(result, dict)
        assert result["name"]["kind"] == "literal"
        assert result["count"]["value"] == 42

    def test_round_trip_nested(self):
        original = {
            "data": {
                "items": [
                    {"kind": "literal", "value": "a"},
                    {"kind": "literal", "value": "b"},
                ],
            },
        }
        tree = body_payload_to_tree(original)
        result = tree_to_payload(tree)
        assert isinstance(result, dict)
        assert isinstance(result["data"], dict)
        assert isinstance(result["data"]["items"], list)


# ---------------------------------------------------------------------------
# Guided auth editor
# ---------------------------------------------------------------------------


class TestGuidedAuthEditor:
    def test_collect_none_auth(self):
        _reset_session_state()
        ss = sys.modules["streamlit"].session_state
        ss["auth_test_type"] = "none"
        value, error = collect_guided_auth_value("auth_test")
        assert error is None
        assert value == {}

    def test_collect_basic_auth_guided(self):
        _reset_session_state()
        ss = sys.modules["streamlit"].session_state
        ss["auth_test_type"] = "basic"
        ss["auth_test_g_username_gv_mode"] = "literal"
        ss["auth_test_g_username_gv_text"] = '"alice"'
        ss["auth_test_g_password_gv_mode"] = "literal"
        ss["auth_test_g_password_gv_text"] = '"secret"'
        value, error = collect_guided_auth_value("auth_test")
        assert error is None
        assert value["type"] == "basic"
        assert value["username"] == {"kind": "literal", "value": "alice"}
        assert value["password"] == {"kind": "literal", "value": "secret"}

    def test_collect_bearer_auth_guided(self):
        _reset_session_state()
        ss = sys.modules["streamlit"].session_state
        ss["auth_test_type"] = "bearer"
        ss["auth_test_g_token_gv_mode"] = "runtimeValue"
        ss["auth_test_g_token_gv_definitionId"] = "token-def"
        value, error = collect_guided_auth_value("auth_test")
        assert error is None
        assert value["type"] == "bearer"
        assert value["token"] == {"kind": "runtimeValue", "definitionId": "token-def"}

    def test_collect_oauth2_auth_guided(self):
        _reset_session_state()
        ss = sys.modules["streamlit"].session_state
        ss["auth_test_type"] = "oauth2"
        ss["auth_test_g_tokenUrl_gv_mode"] = "literal"
        ss["auth_test_g_tokenUrl_gv_text"] = '"https://auth.example.com/token"'
        ss["auth_test_g_clientId_gv_mode"] = "literal"
        ss["auth_test_g_clientId_gv_text"] = '"client1"'
        ss["auth_test_g_clientSecret_gv_mode"] = "literal"
        ss["auth_test_g_clientSecret_gv_text"] = '"secret1"'
        value, error = collect_guided_auth_value("auth_test")
        assert error is None
        assert value["type"] == "oauth2"
        assert value["tokenUrl"]["value"] == "https://auth.example.com/token"
