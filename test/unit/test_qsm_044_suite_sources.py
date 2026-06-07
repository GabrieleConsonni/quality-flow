from pydantic import ValidationError

from app.elaborations.models.dtos.configuration_command_dto import (
    CommandCode,
    convert_to_config_command_type,
)
from app.elaborations.models.dtos.test_suite_dto import (
    CreateSuiteItemDto,
    CreateTestSuiteDto,
)
from app.elaborations.services.suite_source_registry import (
    build_visible_sources_for_suite_item,
    validate_suite_sources_graph,
)


def test_create_suite_item_dto_rejects_duplicate_source_codes():
    try:
        CreateSuiteItemDto(
            kind="test",
            description="test",
            sources=[
                {"sourceCode": "orders", "sourceType": "jsonArray", "jsonArrayId": "ja-1"},
                {
                    "sourceCode": "orders",
                    "sourceType": "dataset",
                    "datasetId": "ds-1",
                    "perimeter": {},
                },
            ],
            commands=[],
        )
    except ValidationError as exc:
        assert "Duplicate sourceCode 'orders'" in str(exc)
    else:
        raise AssertionError("Expected duplicate sourceCode validation error.")


def test_create_suite_item_dto_rejects_queue_as_source_type():
    try:
        CreateSuiteItemDto(
            kind="test",
            description="test",
            sources=[
                {"sourceCode": "queuePayload", "sourceType": "sqsQueue", "queueId": "q-1"},
            ],
            commands=[],
        )
    except ValidationError as exc:
        assert exc.errors()
    else:
        raise AssertionError("Expected queue source validation error.")


def test_build_visible_sources_for_suite_item_applies_batch_visibility_rules():
    before_all = CreateSuiteItemDto(
        kind="hook",
        hook_phase="before-all",
        description="before all",
        sources=[{"sourceCode": "suiteRows", "sourceType": "jsonArray", "jsonArrayId": "ja-1"}],
        commands=[],
    )
    before_each = CreateSuiteItemDto(
        kind="hook",
        hook_phase="before-each",
        description="before each",
        sources=[
            {
                "sourceCode": "caseRows",
                "sourceType": "dataset",
                "datasetId": "ds-1",
                "perimeter": {},
            }
        ],
        commands=[],
    )
    test_item = CreateSuiteItemDto(
        kind="test",
        description="test",
        sources=[{"sourceCode": "localRows", "sourceType": "jsonArray", "jsonArrayId": "ja-2"}],
        commands=[],
    )

    visible = build_visible_sources_for_suite_item(
        before_all=before_all,
        before_each=before_each,
        current_item=test_item,
    )

    assert set(visible) == {"suiteRows", "caseRows", "localRows"}


def test_validate_suite_sources_graph_requires_visible_source_refs():
    dto = CreateTestSuiteDto(
        description="suite",
        hooks=[
            {
                "kind": "hook",
                "hook_phase": "before-all",
                "description": "before all",
                "sources": [
                    {"sourceCode": "suiteRows", "sourceType": "jsonArray", "jsonArrayId": "ja-1"}
                ],
                "commands": [],
            }
        ],
        tests=[
            {
                "kind": "test",
                "description": "test",
                "sources": [],
                "commands": [
                    {
                        "order": 1,
                        "description": "send source",
                        "cfg": {
                            "commandCode": "sendMessageQueue",
                            "commandType": "action",
                            "queue_id": "queue-1",
                            "inputRef": {"kind": "source", "sourceCode": "missingSource"},
                        },
                    }
                ],
            }
        ],
    )

    try:
        validate_suite_sources_graph(dto)
    except ValueError as exc:
        assert "missingSource" in str(exc)
    else:
        raise AssertionError("Expected missing source visibility validation error.")


def test_convert_to_config_command_type_handles_new_input_refs():
    cfg = convert_to_config_command_type(
        {
            "commandCode": CommandCode.SEND_MESSAGE_QUEUE.value,
            "commandType": "action",
            "queue_id": "queue-1",
            "inputRef": {"kind": "source", "sourceCode": "suiteRows"},
        }
    )

    assert cfg.commandCode == CommandCode.SEND_MESSAGE_QUEUE.value
    assert cfg.inputRef is not None
    assert cfg.inputRef.kind == "source"
    assert cfg.inputRef.sourceCode == "suiteRows"
