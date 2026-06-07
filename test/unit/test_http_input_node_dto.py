"""Unit tests for HTTP input node DTO, guided authorization, and pathParams support."""

import pytest

from elaborations.models.dtos.configuration_command_dto import (
    HttpInputNode,
    HttpInputNodeKind,
    ReadApiConfigurationCommandDto,
    WriteApiConfigurationCommandDto,
    convert_to_config_command_type,
    _coerce_http_input_node,
    _coerce_to_http_input_node,
    _coerce_http_input_tree,
    _coerce_http_kv_params,
    _coerce_authorization_guided,
    _serialize_http_input_node,
)


# ---------------------------------------------------------------------------
# HttpInputNode model
# ---------------------------------------------------------------------------


class TestHttpInputNode:
    def test_literal_node(self):
        node = HttpInputNode(kind="literal", value="hello")
        assert node.kind == "literal"
        assert node.value == "hello"
        assert node.definitionId is None

    def test_runtime_value_node(self):
        node = HttpInputNode(kind="runtimeValue", definitionId="def-1")
        assert node.kind == "runtimeValue"
        assert node.definitionId == "def-1"
        assert node.value is None

    def test_source_node(self):
        node = HttpInputNode(kind="source", sourceCode="ordersSource")
        assert node.kind == "source"
        assert node.sourceCode == "ordersSource"

    def test_built_in_node(self):
        node = HttpInputNode(kind="builtIn", resolver="today")
        assert node.kind == "builtIn"
        assert node.resolver == "today"

    def test_built_in_node_now(self):
        node = HttpInputNode(kind="builtIn", resolver="now")
        assert node.resolver == "now"

    def test_invalid_kind_raises(self):
        with pytest.raises(ValueError, match="kind must be one of"):
            HttpInputNode(kind="unknown")

    def test_runtime_value_requires_definition_id(self):
        with pytest.raises(ValueError, match="definitionId is required"):
            HttpInputNode(kind="runtimeValue")

    def test_source_requires_source_code(self):
        with pytest.raises(ValueError, match="sourceCode is required"):
            HttpInputNode(kind="source")

    def test_built_in_requires_valid_resolver(self):
        with pytest.raises(ValueError, match="resolver must be one of"):
            HttpInputNode(kind="builtIn", resolver="invalid")


# ---------------------------------------------------------------------------
# Coercion functions
# ---------------------------------------------------------------------------


class TestCoercion:
    def test_coerce_http_input_node_from_dict(self):
        node = _coerce_http_input_node({"kind": "literal", "value": 42})
        assert isinstance(node, HttpInputNode)
        assert node.kind == "literal"
        assert node.value == 42

    def test_coerce_http_input_node_returns_none_for_plain_dict(self):
        result = _coerce_http_input_node({"foo": "bar"})
        assert result is None

    def test_coerce_to_http_input_node_wraps_scalar(self):
        node = _coerce_to_http_input_node("hello")
        assert isinstance(node, HttpInputNode)
        assert node.kind == "literal"
        assert node.value == "hello"

    def test_coerce_to_http_input_node_wraps_number(self):
        node = _coerce_to_http_input_node(42)
        assert isinstance(node, HttpInputNode)
        assert node.value == 42

    def test_coerce_to_http_input_node_passes_through_node(self):
        node = _coerce_to_http_input_node({"kind": "runtimeValue", "definitionId": "x"})
        assert isinstance(node, HttpInputNode)
        assert node.kind == "runtimeValue"

    def test_coerce_http_input_tree_recursive(self):
        tree = _coerce_http_input_tree({
            "field1": "hello",
            "field2": {"kind": "runtimeValue", "definitionId": "def-1"},
            "nested": {"a": 42},
        })
        assert isinstance(tree, dict)
        assert isinstance(tree["field1"], HttpInputNode)
        assert tree["field1"].value == "hello"
        assert isinstance(tree["field2"], HttpInputNode)
        assert tree["field2"].kind == "runtimeValue"
        assert isinstance(tree["nested"], dict)
        assert isinstance(tree["nested"]["a"], HttpInputNode)

    def test_coerce_http_input_tree_list(self):
        tree = _coerce_http_input_tree([1, "two", {"kind": "builtIn", "resolver": "today"}])
        assert isinstance(tree, list)
        assert len(tree) == 3
        assert isinstance(tree[0], HttpInputNode)
        assert tree[0].value == 1
        assert isinstance(tree[2], HttpInputNode)
        assert tree[2].kind == "builtIn"

    def test_coerce_http_kv_params_from_dict(self):
        result = _coerce_http_kv_params({"key1": "val1", "key2": 42})
        assert isinstance(result, dict)
        assert isinstance(result["key1"], HttpInputNode)
        assert result["key1"].value == "val1"
        assert isinstance(result["key2"], HttpInputNode)
        assert result["key2"].value == 42

    def test_coerce_http_kv_params_preserves_nodes(self):
        result = _coerce_http_kv_params({
            "key1": {"kind": "runtimeValue", "definitionId": "d1"},
        })
        assert isinstance(result["key1"], HttpInputNode)
        assert result["key1"].kind == "runtimeValue"

    def test_coerce_http_kv_params_from_list(self):
        result = _coerce_http_kv_params(["a", "b"])
        assert isinstance(result, dict)
        assert "0" in result
        assert "1" in result

    def test_coerce_http_kv_params_none(self):
        assert _coerce_http_kv_params(None) is None

    def test_coerce_http_kv_params_empty_dict(self):
        assert _coerce_http_kv_params({}) is None


# ---------------------------------------------------------------------------
# Guided authorization coercion
# ---------------------------------------------------------------------------


class TestGuidedAuthorization:
    def test_basic_auth_with_literal_strings(self):
        result = _coerce_authorization_guided({
            "type": "basic",
            "username": "alice",
            "password": "secret",
        })
        assert result["type"] == "basic"
        assert isinstance(result["username"], HttpInputNode)
        assert result["username"].kind == "literal"
        assert result["username"].value == "alice"

    def test_basic_auth_with_guided_node(self):
        result = _coerce_authorization_guided({
            "type": "basic",
            "username": {"kind": "runtimeValue", "definitionId": "user-def"},
            "password": {"kind": "literal", "value": "secret"},
        })
        assert result["username"].kind == "runtimeValue"
        assert result["username"].definitionId == "user-def"

    def test_bearer_auth(self):
        result = _coerce_authorization_guided({
            "type": "bearer",
            "token": "my-token",
        })
        assert result["type"] == "bearer"
        assert isinstance(result["token"], HttpInputNode)
        assert result["token"].value == "my-token"

    def test_api_key_auth(self):
        result = _coerce_authorization_guided({
            "type": "apiKey",
            "username": "user1",
            "apiKey": "key1",
            "authEndpoint": "https://auth.example.com/token",
        })
        assert result["type"] == "apiKey"
        assert isinstance(result["username"], HttpInputNode)
        assert isinstance(result["apiKey"], HttpInputNode)
        assert isinstance(result["authEndpoint"], HttpInputNode)

    def test_oauth2_auth(self):
        result = _coerce_authorization_guided({
            "type": "oauth2",
            "tokenUrl": "https://auth.example.com/token",
            "clientId": "client1",
            "clientSecret": "secret1",
        })
        assert result["type"] == "oauth2"
        assert isinstance(result["tokenUrl"], HttpInputNode)

    def test_empty_type_returns_empty_dict(self):
        result = _coerce_authorization_guided({"type": ""})
        assert result == {}

    def test_none_returns_none(self):
        assert _coerce_authorization_guided(None) is None

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="authorization.type"):
            _coerce_authorization_guided({"type": "custom"})


# ---------------------------------------------------------------------------
# ReadApi / WriteApi DTOs with pathParams
# ---------------------------------------------------------------------------


class TestReadApiDto:
    def test_basic_creation(self):
        dto = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com/orders",
        )
        assert dto.method == "GET"
        assert dto.url == "https://api.example.com/orders"
        assert dto.pathParams is None

    def test_with_path_params(self):
        dto = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com/orders/{id}",
            pathParams={"id": "123"},
        )
        assert dto.pathParams is not None
        assert "id" in dto.pathParams
        assert isinstance(dto.pathParams["id"], HttpInputNode)
        assert dto.pathParams["id"].value == "123"

    def test_with_guided_query_params(self):
        dto = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com/orders",
            queryParams={"page": "1", "status": {"kind": "runtimeValue", "definitionId": "def-1"}},
        )
        assert isinstance(dto.queryParams["page"], HttpInputNode)
        assert dto.queryParams["page"].value == "1"
        assert dto.queryParams["status"].kind == "runtimeValue"

    def test_with_guided_headers(self):
        dto = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com/orders",
            headers={"X-Custom": {"kind": "builtIn", "resolver": "today"}},
        )
        assert dto.headers["X-Custom"].kind == "builtIn"
        assert dto.headers["X-Custom"].resolver == "today"

    def test_with_guided_auth(self):
        dto = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com/orders",
            authorization={"type": "bearer", "token": "abc"},
        )
        assert dto.authorization["type"] == "bearer"
        assert isinstance(dto.authorization["token"], HttpInputNode)

    def test_legacy_dict_query_params_normalized(self):
        dto = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com/orders",
            queryParams={"page": 1, "limit": 50},
        )
        assert isinstance(dto.queryParams["page"], HttpInputNode)
        assert dto.queryParams["page"].value == 1

    def test_legacy_list_query_params(self):
        dto = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com/orders",
            queryParams=["a", "b"],
        )
        assert isinstance(dto.queryParams, dict)


class TestWriteApiDto:
    def test_basic_creation(self):
        dto = WriteApiConfigurationCommandDto(
            commandCode="writeApi",
            commandType="action",
            method="POST",
            url="https://api.example.com/orders",
        )
        assert dto.method == "POST"
        assert dto.pathParams is None

    def test_with_path_params(self):
        dto = WriteApiConfigurationCommandDto(
            commandCode="writeApi",
            commandType="action",
            method="PUT",
            url="https://api.example.com/orders/{orderId}",
            pathParams={"orderId": {"kind": "runtimeValue", "definitionId": "order-def"}},
        )
        assert dto.pathParams["orderId"].kind == "runtimeValue"

    def test_body_with_guided_nodes(self):
        dto = WriteApiConfigurationCommandDto(
            commandCode="writeApi",
            commandType="action",
            method="POST",
            url="https://api.example.com/orders",
            body={
                "name": "test",
                "timestamp": {"kind": "builtIn", "resolver": "now"},
            },
        )
        assert isinstance(dto.body, dict)
        assert isinstance(dto.body["name"], HttpInputNode)
        assert dto.body["name"].value == "test"
        assert isinstance(dto.body["timestamp"], HttpInputNode)
        assert dto.body["timestamp"].kind == "builtIn"

    def test_body_with_nested_structure(self):
        dto = WriteApiConfigurationCommandDto(
            commandCode="writeApi",
            commandType="action",
            method="POST",
            url="https://api.example.com/data",
            body={
                "level1": {
                    "level2": {"kind": "literal", "value": "deep"},
                },
            },
        )
        assert isinstance(dto.body["level1"], dict)
        assert isinstance(dto.body["level1"]["level2"], HttpInputNode)

    def test_form_urlencoded_body_accepts_flat_guided_nodes(self):
        dto = WriteApiConfigurationCommandDto(
            commandCode="writeApi",
            commandType="action",
            method="POST",
            url="https://api.example.com/orders",
            bodyType="formUrlEncoded",
            body={
                "code": {"kind": "literal", "value": "A-100"},
                "requestedAt": {"kind": "builtIn", "resolver": "now"},
            },
        )
        assert dto.bodyType == "formUrlEncoded"
        assert isinstance(dto.body["code"], HttpInputNode)
        assert dto.body["code"].kind == "literal"
        assert dto.body["requestedAt"].kind == "builtIn"

    def test_form_urlencoded_body_rejects_source_nodes(self):
        with pytest.raises(ValueError, match="does not support source nodes"):
            WriteApiConfigurationCommandDto(
                commandCode="writeApi",
                commandType="action",
                method="POST",
                url="https://api.example.com/orders",
                bodyType="formUrlEncoded",
                body={"rows": {"kind": "source", "sourceCode": "orders"}},
            )

    def test_form_urlencoded_body_rejects_nested_literals(self):
        with pytest.raises(ValueError, match="scalar literal"):
            WriteApiConfigurationCommandDto(
                commandCode="writeApi",
                commandType="action",
                method="POST",
                url="https://api.example.com/orders",
                bodyType="formUrlEncoded",
                body={"payload": {"kind": "literal", "value": {"nested": True}}},
            )


# ---------------------------------------------------------------------------
# convert_to_config_command_type with pathParams
# ---------------------------------------------------------------------------


class TestConvertToConfigCommandType:
    def test_read_api_with_path_params(self):
        cfg = convert_to_config_command_type({
            "commandCode": "readApi",
            "commandType": "action",
            "url": "https://api.example.com/{id}",
            "pathParams": {"id": {"kind": "literal", "value": "123"}},
        })
        assert isinstance(cfg, ReadApiConfigurationCommandDto)
        assert cfg.pathParams is not None
        assert "id" in cfg.pathParams

    def test_write_api_with_path_params(self):
        cfg = convert_to_config_command_type({
            "commandCode": "writeApi",
            "commandType": "action",
            "method": "POST",
            "url": "https://api.example.com/{id}",
            "pathParams": {"id": "abc"},
        })
        assert isinstance(cfg, WriteApiConfigurationCommandDto)
        assert cfg.pathParams is not None

    def test_legacy_read_api_still_works(self):
        cfg = convert_to_config_command_type({
            "commandCode": "readApi",
            "commandType": "action",
            "url": "https://api.example.com/orders",
            "queryParams": {"page": 1},
            "headers": {"Accept": "application/json"},
            "authorization": {"type": "bearer", "token": "abc"},
        })
        assert isinstance(cfg, ReadApiConfigurationCommandDto)
        assert cfg.queryParams is not None
        assert isinstance(cfg.queryParams["page"], HttpInputNode)
        assert cfg.queryParams["page"].value == 1

    def test_legacy_write_api_still_works(self):
        cfg = convert_to_config_command_type({
            "commandCode": "writeApi",
            "commandType": "action",
            "method": "POST",
            "url": "https://api.example.com/orders",
            "body": {"name": "order1"},
            "headers": {"Content-Type": "application/json"},
        })
        assert isinstance(cfg, WriteApiConfigurationCommandDto)
        assert isinstance(cfg.body, dict)

    def test_convert_write_api_with_form_urlencoded_body(self):
        cfg = convert_to_config_command_type({
            "commandCode": "writeApi",
            "commandType": "action",
            "method": "POST",
            "url": "https://api.example.com/orders",
            "bodyType": "formUrlEncoded",
            "body": {
                "code": {"kind": "literal", "value": "A-100"},
            },
        })
        assert isinstance(cfg, WriteApiConfigurationCommandDto)
        assert cfg.bodyType == "formUrlEncoded"
        assert cfg.body["code"].kind == "literal"


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_serialize_literal_node(self):
        node = HttpInputNode(kind="literal", value="hello")
        result = _serialize_http_input_node(node)
        assert result == {"kind": "literal", "value": "hello"}

    def test_serialize_runtime_value_node(self):
        node = HttpInputNode(kind="runtimeValue", definitionId="def-1")
        result = _serialize_http_input_node(node)
        assert result == {"kind": "runtimeValue", "definitionId": "def-1"}

    def test_serialize_source_node(self):
        node = HttpInputNode(kind="source", sourceCode="src-1")
        result = _serialize_http_input_node(node)
        assert result == {"kind": "source", "sourceCode": "src-1"}

    def test_serialize_built_in_node(self):
        node = HttpInputNode(kind="builtIn", resolver="today")
        result = _serialize_http_input_node(node)
        assert result == {"kind": "builtIn", "resolver": "today"}

    def test_serialize_nested_dict(self):
        tree = {
            "key": HttpInputNode(kind="literal", value=42),
            "nested": {
                "child": HttpInputNode(kind="builtIn", resolver="now"),
            },
        }
        result = _serialize_http_input_node(tree)
        assert result["key"] == {"kind": "literal", "value": 42}
        assert result["nested"]["child"] == {"kind": "builtIn", "resolver": "now"}

    def test_serialize_list(self):
        tree = [
            HttpInputNode(kind="literal", value="a"),
            HttpInputNode(kind="literal", value="b"),
        ]
        result = _serialize_http_input_node(tree)
        assert result == [
            {"kind": "literal", "value": "a"},
            {"kind": "literal", "value": "b"},
        ]
