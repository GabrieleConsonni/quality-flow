import pytest

from app.elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
    DataConfigurationOperationDto,
    PublishConfigurationOperationDto,
    ReadApiConfigurationCommandDto,
    WriteApiConfigurationCommandDto,
)
from app.elaborations.models.dtos.test_suite_dto import CreateTestSuiteDto
from app.elaborations.services.constants.command_constant_definition_registry import (
    validate_suite_constant_graph,
)
from app.elaborations.services.operations.command_policy_validator import (
    validate_operation_policy,
)
from app.elaborations.services.operations.command_scope import (
    SCOPE_MOCK_POST_RESPONSE,
    SCOPE_MOCK_PRE_RESPONSE,
    SCOPE_TEST,
)


def test_policy_blocks_global_target_in_test_scope():
    cfg = DataConfigurationOperationDto(
        definitionId="def-rows",
        name="rows",
        context="global",
        sourceType="json",
        data=[{"id": 1}],
        target="$.global.rows",
    )

    with pytest.raises(
        ValueError,
        match="Global context is immutable during test execution.",
    ):
        validate_operation_policy(cfg, SCOPE_TEST)


def test_policy_blocks_side_effect_command_in_mock_pre_response():
    cfg = PublishConfigurationOperationDto(
        queue_id="queue-1",
        sourceConstantRef={"definitionId": "def-source"},
    )

    with pytest.raises(
        ValueError,
        match="not allowed in scope 'mock.preResponse'",
    ):
        validate_operation_policy(cfg, SCOPE_MOCK_PRE_RESPONSE)


def test_policy_allows_assert_in_mock_pre_response():
    cfg = AssertConfigurationCommandDto(
        commandCode="jsonEmpty",
        commandType="assert",
        actualConstantRef={"definitionId": "def-actual"},
    )

    contract = validate_operation_policy(cfg, SCOPE_MOCK_PRE_RESPONSE)

    assert contract.family == "assert"


def test_policy_blocks_read_api_in_mock_pre_response():
    cfg = ReadApiConfigurationCommandDto(
        commandCode="readApi",
        commandType="action",
        url="https://api.example.com/orders",
    )

    with pytest.raises(
        ValueError,
        match="not allowed in scope 'mock.preResponse'",
    ):
        validate_operation_policy(cfg, SCOPE_MOCK_PRE_RESPONSE)


def test_policy_allows_write_api_in_mock_post_response():
    cfg = WriteApiConfigurationCommandDto(
        commandCode="writeApi",
        commandType="action",
        method="POST",
        url="https://api.example.com/orders",
    )

    contract = validate_operation_policy(cfg, SCOPE_MOCK_POST_RESPONSE)

    assert contract.family == "action"


def test_validate_suite_constant_graph_allows_test_to_read_before_all_global_constant():
    dto = CreateTestSuiteDto(
        description="suite",
        hooks=[
            {
                "kind": "hook",
                "hook_phase": "before-all",
                "commands": [
                    {
                        "order": 1,
                        "description": "load rows",
                        "cfg": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "definitionId": "def-rows",
                            "name": "rows",
                            "context": "global",
                            "sourceType": "jsonArray",
                            "json_array_id": "json-array-1",
                        },
                    }
                ],
            }
        ],
        tests=[
            {
                "kind": "test",
                "description": "test 1",
                "commands": [
                    {
                        "order": 1,
                        "description": "save rows",
                        "cfg": {
                            "commandCode": "saveTable",
                            "commandType": "action",
                            "table_name": "tmp_rows",
                            "sourceConstantRef": {"definitionId": "def-rows"},
                        },
                    }
                ],
            }
        ],
    )

    validate_suite_constant_graph(dto)


def test_validate_suite_constant_graph_allows_send_message_queue_to_read_raw_constant():
    dto = CreateTestSuiteDto(
        description="suite",
        tests=[
            {
                "kind": "test",
                "description": "test 1",
                "commands": [
                    {
                        "order": 1,
                        "description": "build payload",
                        "cfg": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "definitionId": "def-message",
                            "name": "message",
                            "context": "local",
                            "sourceType": "raw",
                            "value": "hello world",
                        },
                    },
                    {
                        "order": 2,
                        "description": "publish payload",
                        "cfg": {
                            "commandCode": "sendMessageQueue",
                            "commandType": "action",
                            "queue_id": "queue-1",
                            "sourceConstantRef": {"definitionId": "def-message"},
                        },
                    },
                ],
            }
        ],
    )

    validate_suite_constant_graph(dto)


def test_validate_suite_constant_graph_allows_send_message_queue_to_read_dataset_constant():
    dto = CreateTestSuiteDto(
        description="suite",
        tests=[
            {
                "kind": "test",
                "description": "test 1",
                "commands": [
                    {
                        "order": 1,
                        "description": "bind dataset",
                        "cfg": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "definitionId": "def-message-dataset",
                            "name": "messageDataset",
                            "context": "local",
                            "sourceType": "dataset",
                            "dataset_id": "dataset-1",
                        },
                    },
                    {
                        "order": 2,
                        "description": "publish payloads",
                        "cfg": {
                            "commandCode": "sendMessageQueue",
                            "commandType": "action",
                            "queue_id": "queue-1",
                            "sourceConstantRef": {"definitionId": "def-message-dataset"},
                        },
                    },
                ],
            }
        ],
    )

    validate_suite_constant_graph(dto)

