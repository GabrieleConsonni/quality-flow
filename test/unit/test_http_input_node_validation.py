"""Unit tests for validation graph extraction of HTTP input node refs."""

import pytest

from elaborations.models.dtos.configuration_command_dto import (
    HttpInputNode,
    ReadApiConfigurationCommandDto,
    WriteApiConfigurationCommandDto,
)
from elaborations.services.constants.command_constant_definition_registry import (
    PlannedDefinition,
    _definition_refs,
    _extract_http_input_node_refs,
    _extract_http_auth_refs,
    plan_definitions_for_commands,
)


class TestExtractHttpInputNodeRefs:
    def test_literal_node_no_refs(self):
        node = HttpInputNode(kind="literal", value="hello")
        refs = _extract_http_input_node_refs(node, "source")
        assert refs == []

    def test_runtime_value_node_extracts_ref(self):
        node = HttpInputNode(kind="runtimeValue", definitionId="def-1")
        refs = _extract_http_input_node_refs(node, "source")
        assert refs == [("source", "def-1")]

    def test_source_node_no_runtime_refs(self):
        node = HttpInputNode(kind="source", sourceCode="src-1")
        refs = _extract_http_input_node_refs(node, "source")
        assert refs == []

    def test_built_in_no_refs(self):
        node = HttpInputNode(kind="builtIn", resolver="today")
        refs = _extract_http_input_node_refs(node, "source")
        assert refs == []

    def test_nested_dict_with_runtime_value(self):
        tree = {
            "key1": HttpInputNode(kind="literal", value="x"),
            "key2": HttpInputNode(kind="runtimeValue", definitionId="def-2"),
        }
        refs = _extract_http_input_node_refs(tree, "source")
        assert ("source", "def-2") in refs
        assert len(refs) == 1

    def test_nested_list_with_runtime_value(self):
        tree = [
            HttpInputNode(kind="runtimeValue", definitionId="def-a"),
            HttpInputNode(kind="literal", value="x"),
        ]
        refs = _extract_http_input_node_refs(tree, "source")
        assert refs == [("source", "def-a")]


class TestExtractHttpAuthRefs:
    def test_no_auth(self):
        assert _extract_http_auth_refs(None) == []
        assert _extract_http_auth_refs({}) == []

    def test_literal_auth_no_refs(self):
        auth = {
            "type": "basic",
            "username": HttpInputNode(kind="literal", value="alice"),
            "password": HttpInputNode(kind="literal", value="pass"),
        }
        refs = _extract_http_auth_refs(auth)
        assert refs == []

    def test_runtime_value_in_auth(self):
        auth = {
            "type": "basic",
            "username": HttpInputNode(kind="runtimeValue", definitionId="user-def"),
            "password": HttpInputNode(kind="literal", value="pass"),
        }
        refs = _extract_http_auth_refs(auth)
        assert ("source", "user-def") in refs


class TestDefinitionRefsForApiCommands:
    def test_read_api_with_runtime_value_in_headers(self):
        cfg = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com",
            headers={"X-Key": {"kind": "runtimeValue", "definitionId": "hdr-def"}},
        )
        refs = _definition_refs(cfg)
        assert ("source", "hdr-def") in refs

    def test_read_api_with_runtime_value_in_query_params(self):
        cfg = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com",
            queryParams={"page": {"kind": "runtimeValue", "definitionId": "page-def"}},
        )
        refs = _definition_refs(cfg)
        assert ("source", "page-def") in refs

    def test_read_api_with_runtime_value_in_path_params(self):
        cfg = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com/{id}",
            pathParams={"id": {"kind": "runtimeValue", "definitionId": "id-def"}},
        )
        refs = _definition_refs(cfg)
        assert ("source", "id-def") in refs

    def test_read_api_with_runtime_value_in_auth(self):
        cfg = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com",
            authorization={
                "type": "bearer",
                "token": {"kind": "runtimeValue", "definitionId": "token-def"},
            },
        )
        refs = _definition_refs(cfg)
        assert ("source", "token-def") in refs

    def test_write_api_with_runtime_value_in_body(self):
        cfg = WriteApiConfigurationCommandDto(
            commandCode="writeApi",
            commandType="action",
            method="POST",
            url="https://api.example.com",
            body={
                "userId": {"kind": "runtimeValue", "definitionId": "body-def"},
            },
        )
        refs = _definition_refs(cfg)
        assert ("source", "body-def") in refs

    def test_write_api_with_form_urlencoded_runtime_value_in_body(self):
        cfg = WriteApiConfigurationCommandDto(
            commandCode="writeApi",
            commandType="action",
            method="POST",
            url="https://api.example.com",
            bodyType="formUrlEncoded",
            body={
                "access_token": {
                    "kind": "runtimeValue",
                    "definitionId": "body-def",
                    "fieldPath": "payload.access_token",
                },
            },
        )
        refs = _definition_refs(cfg)
        assert ("source", "body-def") in refs

    def test_no_refs_for_all_literals(self):
        cfg = ReadApiConfigurationCommandDto(
            commandCode="readApi",
            commandType="action",
            url="https://api.example.com",
            queryParams={"page": "1"},
            headers={"Accept": "application/json"},
        )
        refs = _definition_refs(cfg)
        assert len(refs) == 0


class TestFormUrlEncodedValidationGraph:
    def test_plan_definitions_rejects_dataset_runtime_value_in_form_urlencoded_body(self):
        raw_commands = [
            {
                "id": "cmd-http",
                "order": 2,
                "cfg": {
                    "commandCode": "writeApi",
                    "commandType": "action",
                    "method": "POST",
                    "url": "https://api.example.com/orders",
                    "bodyType": "formUrlEncoded",
                    "body": {
                        "datasetField": {
                            "kind": "runtimeValue",
                            "definitionId": "def-dataset",
                        }
                    },
                },
            }
        ]
        initial_visible = {
            "def-dataset": PlannedDefinition(
                definition_id="def-dataset",
                command_id="cmd-def",
                command_order=1,
                section_type="test",
                name="rows",
                context_scope="local",
                value_type="dataset",
            )
        }

        with pytest.raises(ValueError, match="incompatible type 'dataset'"):
            plan_definitions_for_commands(
                raw_commands,
                section_type="test",
                initial_visible=initial_visible,
            )

    def test_plan_definitions_allows_json_runtime_value_in_form_urlencoded_body(self):
        raw_commands = [
            {
                "id": "cmd-http",
                "order": 2,
                "cfg": {
                    "commandCode": "writeApi",
                    "commandType": "action",
                    "method": "POST",
                    "url": "https://api.example.com/orders",
                    "bodyType": "formUrlEncoded",
                    "body": {
                        "token": {
                            "kind": "runtimeValue",
                            "definitionId": "def-json",
                            "fieldPath": "payload.access_token",
                        }
                    },
                },
            }
        ]
        initial_visible = {
            "def-json": PlannedDefinition(
                definition_id="def-json",
                command_id="cmd-def",
                command_order=1,
                section_type="test",
                name="response",
                context_scope="local",
                value_type="json",
            )
        }

        planned, visible = plan_definitions_for_commands(
            raw_commands,
            section_type="test",
            initial_visible=initial_visible,
        )

        assert planned == []
        assert "def-json" in visible
