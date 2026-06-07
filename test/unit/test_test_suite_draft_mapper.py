import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "app" / "ui"
if str(UI_ROOT) not in sys.path:
    sys.path.append(str(UI_ROOT))


from test_suites.services.draft_mapper import build_test_suite_draft, draft_to_test_suite_payload


def test_build_test_suite_draft_hydrates_ref_based_commands_for_ui_editing():
    payload = {
        "id": "suite-1",
        "description": "suite",
        "hooks": [
            {
                "hook_phase": "before-all",
                "description": "before all",
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
        "tests": [
            {
                "description": "test 1",
                "commands": [
                    {
                        "order": 1,
                        "description": "send message",
                        "cfg": {
                            "commandCode": "sendMessageQueue",
                            "commandType": "action",
                            "queue_id": "queue-1",
                            "sourceConstantRef": {"definitionId": "def-rows"},
                            "resultConstant": {
                                "definitionId": "def-publish-result",
                                "name": "publishResult",
                                "valueType": "json",
                            },
                        },
                    },
                    {
                        "order": 2,
                        "description": "assert publish result",
                        "cfg": {
                            "commandCode": "jsonEquals",
                            "commandType": "assert",
                            "actualConstantRef": {"definitionId": "def-publish-result"},
                            "expected": {"ok": True},
                        },
                    },
                ],
            }
        ],
    }

    draft = build_test_suite_draft(payload)

    before_all_cfg = draft["hooks"]["before-all"]["operations"][0]["configuration_json"]
    send_cfg = draft["tests"][0]["operations"][0]["configuration_json"]
    assert_cfg = draft["tests"][0]["operations"][1]["configuration_json"]

    assert before_all_cfg["definitionId"] == "def-rows"
    assert send_cfg["source"] == "$.global.constants.rows"
    assert send_cfg["result_target"] == "$.result.constants.publishResult"
    assert assert_cfg["actual"] == "$.result.constants.publishResult"


def test_build_test_suite_draft_uses_stable_ui_keys_after_reload():
    payload = {
        "id": "suite-1",
        "description": "suite",
        "hooks": [
            {
                "hook_phase": "before-all",
                "description": "before all",
                "commands": [
                    {
                        "order": 1,
                        "description": "load token",
                        "cfg": {
                            "commandCode": "readApi",
                            "commandType": "action",
                            "url": "https://api.example.com/token",
                        },
                    }
                ],
            }
        ],
        "tests": [
            {
                "id": "test-1",
                "description": "test",
                "position": 1,
                "commands": [
                    {
                        "order": 1,
                        "description": "submit form",
                        "cfg": {
                            "commandCode": "writeApi",
                            "commandType": "action",
                            "method": "POST",
                            "url": "https://api.example.com/form",
                        },
                    }
                ],
            }
        ],
    }

    first = build_test_suite_draft(payload)
    second = build_test_suite_draft(payload)

    assert first["hooks"]["before-all"]["_ui_key"] == second["hooks"]["before-all"]["_ui_key"]
    assert (
        first["hooks"]["before-all"]["operations"][0]["_ui_key"]
        == second["hooks"]["before-all"]["operations"][0]["_ui_key"]
    )
    assert first["tests"][0]["_ui_key"] == second["tests"][0]["_ui_key"]
    assert first["tests"][0]["operations"][0]["_ui_key"] == second["tests"][0]["operations"][0]["_ui_key"]


def test_draft_to_test_suite_payload_converts_legacy_suite_editor_fields_to_qsm_044_contract():
    draft = {
        "id": "suite-1",
        "description": "suite",
        "hooks": {
            "before-all": {
                "kind": "hook",
                "hook_phase": "before-all",
                "description": "before all",
                "operations": [
                    {
                        "order": 1,
                        "description": "load rows",
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "rows",
                            "context": "global",
                            "sourceType": "jsonArray",
                            "json_array_id": "json-array-1",
                        },
                    }
                ],
            }
        },
        "tests": [
            {
                "kind": "test",
                "description": "test 1",
                "operations": [
                    {
                        "order": 1,
                        "description": "send message",
                        "configuration_json": {
                            "commandCode": "sendMessageQueue",
                            "commandType": "action",
                            "queue_id": "queue-1",
                            "source": "$.global.constants.rows",
                            "result_target": "$.result.constants.publishResult",
                        },
                    },
                    {
                        "order": 2,
                        "description": "assert publish result",
                        "configuration_json": {
                            "commandCode": "jsonEquals",
                            "commandType": "assert",
                            "actual": "$.result.constants.publishResult",
                            "expected": {"ok": True},
                        },
                    },
                ],
            }
        ],
    }

    payload = draft_to_test_suite_payload(draft)

    init_cfg = payload["hooks"][0]["commands"][0]["cfg"]
    send_cfg = payload["tests"][0]["commands"][0]["cfg"]
    assert_cfg = payload["tests"][0]["commands"][1]["cfg"]

    assert init_cfg["commandCode"] == "setVariable"
    assert init_cfg["definitionId"]
    assert send_cfg["inputRef"]["kind"] == "runtimeValue"
    assert send_cfg["inputRef"]["definitionId"] == init_cfg["definitionId"]
    assert send_cfg["resultConstant"]["name"] == "publishResult"
    assert send_cfg["resultConstant"]["definitionId"]
    assert assert_cfg["actualRef"]["kind"] == "runtimeValue"
    assert assert_cfg["actualRef"]["definitionId"] == send_cfg["resultConstant"]["definitionId"]


def test_draft_to_test_suite_payload_recomputes_stale_refs_after_command_edit():
    payload = {
        "id": "suite-1",
        "description": "suite",
        "hooks": [
            {
                "hook_phase": "before-all",
                "description": "before all",
                "commands": [
                    {
                        "order": 1,
                        "description": "load rows",
                        "cfg": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "definitionId": "def-rows-original",
                            "name": "rows",
                            "context": "global",
                            "sourceType": "jsonArray",
                            "json_array_id": "json-array-1",
                        },
                    }
                ],
            }
        ],
        "tests": [
            {
                "description": "test 1",
                "commands": [
                    {
                        "order": 1,
                        "description": "send message",
                        "cfg": {
                            "commandCode": "sendMessageQueue",
                            "commandType": "action",
                            "queue_id": "queue-1",
                            "sourceConstantRef": {"definitionId": "def-rows-original"},
                        },
                    }
                ],
            }
        ],
    }

    draft = build_test_suite_draft(payload)
    init_cfg = draft["hooks"]["before-all"]["operations"][0]["configuration_json"]
    send_cfg = draft["tests"][0]["operations"][0]["configuration_json"]

    init_cfg.pop("definitionId", None)
    send_cfg["sourceConstantRef"] = {"definitionId": "stale-definition-id"}
    send_cfg["source"] = "$.global.constants.rows"

    serialized_payload = draft_to_test_suite_payload(draft)

    serialized_init_cfg = serialized_payload["hooks"][0]["commands"][0]["cfg"]
    serialized_send_cfg = serialized_payload["tests"][0]["commands"][0]["cfg"]

    assert serialized_init_cfg["definitionId"]
    assert serialized_send_cfg["inputRef"]["kind"] == "runtimeValue"
    assert serialized_send_cfg["inputRef"]["definitionId"] == serialized_init_cfg["definitionId"]


def test_draft_to_test_suite_payload_recomputes_form_urlencoded_runtime_refs():
    draft = {
        "id": "suite-1",
        "description": "suite",
        "tests": [
            {
                "kind": "test",
                "description": "test 1",
                "operations": [
                    {
                        "order": 1,
                        "description": "load token",
                        "configuration_json": {
                            "commandCode": "readApi",
                            "commandType": "action",
                            "url": "https://api.example.com/token",
                            "result_target": "$.result.constants.tokenResponse",
                        },
                    },
                    {
                        "order": 2,
                        "description": "submit form",
                        "configuration_json": {
                            "commandCode": "writeApi",
                            "commandType": "action",
                            "method": "POST",
                            "url": "https://api.example.com/form",
                            "bodyType": "formUrlEncoded",
                            "body": {
                                "access_token": {
                                    "kind": "runtimeValue",
                                    "definitionId": "$.result.constants.tokenResponse",
                                    "fieldPath": "payload.access_token",
                                },
                                "grant_type": {
                                    "kind": "literal",
                                    "value": "client_credentials",
                                },
                            },
                        },
                    },
                ],
            }
        ],
    }

    payload = draft_to_test_suite_payload(draft)

    read_cfg = payload["tests"][0]["commands"][0]["cfg"]
    write_cfg = payload["tests"][0]["commands"][1]["cfg"]
    assert read_cfg["resultConstant"]["name"] == "tokenResponse"
    assert write_cfg["body"]["access_token"]["definitionId"] == read_cfg["resultConstant"]["definitionId"]
    assert write_cfg["body"]["access_token"]["fieldPath"] == "payload.access_token"


def test_draft_to_test_suite_payload_uses_stable_api_result_target_ids_in_hooks():
    draft = {
        "id": "suite-1",
        "description": "suite",
        "hooks": {
            "before-all": {
                "kind": "hook",
                "hook_phase": "before-all",
                "description": "before all",
                "operations": [
                    {
                        "order": 1,
                        "description": "load token",
                        "configuration_json": {
                            "commandCode": "readApi",
                            "commandType": "action",
                            "url": "https://api.example.com/token",
                            "result_target": "$.result.constants.tokenResponse",
                        },
                    },
                    {
                        "order": 2,
                        "description": "submit form",
                        "configuration_json": {
                            "commandCode": "writeApi",
                            "commandType": "action",
                            "method": "POST",
                            "url": "https://api.example.com/form",
                            "bodyType": "json",
                            "body": {
                                "kind": "runtimeValue",
                                "definitionId": "$.result.constants.tokenResponse",
                                "fieldPath": "payload",
                            },
                        },
                    },
                ],
            }
        },
        "tests": [],
    }

    payload = draft_to_test_suite_payload(draft)

    read_cfg = payload["hooks"][0]["commands"][0]["cfg"]
    write_cfg = payload["hooks"][0]["commands"][1]["cfg"]
    assert read_cfg["resultConstant"]["definitionId"] == "$.result.constants.tokenResponse"
    assert write_cfg["body"]["definitionId"] == "$.result.constants.tokenResponse"


def test_build_test_suite_draft_hydrates_form_urlencoded_runtime_refs_for_ui_editing():
    payload = {
        "id": "suite-1",
        "description": "suite",
        "hooks": [
            {
                "hook_phase": "before-all",
                "description": "before all",
                "commands": [
                    {
                        "order": 1,
                        "description": "load token",
                        "cfg": {
                            "commandCode": "readApi",
                            "commandType": "action",
                            "url": "https://api.example.com/token",
                            "resultConstant": {
                                "definitionId": "def-token-response",
                                "name": "tokenResponse",
                                "valueType": "json",
                            },
                        },
                    },
                    {
                        "order": 2,
                        "description": "submit form",
                        "cfg": {
                            "commandCode": "writeApi",
                            "commandType": "action",
                            "method": "POST",
                            "url": "https://api.example.com/form",
                            "bodyType": "formUrlEncoded",
                            "body": {
                                "access_token": {
                                    "kind": "runtimeValue",
                                    "definitionId": "def-token-response",
                                    "fieldPath": "payload.access_token",
                                }
                            },
                        },
                    },
                ],
            }
        ],
        "tests": [],
    }

    draft = build_test_suite_draft(payload)

    write_cfg = draft["hooks"]["before-all"]["operations"][1]["configuration_json"]
    assert write_cfg["body"]["access_token"]["definitionId"] == "$.result.constants.tokenResponse"

    serialized_payload = draft_to_test_suite_payload(draft)
    read_cfg = serialized_payload["hooks"][0]["commands"][0]["cfg"]
    serialized_write_cfg = serialized_payload["hooks"][0]["commands"][1]["cfg"]
    assert serialized_write_cfg["body"]["access_token"]["definitionId"] == read_cfg["resultConstant"]["definitionId"]


def test_draft_to_test_suite_payload_preserves_expected_ref_for_json_contains_round_trip():
    draft = {
        "id": "suite-contains-ref",
        "description": "suite",
        "hooks": {
            "before-all": {
                "kind": "hook",
                "hook_phase": "before-all",
                "description": "before all",
                "operations": [
                    {
                        "order": 1,
                        "description": "expected payload",
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "expectedPayload",
                            "context": "global",
                            "sourceType": "json",
                            "value": {"id": 1, "code": "A"},
                        },
                    },
                    {
                        "order": 2,
                        "description": "actual payload",
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "actualPayload",
                            "context": "global",
                            "sourceType": "json",
                            "value": {"id": 1, "code": "A", "extra": True},
                        },
                    },
                ],
            }
        },
        "tests": [
            {
                "kind": "test",
                "description": "contains",
                "operations": [
                    {
                        "order": 1,
                        "description": "assert contains",
                        "configuration_json": {
                            "commandCode": "jsonContains",
                            "commandType": "assert",
                            "actual": "$.global.constants.actualPayload",
                            "expected": {"$ref": "$.global.constants.expectedPayload"},
                            "compare_keys": ["id", "code"],
                        },
                    }
                ],
            }
        ],
    }

    payload = draft_to_test_suite_payload(draft)
    assert_cfg = payload["tests"][0]["commands"][0]["cfg"]

    assert assert_cfg["actualRef"]["kind"] == "runtimeValue"
    assert assert_cfg["actualRef"]["definitionId"]
    assert assert_cfg["expected"] == {"$ref": "$.global.constants.expectedPayload"}
    assert assert_cfg["compare_keys"] == ["id", "code"]

    round_trip = build_test_suite_draft(payload)
    round_trip_cfg = round_trip["tests"][0]["operations"][0]["configuration_json"]

    assert round_trip_cfg["actual"] == "$.global.constants.actualPayload"
    assert round_trip_cfg["expected"] == {"$ref": "$.global.constants.expectedPayload"}
    assert round_trip_cfg["compare_keys"] == ["id", "code"]


def test_draft_mapper_round_trips_dataset_parameter_constant_bindings():
    payload = {
        "id": "suite-dataset-params",
        "description": "suite",
        "hooks": [
            {
                "hook_phase": "before-all",
                "description": "before all",
                "commands": [
                    {
                        "order": 1,
                        "description": "pipeline id",
                        "cfg": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "definitionId": "def-pipeline",
                            "name": "pipelineId",
                            "context": "global",
                            "sourceType": "raw",
                            "value": "PIPE-01",
                        },
                    }
                ],
            }
        ],
        "tests": [
            {
                "description": "test 1",
                "commands": [
                    {
                        "order": 1,
                        "description": "dataset rows",
                        "cfg": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "definitionId": "def-dataset",
                            "name": "rows",
                            "context": "local",
                            "sourceType": "dataset",
                            "dataset_id": "dataset-1",
                            "parameters": {
                                "pipelineId": {
                                    "kind": "constant_ref",
                                    "definitionId": "def-pipeline",
                                },
                                "snapshotAt": {
                                    "kind": "built_in",
                                    "resolver": "$now",
                                },
                            },
                        },
                    }
                ],
            }
        ],
    }

    draft = build_test_suite_draft(payload)
    round_trip_cfg = draft["tests"][0]["operations"][0]["configuration_json"]
    assert round_trip_cfg["parameters"]["pipelineId"] == {
        "kind": "constant_path",
        "path": "$.global.constants.pipelineId",
    }

    serialized_payload = draft_to_test_suite_payload(draft)
    serialized_cfg = serialized_payload["tests"][0]["commands"][0]["cfg"]
    assert serialized_cfg["parameters"]["pipelineId"] == {
        "kind": "constant_ref",
        "definitionId": "def-pipeline",
    }
    assert serialized_cfg["parameters"]["snapshotAt"] == {
        "kind": "built_in",
        "resolver": "$now",
    }
