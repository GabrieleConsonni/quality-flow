"""Snapshot-style unit tests for the send_verify template generator."""

from __future__ import annotations

import pytest

from app.elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
    CommandCode,
    InputRefKind,
    QueryDatabaseConfigurationCommandDto,
    ReceiveQueueConfigurationCommandDto,
    SendMessageQueueConfigurationCommandDto,
    SetVariableConfigurationCommandDto,
    SleepConfigurationCommandDto,
)
from app.elaborations.models.enums.template_kind import TemplateKind
from app.templating import InvalidTemplateConfigError, template_registry


def _generate(config: dict):
    return template_registry.generate_commands(TemplateKind.SEND_VERIFY.value, config)


def test_send_verify_minimum_set_no_asserts_emits_setvar_send_sleep():
    commands = _generate(
        {
            "queue_id": "queue-1",
            "payload": {"kind": "json_inline", "value": {"hello": "world"}},
            "wait_ms": 500,
            "asserts": [],
        }
    )

    assert [c.order for c in commands] == [0, 1, 2]
    assert isinstance(commands[0].cfg, SetVariableConfigurationCommandDto)
    assert commands[0].cfg.valueType == "json"
    assert commands[0].cfg.value == {"hello": "world"}

    assert isinstance(commands[1].cfg, SendMessageQueueConfigurationCommandDto)
    assert commands[1].cfg.queue_id == "queue-1"
    assert commands[1].cfg.inputRef.kind == InputRefKind.RUNTIME_VALUE.value
    assert commands[1].cfg.inputRef.definitionId == commands[0].cfg.definitionId

    assert isinstance(commands[2].cfg, SleepConfigurationCommandDto)
    assert commands[2].cfg.duration == 500


def test_send_verify_skips_sleep_when_wait_ms_is_zero():
    commands = _generate(
        {
            "queue_id": "queue-1",
            "payload": {"kind": "json_inline", "value": {"a": 1}},
            "wait_ms": 0,
            "asserts": [],
        }
    )
    assert len(commands) == 2
    assert not isinstance(commands[1].cfg, SleepConfigurationCommandDto)


def test_send_verify_queue_assert_emits_receive_plus_assert():
    commands = _generate(
        {
            "queue_id": "queue-1",
            "payload": {"kind": "json_inline", "value": {"foo": "bar"}},
            "wait_ms": 250,
            "asserts": [
                {"target": "queue", "queue_id": "queue-out", "operator": "exists"},
            ],
        }
    )

    # setVariable, sendMessageQueue, sleep, receiveQueue, assertJsonNotEmpty
    assert len(commands) == 5
    receive_cmd = commands[3].cfg
    assert isinstance(receive_cmd, ReceiveQueueConfigurationCommandDto)
    assert receive_cmd.queue_id == "queue-out"
    assert receive_cmd.resultConstant is not None

    assert_cmd = commands[4].cfg
    assert isinstance(assert_cmd, AssertConfigurationCommandDto)
    assert assert_cmd.commandCode == CommandCode.JSON_NOT_EMPTY.value
    assert assert_cmd.actualRef.definitionId == receive_cmd.resultConstant.definitionId


def test_send_verify_database_assert_emits_query_plus_assert():
    commands = _generate(
        {
            "queue_id": "queue-1",
            "payload": {"kind": "json_inline", "value": {"id": 42}},
            "wait_ms": 0,
            "asserts": [
                {
                    "target": "database",
                    "connection_id": "conn-1",
                    "database_query": "SELECT 1 AS r",
                    "operator": "equals",
                    "expected": [{"r": 1}],
                },
            ],
        }
    )

    # setVariable, sendMessageQueue, queryDatabase, assertJsonEquals
    assert len(commands) == 4
    query_cmd = commands[2].cfg
    assert isinstance(query_cmd, QueryDatabaseConfigurationCommandDto)
    assert query_cmd.connection_id == "conn-1"
    assert query_cmd.query == "SELECT 1 AS r"

    assert_cmd = commands[3].cfg
    assert isinstance(assert_cmd, AssertConfigurationCommandDto)
    assert assert_cmd.commandCode == CommandCode.JSON_EQUALS.value
    assert assert_cmd.expected == [{"r": 1}]
    assert assert_cmd.actualRef.definitionId == query_cmd.resultConstant.definitionId


def test_send_verify_target_none_assert_is_skipped():
    commands = _generate(
        {
            "queue_id": "queue-1",
            "payload": {"kind": "json_inline", "value": {"a": 1}},
            "wait_ms": 100,
            "asserts": [
                {"target": "none", "operator": "exists"},
            ],
        }
    )
    # setVariable, send, sleep (no read/assert because target=none).
    assert len(commands) == 3


def test_send_verify_rejects_missing_queue_id():
    with pytest.raises(InvalidTemplateConfigError):
        _generate({"payload": {"kind": "json_inline", "value": {}}, "wait_ms": 0})


def test_send_verify_rejects_unsupported_payload_kind():
    with pytest.raises(InvalidTemplateConfigError):
        _generate(
            {
                "queue_id": "queue-1",
                "payload": {"kind": "json_array_ref", "value": "abc"},
            }
        )


def test_send_verify_rejects_invalid_operator():
    with pytest.raises(InvalidTemplateConfigError):
        _generate(
            {
                "queue_id": "queue-1",
                "payload": {"kind": "json_inline", "value": {}},
                "wait_ms": 0,
                "asserts": [{"target": "queue", "queue_id": "q", "operator": "matches_schema"}],
            }
        )


def test_send_verify_rejects_equals_without_expected():
    with pytest.raises(InvalidTemplateConfigError):
        _generate(
            {
                "queue_id": "queue-1",
                "payload": {"kind": "json_inline", "value": {}},
                "wait_ms": 0,
                "asserts": [{"target": "queue", "queue_id": "q", "operator": "equals"}],
            }
        )
