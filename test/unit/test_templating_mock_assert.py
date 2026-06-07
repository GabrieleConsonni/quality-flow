"""Snapshot-style unit tests for the mock_assert template generator."""

from __future__ import annotations

import pytest

from app.elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
    CommandCode,
    QueryDatabaseConfigurationCommandDto,
    ReceiveQueueConfigurationCommandDto,
    SleepConfigurationCommandDto,
)
from app.elaborations.models.enums.template_kind import TemplateKind
from app.templating import InvalidTemplateConfigError, template_registry


def _generate(config: dict):
    return template_registry.generate_commands(TemplateKind.MOCK_ASSERT.value, config)


def test_mock_assert_queue_target_emits_sleep_receive_assert():
    commands = _generate(
        {
            "wait_ms": 750,
            "asserts": [
                {"target": "queue", "queue_id": "queue-out", "operator": "exists"},
            ],
        }
    )

    assert [c.order for c in commands] == [0, 1, 2]
    assert isinstance(commands[0].cfg, SleepConfigurationCommandDto)
    assert commands[0].cfg.duration == 750

    receive_cmd = commands[1].cfg
    assert isinstance(receive_cmd, ReceiveQueueConfigurationCommandDto)
    assert receive_cmd.queue_id == "queue-out"

    assert_cmd = commands[2].cfg
    assert isinstance(assert_cmd, AssertConfigurationCommandDto)
    assert assert_cmd.commandCode == CommandCode.JSON_NOT_EMPTY.value
    assert assert_cmd.actualRef.definitionId == receive_cmd.resultConstant.definitionId


def test_mock_assert_database_target_with_equals_emits_query_assert():
    commands = _generate(
        {
            "wait_ms": 0,
            "asserts": [
                {
                    "target": "database",
                    "connection_id": "conn-1",
                    "database_query": "SELECT COUNT(*) AS c FROM orders",
                    "operator": "equals",
                    "expected": [{"c": 1}],
                },
            ],
        }
    )

    # wait_ms=0 → no sleep step
    assert len(commands) == 2
    query_cmd = commands[0].cfg
    assert isinstance(query_cmd, QueryDatabaseConfigurationCommandDto)
    assert query_cmd.query == "SELECT COUNT(*) AS c FROM orders"

    assert_cmd = commands[1].cfg
    assert isinstance(assert_cmd, AssertConfigurationCommandDto)
    assert assert_cmd.commandCode == CommandCode.JSON_EQUALS.value
    assert assert_cmd.expected == [{"c": 1}]


def test_mock_assert_requires_at_least_one_assert():
    with pytest.raises(InvalidTemplateConfigError):
        _generate({"wait_ms": 100, "asserts": []})


def test_mock_assert_rejects_target_none():
    with pytest.raises(InvalidTemplateConfigError):
        _generate(
            {
                "wait_ms": 0,
                "asserts": [{"target": "none", "operator": "exists"}],
            }
        )


def test_mock_assert_multiple_asserts_chain_in_order():
    commands = _generate(
        {
            "wait_ms": 0,
            "asserts": [
                {"target": "queue", "queue_id": "queue-a", "operator": "exists"},
                {
                    "target": "database",
                    "connection_id": "conn-1",
                    "database_query": "SELECT 1",
                    "operator": "exists",
                },
            ],
        }
    )
    # 4 commands: receive-a, assert-a, query, assert-q
    assert len(commands) == 4
    assert isinstance(commands[0].cfg, ReceiveQueueConfigurationCommandDto)
    assert isinstance(commands[1].cfg, AssertConfigurationCommandDto)
    assert isinstance(commands[2].cfg, QueryDatabaseConfigurationCommandDto)
    assert isinstance(commands[3].cfg, AssertConfigurationCommandDto)
    # actualRef of assert[1] points to commands[2] (query) result
    assert commands[3].cfg.actualRef.definitionId == commands[2].cfg.resultConstant.definitionId
