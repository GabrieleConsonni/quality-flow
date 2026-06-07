"""Unit tests for HTTP input node resolver — path params, headers, auth compilation."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from elaborations.services.operations.http_input_node_resolver import (
    _resolve_built_in,
    resolve_http_body,
    resolve_path_params_and_url,
)
from elaborations.models.dtos.configuration_command_dto import HttpInputNode


# ---------------------------------------------------------------------------
# Built-in resolution
# ---------------------------------------------------------------------------


class TestResolveBuiltIn:
    def test_today(self):
        result = _resolve_built_in("today")
        assert isinstance(result, str)
        assert len(result) == 10  # YYYY-MM-DD

    def test_now(self):
        result = _resolve_built_in("now")
        assert isinstance(result, str)
        assert "T" in result

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            _resolve_built_in("invalid")


# ---------------------------------------------------------------------------
# Path param interpolation
# ---------------------------------------------------------------------------


class TestPathParams:
    def test_no_params_plain_url(self):
        session = MagicMock()
        result = resolve_path_params_and_url(session, "https://api.example.com/orders", None)
        assert result == "https://api.example.com/orders"

    def test_no_params_with_placeholders_raises(self):
        session = MagicMock()
        with pytest.raises(ValueError, match="unresolved path parameter"):
            resolve_path_params_and_url(session, "https://api.example.com/{id}", None)

    def test_literal_params(self):
        session = MagicMock()
        params = {
            "id": HttpInputNode(kind="literal", value="123"),
        }
        with patch(
            "elaborations.services.operations.http_input_node_resolver.resolve_http_input_node",
            side_effect=lambda s, n: n.value if isinstance(n, HttpInputNode) and n.kind == "literal" else None,
        ):
            result = resolve_path_params_and_url(session, "https://api.example.com/orders/{id}", params)
        assert result == "https://api.example.com/orders/123"

    def test_multiple_params(self):
        session = MagicMock()
        params = {
            "org": HttpInputNode(kind="literal", value="acme"),
            "id": HttpInputNode(kind="literal", value="456"),
        }
        with patch(
            "elaborations.services.operations.http_input_node_resolver.resolve_http_input_node",
            side_effect=lambda s, n: n.value if isinstance(n, HttpInputNode) and n.kind == "literal" else None,
        ):
            result = resolve_path_params_and_url(
                session, "https://api.example.com/{org}/orders/{id}", params
            )
        assert result == "https://api.example.com/acme/orders/456"

    def test_missing_param_value_raises(self):
        session = MagicMock()
        params = {
            "id": HttpInputNode(kind="literal", value=None),
        }
        with patch(
            "elaborations.services.operations.http_input_node_resolver.resolve_http_input_node",
            return_value=None,
        ):
            with pytest.raises(ValueError, match="resolved to None"):
                resolve_path_params_and_url(session, "https://api.example.com/{id}", params)

    def test_unmatched_placeholder_raises(self):
        session = MagicMock()
        params = {
            "x": HttpInputNode(kind="literal", value="val"),
        }
        with patch(
            "elaborations.services.operations.http_input_node_resolver.resolve_http_input_node",
            side_effect=lambda s, n: n.value if isinstance(n, HttpInputNode) and n.kind == "literal" else None,
        ):
            with pytest.raises(ValueError, match="no matching pathParams"):
                resolve_path_params_and_url(session, "https://api.example.com/{y}", params)


# ---------------------------------------------------------------------------
# Body resolution
# ---------------------------------------------------------------------------


class TestResolveHttpBody:
    def test_form_urlencoded_body_omits_none_and_preserves_scalars(self):
        session = MagicMock()
        body = {
            "access_token": HttpInputNode(
                kind="runtimeValue",
                definitionId="def-json",
                fieldPath="payload.access_token",
            ),
            "empty": HttpInputNode(kind="literal", value=None),
            "sent_at": HttpInputNode(kind="builtIn", resolver="today"),
        }

        def _fake_resolve_http_input_node(_session, node):
            if node.kind == "runtimeValue":
                return "abc-123"
            if node.kind == "builtIn":
                return "2026-04-14"
            return node.value

        with patch(
            "elaborations.services.operations.http_input_node_resolver.resolve_definition_path",
            return_value=(SimpleNamespace(value_type="json"), "$.local.constants.response"),
        ), patch(
            "elaborations.services.operations.http_input_node_resolver.resolve_http_input_node",
            side_effect=_fake_resolve_http_input_node,
        ):
            resolved = resolve_http_body(session, body, "formUrlEncoded")

        assert resolved == {
            "access_token": "abc-123",
            "sent_at": "2026-04-14",
        }

    def test_form_urlencoded_body_rejects_runtime_value_with_dataset_type(self):
        session = MagicMock()
        body = {
            "rows": HttpInputNode(kind="runtimeValue", definitionId="def-dataset"),
        }

        with patch(
            "elaborations.services.operations.http_input_node_resolver.resolve_definition_path",
            return_value=(SimpleNamespace(value_type="dataset"), "$.local.constants.rows"),
        ):
            with pytest.raises(ValueError, match="does not support runtime value type 'dataset'"):
                resolve_http_body(session, body, "formUrlEncoded")

    def test_form_urlencoded_body_rejects_non_scalar_resolved_value(self):
        session = MagicMock()
        body = {
            "payload": HttpInputNode(kind="runtimeValue", definitionId="def-json"),
        }

        with patch(
            "elaborations.services.operations.http_input_node_resolver.resolve_definition_path",
            return_value=(SimpleNamespace(value_type="json"), "$.local.constants.payload"),
        ), patch(
            "elaborations.services.operations.http_input_node_resolver.resolve_http_input_node",
            return_value={"nested": True},
        ):
            with pytest.raises(ValueError, match="resolved to a non-scalar value"):
                resolve_http_body(session, body, "formUrlEncoded")
