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


from ui.test_suites.components import (
    advanced_suite_editor_settings_container,
    suite_editor_component,
    test_editor_component,
)
from ui.elaborations_shared.components import auth_editor
from ui.elaborations_shared.components import test_command_component


def _reset_session_state():
    sys.modules["streamlit"].session_state.clear()


def test_normalize_authorization_config_resets_legacy_payloads():
    _reset_session_state()

    assert auth_editor.normalize_authorization_config({"header": "Authorization"}) == {}
    assert auth_editor.normalize_authorization_config(None) == {}


def test_collect_auth_editor_value_for_no_auth_returns_empty_dict():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["auth_test_type"] = auth_editor.AUTH_TYPE_NONE

    value, error = auth_editor.collect_auth_editor_value("auth_test")

    assert error is None
    assert value == {}


def test_collect_auth_editor_value_for_basic_auth():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["auth_test_type"] = auth_editor.AUTH_TYPE_BASIC
    streamlit_module.session_state["auth_test_username"] = "alice"
    streamlit_module.session_state["auth_test_password"] = "secret"

    value, error = auth_editor.collect_auth_editor_value("auth_test")

    assert error is None
    assert value == {
        "type": "basic",
        "username": "alice",
        "password": "secret",
    }


def test_collect_auth_editor_value_for_bearer_auth_requires_token():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["auth_test_type"] = auth_editor.AUTH_TYPE_BEARER
    streamlit_module.session_state["auth_test_token"] = ""

    value, error = auth_editor.collect_auth_editor_value("auth_test")

    assert value == {}
    assert error == "Auth token is required."


def test_collect_auth_editor_value_for_api_key_auth():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["auth_test_type"] = auth_editor.AUTH_TYPE_API_KEY
    streamlit_module.session_state["auth_test_username"] = "service-user"
    streamlit_module.session_state["auth_test_apiKey"] = "abc123"
    streamlit_module.session_state["auth_test_authEndpoint"] = "https://auth.example.com/token"

    value, error = auth_editor.collect_auth_editor_value("auth_test")

    assert error is None
    assert value == {
        "type": "apiKey",
        "username": "service-user",
        "apiKey": "abc123",
        "authEndpoint": "https://auth.example.com/token",
    }


def test_collect_auth_editor_value_for_oauth2_auth():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["auth_test_type"] = auth_editor.AUTH_TYPE_OAUTH2
    streamlit_module.session_state["auth_test_tokenUrl"] = "https://auth.example.com/oauth/token"
    streamlit_module.session_state["auth_test_clientId"] = "client-id"
    streamlit_module.session_state["auth_test_clientSecret"] = "client-secret"

    value, error = auth_editor.collect_auth_editor_value("auth_test")

    assert error is None
    assert value == {
        "type": "oauth2",
        "tokenUrl": "https://auth.example.com/oauth/token",
        "clientId": "client-id",
        "clientSecret": "client-secret",
    }


def test_initialize_auth_editor_state_prefills_known_auth_payload():
    _reset_session_state()

    auth_editor.initialize_auth_editor_state(
        "auth_test",
        {
            "type": "bearer",
            "token": "secret-token",
        },
    )

    session_state = sys.modules["streamlit"].session_state
    assert session_state["auth_test_type"] == "bearer"
    assert session_state["auth_test_token"] == "secret-token"


def test_initialize_auth_mode_state_uses_custom_for_recognized_route_auth():
    _reset_session_state()

    auth_editor.initialize_auth_mode_state(
        "auth_mode_test",
        None,
        {"type": "basic", "username": "alice", "password": "secret"},
    )

    session_state = sys.modules["streamlit"].session_state
    assert session_state["auth_mode_test_mode"] == "custom"
    assert session_state["auth_mode_test_type"] == "basic"


def test_collect_auth_mode_value_for_inherit_and_none():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]

    streamlit_module.session_state["auth_mode_test_mode"] = auth_editor.AUTH_MODE_INHERIT
    mode, value, error = auth_editor.collect_auth_mode_value("auth_mode_test")
    assert (mode, value, error) == ("inherit", {}, None)

    streamlit_module.session_state["auth_mode_test_mode"] = auth_editor.AUTH_MODE_NONE
    mode, value, error = auth_editor.collect_auth_mode_value("auth_mode_test")
    assert (mode, value, error) == ("none", {}, None)


def test_build_suite_command_summary_for_init_constant():
    _reset_session_state()
    command = {
        "description": "load rows",
        "configuration_json": {
            "commandCode": "initConstant",
            "commandType": "context",
            "name": "rows",
            "sourceType": "jsonArray",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "**Initialize json array variable** *rows*"


def test_build_suite_command_summary_for_delete_constant():
    _reset_session_state()
    command = {
        "description": "cleanup",
        "configuration_json": {
            "commandCode": "deleteConstant",
            "commandType": "context",
            "name": "rows",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "**Delete variable** *rows*"


def test_build_suite_command_summary_omits_dash_when_description_is_empty():
    _reset_session_state()
    command = {
        "description": "",
        "configuration_json": {
            "commandCode": "initConstant",
            "commandType": "context",
            "name": "rows",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "**Initialize generic variable** *rows*"


def test_build_suite_command_summary_for_table_commands():
    _reset_session_state()
    save_table_command = {
        "description": "persist rows",
        "configuration_json": {
            "commandCode": "saveTable",
            "commandType": "action",
            "table_name": "orders_tmp",
            "source": "$.local.constants.rows",
        },
    }
    drop_table_command = {
        "description": "",
        "configuration_json": {
            "commandCode": "dropTable",
            "commandType": "action",
            "table_name": "orders_tmp",
        },
    }
    clean_table_command = {
        "description": "truncate staging",
        "configuration_json": {
            "commandCode": "cleanTable",
            "commandType": "action",
            "table_name": "orders_tmp",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(save_table_command) == "**Save variable** *rows* **to table** *orders_tmp*"
    assert suite_editor_component._build_suite_command_markdown(drop_table_command) == "**Drop table** *orders_tmp*"
    assert suite_editor_component._build_suite_command_markdown(clean_table_command) == "**Clean table** *orders_tmp*"


def test_build_suite_command_summary_for_send_message_queue(monkeypatch):
    _reset_session_state()
    sys.modules["streamlit"].session_state[suite_editor_component.TEST_EDITOR_BROKERS_KEY] = [
        {"id": "broker-1", "description": "Broker one"}
    ]
    monkeypatch.setattr(
        suite_editor_component,
        "load_test_editor_queues_for_broker",
        lambda broker_id, force=False: [{"id": "queue-1", "description": "Orders queue"}],
    )
    command = {
        "description": "publish rows",
        "configuration_json": {
            "commandCode": "sendMessageQueue",
            "commandType": "action",
            "source": "$.local.constants.rows",
            "queue_id": "queue-1",
        },
    }

    assert (
        suite_editor_component._build_suite_command_markdown(command)
        == "**Send variable** *rows* **to queue** *Orders queue*"
    )


def test_build_suite_command_summary_for_dataset_commands_uses_cache_labels():
    _reset_session_state()
    sys.modules["streamlit"].session_state[suite_editor_component.DATABASE_CONNECTIONS_KEY] = [
        {"id": "conn-1", "description": "Orders DB"}
    ]
    sys.modules["streamlit"].session_state[suite_editor_component.TEST_EDITOR_DATABASE_DATASOURCES_KEY] = [
        {
            "id": "dataset-1",
            "description": "Orders dataset",
            "payload": {"connection_id": "conn-1"},
        }
    ]
    export_command = {
        "description": "share rows",
        "configuration_json": {
            "commandCode": "exportDataset",
            "commandType": "action",
            "connection_id": "conn-1",
            "dataset_id": "dataset-1",
            "table_name": "orders_stage",
            "source": "$.local.constants.rows",
        },
    }
    drop_command = {
        "description": "",
        "configuration_json": {
            "commandCode": "dropDataset",
            "commandType": "action",
            "dataset_id": "dataset-1",
        },
    }
    clean_command = {
        "description": "clean target",
        "configuration_json": {
            "commandCode": "cleanDataset",
            "commandType": "action",
            "dataset_id": "dataset-1",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(export_command) == "**Export variable** *rows* **to table** *orders_stage*"
    assert suite_editor_component._build_suite_command_markdown(drop_command) == "**Drop dataset** *Orders dataset* **from** *Orders DB* **database**"
    assert suite_editor_component._build_suite_command_markdown(clean_command) == "**Clean dataset** *Orders dataset* **from** *Orders DB* **database**"


def test_build_suite_command_summary_for_sleep_and_run_suite():
    _reset_session_state()
    sys.modules["streamlit"].session_state[suite_editor_component.TEST_SUITES_KEY] = [
        {"id": "suite-1", "description": "Nightly suite"}
    ]
    sleep_command = {
        "description": "wait broker",
        "configuration_json": {
            "commandCode": "sleep",
            "commandType": "action",
            "duration": 15,
        },
    }
    run_suite_command = {
        "description": "run smoke",
        "configuration_json": {
            "commandCode": "runSuite",
            "commandType": "action",
            "suite_id": "suite-1",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(sleep_command) == "**Sleep** *15s*"
    assert suite_editor_component._build_suite_command_markdown(run_suite_command) == "**Run suite** *Nightly suite*"


def test_build_suite_command_summary_for_http_commands():
    _reset_session_state()
    read_command = {
        "configuration_json": {
            "commandCode": "readApi",
            "commandType": "action",
            "url": "https://api.example.com/orders",
        },
    }
    write_command = {
        "configuration_json": {
            "commandCode": "writeApi",
            "commandType": "action",
            "method": "PATCH",
            "url": "https://api.example.com/orders/10",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(read_command) == "**Read API** *https://api.example.com/orders*"
    assert suite_editor_component._build_suite_command_markdown(write_command) == "**Write API PATCH** *https://api.example.com/orders/10*"


def test_test_editor_command_list_label_for_http_commands_hides_url():
    _reset_session_state()
    read_command = {
        "configuration_json": {
            "commandCode": "readApi",
            "commandType": "action",
            "url": "https://api.example.com/orders",
            "result_target": "$.result.constants.readApiResult",
        },
    }
    write_command = {
        "configuration_json": {
            "commandCode": "writeApi",
            "commandType": "action",
            "method": "PATCH",
            "url": "https://api.example.com/orders/10",
            "result_target": "$.result.constants.writeApiResult",
        },
    }

    assert (
        test_editor_component._build_test_editor_command_list_label(read_command)
        == "**Fetch data from a REST API** **response stored in variable** *readApiResult*"
    )
    assert (
        test_editor_component._build_test_editor_command_list_label(write_command)
        == "**Send data to a REST API PATCH** **response stored in variable** *writeApiResult*"
    )


def test_build_suite_command_summary_for_assert_uses_variable_name():
    _reset_session_state()
    command = {
        "description": "compare payload",
        "configuration_json": {
            "commandCode": "jsonArrayEquals",
            "commandType": "assert",
            "actual": "$.local.constants.rows",
        },
    }

    assert (
        suite_editor_component._build_suite_command_markdown(command)
        == "**Expected JsonArray equals to** *rows*"
    )


def test_command_labels_use_variable_wording():
    _reset_session_state()
    command = {"configuration_json": {"commandCode": "initConstant", "sourceType": "dataset"}}

    assert suite_editor_component._command_ui_label(command) == "Dataset source"
    assert suite_editor_component._command_action_label(command) == "dataset source"


def test_hook_command_type_labels_use_advanced_wording():
    assert suite_editor_component._hook_command_type_label("initConstant") == "Set runtime value"
    assert suite_editor_component._hook_command_type_label("deleteConstant") == "Delete runtime value"


def test_suite_editor_constant_group_uses_implicit_command_type():
    command_options = suite_editor_component.TEST_CONSTANT_COMMAND_CODES
    command_ui_code = command_options[0] if command_options else ""

    assert command_ui_code == "initConstant"


def test_format_source_variable_option_uses_name_and_type():
    assert (
        suite_editor_component._format_source_variable_option(
            {"name": "rows", "value_type": "dataset"}
        )
        == "rows:dataset"
    )


def test_function_runtime_value_uses_functions_icon():
    command = {"configuration_json": {"commandCode": "initConstant", "valueType": "function"}}

    assert suite_editor_component._command_leading_icon(command) == ":material/functions:"


def test_dataset_summary_falls_back_to_raw_ids_when_cache_is_missing():
    _reset_session_state()
    command = {
        "description": "",
        "configuration_json": {
            "commandCode": "dropDataset",
            "commandType": "action",
            "dataset_id": "dataset-42",
        },
    }

    assert suite_editor_component._build_suite_command_markdown(command) == "**Drop dataset** *dataset-42* **from** - **database**"


def test_resolve_hook_command_group():
    assert suite_editor_component._resolve_hook_command_group(
        {"commandCode": "initConstant", "commandType": "context"}
    ) == "context"
    assert suite_editor_component._resolve_hook_command_group(
        {"commandCode": "saveTable", "commandType": "action"}
    ) == "action"


def test_resolve_test_command_group():
    assert suite_editor_component._resolve_test_command_group(
        {"commandCode": "initConstant", "commandType": "context"}
    ) == "constant"
    assert suite_editor_component._resolve_test_command_group(
        {"commandCode": "saveTable", "commandType": "action"}
    ) == "action"
    assert suite_editor_component._resolve_test_command_group(
        {"commandCode": "jsonEquals", "commandType": "assert"}
    ) == "assert"


def test_default_context_for_item_uses_global_for_before_all_and_after_all():
    assert suite_editor_component._default_context_for_item({"kind": "hook", "hook_phase": "before-all"}) == "global"
    assert suite_editor_component._default_context_for_item({"kind": "hook", "hook_phase": "after-all"}) == "global"


def test_default_context_for_item_uses_local_for_before_each_test_and_after_each():
    assert suite_editor_component._default_context_for_item({"kind": "hook", "hook_phase": "before-each"}) == "local"
    assert suite_editor_component._default_context_for_item({"kind": "hook", "hook_phase": "after-each"}) == "local"
    assert suite_editor_component._default_context_for_item({"kind": "test"}) == "local"


def test_resolve_available_source_constants_for_test_action_includes_visible_compatible_constants():
    test_item = {
        "kind": "test",
        "description": "test",
        "operations": [
            {
                "configuration_json": {
                    "commandCode": "initConstant",
                    "commandType": "context",
                    "name": "localRows",
                    "context": "local",
                    "sourceType": "json",
                }
            }
        ],
    }
    draft = {
        "hooks": {
            "before-all": {
                "kind": "hook",
                "hook_phase": "before-all",
                "operations": [
                    {
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "globalRows",
                            "context": "global",
                            "sourceType": "jsonArray",
                        }
                    }
                ],
            }
        },
        "tests": [test_item],
    }

    options = suite_editor_component._resolve_available_source_constants(
        draft,
        test_item,
        command_code="saveTable",
        stop_before_index=1,
    )

    assert [item["path"] for item in options] == [
        "$.global.constants.globalRows",
        "$.local.constants.localRows",
    ]


def test_resolve_available_source_constants_for_before_all_excludes_global_constants():
    hook_item = {
        "kind": "hook",
        "hook_phase": "before-all",
        "operations": [
            {
                "configuration_json": {
                    "commandCode": "initConstant",
                    "commandType": "context",
                    "name": "globalRows",
                    "context": "global",
                    "sourceType": "jsonArray",
                }
            }
        ],
    }
    draft = {
        "hooks": {
            "before-all": hook_item,
        },
        "tests": [],
    }

    options = suite_editor_component._resolve_available_source_constants(
        draft,
        hook_item,
        command_code="saveTable",
        stop_before_index=1,
    )

    assert options == []


def test_resolve_available_source_constants_includes_declared_sources_with_source_prefix():
    test_item = {
        "kind": "test",
        "description": "test",
        "sources": [
            {
                "sourceCode": "ordersSource",
                "sourceType": "jsonArray",
                "jsonArrayId": "ja-1",
            }
        ],
        "operations": [],
    }
    draft = {
        "hooks": {},
        "tests": [test_item],
    }

    options = suite_editor_component._resolve_available_source_constants(
        draft,
        test_item,
        command_code="sendMessageQueue",
    )

    assert [item["path"] for item in options] == ["source:ordersSource"]


def test_resolve_available_source_constants_for_send_message_queue_includes_raw_constants():
    test_item = {
        "kind": "test",
        "description": "test",
        "operations": [
            {
                "configuration_json": {
                    "commandCode": "initConstant",
                    "commandType": "context",
                    "name": "messageBody",
                    "context": "local",
                    "sourceType": "raw",
                }
            }
        ],
    }
    draft = {
        "hooks": {},
        "tests": [test_item],
    }

    options = suite_editor_component._resolve_available_source_constants(
        draft,
        test_item,
        command_code="sendMessageQueue",
        stop_before_index=1,
    )

    assert [item["path"] for item in options] == [
        "$.local.constants.messageBody",
    ]


def test_resolve_available_source_constants_for_send_message_queue_keeps_raw_preview_value():
    test_item = {
        "kind": "test",
        "description": "test",
        "operations": [
            {
                "configuration_json": {
                    "commandCode": "initConstant",
                    "commandType": "context",
                    "name": "messageBody",
                    "context": "local",
                    "sourceType": "raw",
                    "value": '{"hello": "world"}',
                }
            }
        ],
    }
    draft = {
        "hooks": {},
        "tests": [test_item],
    }

    options = suite_editor_component._resolve_available_source_constants(
        draft,
        test_item,
        command_code="sendMessageQueue",
        stop_before_index=1,
    )

    assert options[0]["preview_value"] == '{"hello": "world"}'


def test_resolve_available_source_constants_for_send_message_queue_includes_dataset_constants():
    test_item = {
        "kind": "test",
        "description": "test",
        "operations": [
            {
                "configuration_json": {
                    "commandCode": "initConstant",
                    "commandType": "context",
                    "name": "messageDataset",
                    "context": "local",
                    "sourceType": "dataset",
                }
            }
        ],
    }
    draft = {
        "hooks": {},
        "tests": [test_item],
    }

    options = suite_editor_component._resolve_available_source_constants(
        draft,
        test_item,
        command_code="sendMessageQueue",
        stop_before_index=1,
    )

    assert [item["path"] for item in options] == [
        "$.local.constants.messageDataset",
    ]


def test_resequence_operations_rewrites_order_progressively():
    operations = [
        {"order": 4, "_ui_key": "op-4", "description": "fourth"},
        {"order": 9, "_ui_key": "op-9", "description": "ninth"},
    ]

    result = suite_editor_component._resequence_operations(operations)

    assert [item["order"] for item in result] == [1, 2]
    assert [item["_ui_key"] for item in result] == ["op-4", "op-9"]


def test_friendly_suite_validation_message_for_visibility_errors():
    message = suite_editor_component._friendly_suite_validation_message(
        "Constant reference 'def-rows' is not visible for command 'saveTable'."
    )

    assert message == "This order uses a variable before it is declared or after it has been deleted."


def test_friendly_suite_validation_message_for_duplicate_definition_errors():
    message = suite_editor_component._friendly_suite_validation_message(
        "Constant 'rows' is already defined in scope 'local'."
    )

    assert message == "This order declares the same variable twice in the same scope."


def test_friendly_suite_validation_message_for_non_writable_scope_errors():
    message = suite_editor_component._friendly_suite_validation_message(
        "Scope 'global' is not writable in section 'test'."
    )

    assert message == "This order writes a variable in a scope that is not allowed here."


def test_api_result_target_label_reads_result_constant_for_reloaded_api_commands():
    cfg = {
        "commandCode": "readApi",
        "resultConstant": {
            "definitionId": "$.result.constants.apiResult",
            "name": "apiResult",
            "valueType": "json",
        },
    }

    assert suite_editor_component._api_result_target_label(cfg) == "apiResult"
    assert test_editor_component._api_result_target_label(cfg) == "apiResult"


def test_build_hook_command_draft_allows_empty_description():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_hook_command_description_1"] = ""
    streamlit_module.session_state["suite_add_hook_init_constant_name_1"] = "rows"
    streamlit_module.session_state["suite_add_hook_init_constant_context_1"] = "local"
    streamlit_module.session_state["suite_add_hook_init_constant_source_type_1"] = "raw"
    streamlit_module.session_state["suite_add_hook_init_constant_value_1"] = ""

    operation, error = suite_editor_component._build_hook_command_draft(1, "initConstant")

    assert error is None
    assert operation is not None
    assert operation["description"] == ""


def test_build_test_command_draft_allows_empty_description():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_1"] = ""
    streamlit_module.session_state["suite_add_test_init_constant_name_1"] = "rows"
    streamlit_module.session_state["suite_add_test_init_constant_context_1"] = "local"
    streamlit_module.session_state["suite_add_test_init_constant_source_type_1"] = "raw"
    streamlit_module.session_state["suite_add_test_init_constant_value_1"] = ""

    operation, error = suite_editor_component._build_test_command_draft(1, "initConstant")

    assert error is None
    assert operation is not None
    assert operation["description"] == ""


def test_build_test_command_draft_for_read_api():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_21"] = "load remote state"
    streamlit_module.session_state["suite_add_test_read_api_url_21"] = "https://api.example.com/orders"
    streamlit_module.session_state["suite_add_test_read_api_query_params_21"] = '{"tenant":"it"}'
    streamlit_module.session_state["suite_add_test_read_api_headers_21"] = '{"x-api-key":"secret"}'
    streamlit_module.session_state["suite_add_test_read_api_timeout_seconds_21"] = 15
    streamlit_module.session_state["suite_add_test_read_api_result_target_21"] = "$.result.constants.ordersResponse"

    operation, error = suite_editor_component._build_test_command_draft(21, "readApi")

    assert error is None
    assert operation["configuration_json"]["commandCode"] == "readApi"
    assert operation["configuration_json"]["queryParams"] == {"tenant": "it"}
    assert operation["configuration_json"]["headers"] == {"x-api-key": "secret"}
    assert operation["configuration_json"]["result_target"] == "$.result.constants.ordersResponse"


def test_build_hook_command_draft_for_read_api_normalizes_result_target_name():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_hook_command_description_23"] = "load hook state"
    streamlit_module.session_state["suite_add_hook_read_api_url_23"] = "https://api.example.com/orders"
    streamlit_module.session_state["suite_add_hook_read_api_result_target_23"] = "hookOrders"

    operation, error = suite_editor_component._build_hook_command_draft(23, "readApi")

    assert error is None
    assert operation["configuration_json"]["commandCode"] == "readApi"
    assert operation["configuration_json"]["result_target"] == "$.result.constants.hookOrders"


def test_build_test_command_draft_for_write_api_text_body():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_22"] = "notify remote service"
    streamlit_module.session_state["suite_add_test_write_api_method_22"] = "PUT"
    streamlit_module.session_state["suite_add_test_write_api_url_22"] = "https://api.example.com/orders/10"
    streamlit_module.session_state["suite_add_test_write_api_query_params_22"] = ""
    streamlit_module.session_state["suite_add_test_write_api_headers_22"] = '{"Content-Type":"text/plain"}'
    streamlit_module.session_state["suite_add_test_write_api_body_type_22"] = "text"
    streamlit_module.session_state["suite_add_test_write_api_body_22"] = "hello"
    streamlit_module.session_state["suite_add_test_write_api_timeout_seconds_22"] = 9
    streamlit_module.session_state["suite_add_test_write_api_result_target_22"] = "$.result.constants.notifyResult"

    operation, error = suite_editor_component._build_test_command_draft(22, "writeApi")

    assert error is None
    assert operation["configuration_json"]["commandCode"] == "writeApi"
    assert operation["configuration_json"]["method"] == "PUT"
    assert operation["configuration_json"]["bodyType"] == "text"
    assert operation["configuration_json"]["body"] == "hello"


def test_build_test_command_draft_for_write_api_form_urlencoded_body():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_24"] = "submit form"
    streamlit_module.session_state["suite_add_test_write_api_method_24"] = "POST"
    streamlit_module.session_state["suite_add_test_write_api_url_24"] = "https://api.example.com/oauth/token"
    streamlit_module.session_state["suite_add_test_write_api_query_params_24"] = ""
    streamlit_module.session_state["suite_add_test_write_api_headers_24"] = ""
    streamlit_module.session_state["suite_add_test_write_api_body_type_24"] = "formUrlEncoded"
    streamlit_module.session_state["suite_add_test_write_api_form_rows_24"] = [
        {
            "row_id": "row-literal",
            "key": "grant_type",
            "node": {"kind": "literal", "value": "client_credentials"},
        },
        {
            "row_id": "row-runtime",
            "key": "access_token",
            "node": {
                "kind": "runtimeValue",
                "definitionId": "def-json",
                "fieldPath": "payload.access_token",
            },
        },
        {
            "row_id": "row-builtin",
            "key": "requested_at",
            "node": {"kind": "builtIn", "resolver": "now"},
        },
    ]
    streamlit_module.session_state["suite_add_test_write_api_form_rows_row_24_val_row-literal_gv_mode"] = "literal"
    streamlit_module.session_state["suite_add_test_write_api_form_rows_row_24_val_row-literal_gv_text"] = "client_credentials"
    streamlit_module.session_state["suite_add_test_write_api_form_rows_row_24_val_row-runtime_gv_mode"] = "runtimeValue"
    streamlit_module.session_state["suite_add_test_write_api_form_rows_row_24_val_row-runtime_gv_definitionId"] = (
        "def-json"
    )
    streamlit_module.session_state["suite_add_test_write_api_form_rows_row_24_val_row-runtime_gv_fieldPath"] = (
        "payload.access_token"
    )
    streamlit_module.session_state["suite_add_test_write_api_form_rows_row_24_val_row-builtin_gv_mode"] = "builtIn"
    streamlit_module.session_state["suite_add_test_write_api_form_rows_row_24_val_row-builtin_gv_resolver"] = "now"
    streamlit_module.session_state["suite_add_test_write_api_timeout_seconds_24"] = 20
    streamlit_module.session_state["suite_add_test_write_api_result_target_24"] = "tokenResponse"

    operation, error = suite_editor_component._build_test_command_draft(24, "writeApi")

    assert error is None
    assert operation["configuration_json"]["commandCode"] == "writeApi"
    assert operation["configuration_json"]["bodyType"] == "formUrlEncoded"
    assert operation["configuration_json"]["body"] == {
        "grant_type": {"kind": "literal", "value": "client_credentials"},
        "access_token": {
            "kind": "runtimeValue",
            "definitionId": "def-json",
            "fieldPath": "payload.access_token",
        },
        "requested_at": {"kind": "builtIn", "resolver": "now"},
    }
    assert operation["configuration_json"]["result_target"] == "$.result.constants.tokenResponse"


def test_build_hook_command_draft_for_write_api_form_urlencoded_body():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_hook_command_description_25"] = "submit hook form"
    streamlit_module.session_state["suite_add_hook_write_api_method_25"] = "POST"
    streamlit_module.session_state["suite_add_hook_write_api_url_25"] = "https://api.example.com/oauth/token"
    streamlit_module.session_state["suite_add_hook_write_api_query_params_25"] = ""
    streamlit_module.session_state["suite_add_hook_write_api_headers_25"] = ""
    streamlit_module.session_state["suite_add_hook_write_api_body_type_25"] = "formUrlEncoded"
    streamlit_module.session_state["suite_add_hook_write_api_form_rows_25"] = [
        {
            "row_id": "row-token",
            "key": "access_token",
            "node": {
                "kind": "runtimeValue",
                "definitionId": "def-json",
                "fieldPath": "payload.access_token",
            },
        }
    ]
    streamlit_module.session_state["suite_add_hook_write_api_form_rows_row_25_val_row-token_gv_mode"] = "runtimeValue"
    streamlit_module.session_state["suite_add_hook_write_api_form_rows_row_25_val_row-token_gv_definitionId"] = (
        "def-json"
    )
    streamlit_module.session_state["suite_add_hook_write_api_form_rows_row_25_val_row-token_gv_fieldPath"] = (
        "payload.access_token"
    )
    streamlit_module.session_state["suite_add_hook_write_api_timeout_seconds_25"] = 11
    streamlit_module.session_state["suite_add_hook_write_api_result_target_25"] = "hookToken"

    operation, error = suite_editor_component._build_hook_command_draft(25, "writeApi")

    assert error is None
    assert operation["configuration_json"]["commandCode"] == "writeApi"
    assert operation["configuration_json"]["bodyType"] == "formUrlEncoded"
    assert operation["configuration_json"]["body"] == {
        "access_token": {
            "kind": "runtimeValue",
            "definitionId": "def-json",
            "fieldPath": "payload.access_token",
        }
    }
    assert operation["configuration_json"]["result_target"] == "$.result.constants.hookToken"


def test_build_hook_command_draft_with_prefix_does_not_touch_locked_widget_state():
    class GuardedSessionState(dict):
        def __init__(self, *args, locked_keys=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.locked_keys = set(locked_keys or [])

        def __setitem__(self, key, value):
            if key in self.locked_keys:
                raise AssertionError(f"attempted write to locked key: {key}")
            return super().__setitem__(key, value)

        def pop(self, key, default=None):
            if key in self.locked_keys:
                raise AssertionError(f"attempted pop of locked key: {key}")
            return super().pop(key, default)

    guarded_state = GuardedSessionState(
        {
            "suite_add_hook_description_2": "load hook api",
            "suite_add_hook_command_type_2": "readApi",
            "suite_add_hook_read_api_url_2": "https://api.example.com/orders",
            "suite_add_hook_read_api_result_target_2": "$.result.constants.orders",
        },
        locked_keys={"suite_add_hook_command_type_2"},
    )
    stub = types.SimpleNamespace(session_state=guarded_state)
    original_st = suite_editor_component.st
    try:
        suite_editor_component.st = stub
        operation, error = suite_editor_component._build_hook_command_draft_with_prefix(
            2,
            "readApi",
            key_prefix="suite_add_hook",
        )
    finally:
        suite_editor_component.st = original_st

    assert error is None
    assert operation is not None
    assert operation["description"] == "load hook api"
    assert operation["configuration_json"]["commandCode"] == "readApi"
    assert operation["configuration_json"]["url"] == "https://api.example.com/orders"
    assert guarded_state["suite_add_hook_command_type_2"] == "readApi"


def test_build_test_command_draft_for_send_message_queue_includes_message_template():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_13"] = ""
    streamlit_module.session_state["suite_add_test_send_message_broker_id_13"] = "broker-1"
    streamlit_module.session_state["suite_add_test_send_message_queue_id_13"] = "queue-1"
    streamlit_module.session_state["suite_add_test_send_message_source_13"] = "$.local.constants.payload"
    streamlit_module.session_state["suite_add_test_send_message_template_enabled_13"] = True
    streamlit_module.session_state["suite_add_test_send_message_template_for_each_13"] = "$.body"
    streamlit_module.session_state["suite_add_test_send_message_template_fields_13"] = ["payload"]
    streamlit_module.session_state["suite_add_test_send_message_template_constants_rows_13"] = [
        {"field": "channel", "type": "string", "value": "sms"},
        {"field": "enabled", "type": "boolean", "value": "true"},
    ]

    operation, error = suite_editor_component._build_test_command_draft(13, "sendMessageQueue")

    assert error is None
    assert operation is not None
    assert operation["configuration_json"]["message_template"] == {
        "forEach": "$.body",
        "fields": ["payload"],
        "constants": [
            {"name": "channel", "kind": "string", "value": "sms"},
            {"name": "enabled", "kind": "boolean", "value": "true"},
        ],
    }


def test_resolve_send_message_preview_payload_uses_template_configuration():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_send_message_template_enabled_13"] = True
    streamlit_module.session_state["suite_add_test_send_message_template_for_each_13"] = "$.body"
    streamlit_module.session_state["suite_add_test_send_message_template_fields_13"] = ["payload"]
    streamlit_module.session_state["suite_add_test_send_message_template_constants_rows_13"] = [
        {"field": "channel", "type": "string", "value": "sms"},
    ]
    original_preview_api = suite_editor_component.preview_send_message_template_rows_via_api
    suite_editor_component.preview_send_message_template_rows_via_api = lambda **kwargs: [
        {"payload": {"id": 1, "status": "queued"}}
    ]

    try:
        preview_payload, preview_error = suite_editor_component._resolve_send_message_preview_payload(
            key_prefix="suite_add_test",
            dialog_nonce=13,
            source_definition={
                "path": "$.local.constants.payload",
                "value_type": "json",
                "preview_value": {"body": {"payload": {"id": 1, "status": "queued"}}},
            },
            json_arrays=[],
            datasources=[],
        )
    finally:
        suite_editor_component.preview_send_message_template_rows_via_api = original_preview_api

    assert preview_error is None
    assert preview_payload == {
        "payload": {"id": 1, "status": "queued"},
        "channel": "sms",
    }


def test_resolve_send_message_preview_payload_uses_raw_source_when_template_is_disabled():
    _reset_session_state()

    preview_payload, preview_error = suite_editor_component._resolve_send_message_preview_payload(
        key_prefix="suite_add_test",
        dialog_nonce=13,
        source_definition={
            "path": "$.local.constants.messageBody",
            "value_type": "raw",
            "preview_value": '{"hello": "world"}',
        },
        json_arrays=[],
        datasources=[],
    )

    assert preview_error is None
    assert preview_payload == '{"hello": "world"}'


def test_render_send_message_template_section_uses_distinct_data_editor_widget_key():
    _reset_session_state()
    session_state = sys.modules["streamlit"].session_state
    session_state["suite_add_test_send_message_template_enabled_13"] = True
    session_state["suite_add_test_send_message_source_13"] = "$.local.constants.payload"
    session_state["suite_add_test_send_message_template_constants_rows_13"] = [
        {"field": "channel", "type": "string", "value": "sms"}
    ]

    class _ColumnConfig:
        @staticmethod
        def TextColumn(*args, **kwargs):
            return {"args": args, "kwargs": kwargs}

        @staticmethod
        def SelectboxColumn(*args, **kwargs):
            return {"args": args, "kwargs": kwargs}

    class _Ctx:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    class StreamlitStub:
        def __init__(self):
            self.session_state = session_state
            self.column_config = _ColumnConfig()
            self.data_editor_calls = []

        def checkbox(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            return None

        def caption(self, *args, **kwargs):
            return None

        def json(self, *args, **kwargs):
            return None

        def text_input(self, *args, **kwargs):
            return None

        def multiselect(self, *args, **kwargs):
            return None

        def columns(self, spec, **kwargs):
            return [_Ctx() for _ in spec]

        def button(self, *args, **kwargs):
            return False

        def rerun(self):
            raise AssertionError("rerun should not be called")

        def data_editor(self, data, **kwargs):
            self.data_editor_calls.append({"data": data, **kwargs})
            return [{"field": "enabled", "type": "boolean", "value": "true"}]

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_preview_helper = suite_editor_component._resolve_send_message_template_preview_rows
    try:
        suite_editor_component.st = stub
        suite_editor_component._resolve_send_message_template_preview_rows = (
            lambda *args, **kwargs: ([{"payload": {"id": 1}}], ["payload"], None)
        )
        suite_editor_component._render_send_message_template_section(
            key_prefix="suite_add_test",
            dialog_nonce=13,
            source_options=[{"path": "$.local.constants.payload", "value_type": "json"}],
            json_arrays=[],
            datasources=[],
        )
    finally:
        suite_editor_component.st = original_st
        suite_editor_component._resolve_send_message_template_preview_rows = original_preview_helper

    assert len(stub.data_editor_calls) == 1
    assert stub.data_editor_calls[0]["data"] == [
        {"field": "channel", "type": "string", "value": "sms"}
    ]
    assert stub.data_editor_calls[0]["key"] == "suite_add_test_send_message_template_constants_editor_13"
    assert stub.data_editor_calls[0]["key"] != "suite_add_test_send_message_template_constants_rows_13"
    assert session_state["suite_add_test_send_message_template_constants_rows_13"] == [
        {"field": "enabled", "type": "boolean", "value": "true"}
    ]


def test_test_action_command_options_do_not_repeat_export_dataset_label():
    labels = [
        suite_editor_component._command_ui_label(
            {
                "configuration_json": {
                    "commandCode": suite_editor_component.TEST_ACTION_COMMAND_MAPPING.get(code, code)
                }
            }
        )
        for code, _label in suite_editor_component.TEST_ACTION_COMMAND_OPTIONS
    ]

    assert labels.count("Export dataset") == 1


def test_append_operation_to_test_allows_empty_description():
    suite_test = {"operations": []}
    operation_item = {
        "description": "",
        "operation_type": "initconstant",
        "configuration_json": {
            "commandCode": "initConstant",
            "commandType": "context",
            "name": "rows",
        },
    }

    test_command_component.append_operation_to_test(suite_test, operation_item)

    assert len(suite_test["operations"]) == 1
    assert suite_test["operations"][0]["description"] == ""
    assert suite_test["operations"][0]["configuration_json"]["name"] == "rows"


def test_command_group_copy_uses_type_specific_labels():
    assert suite_editor_component._command_group_label("context") == "variable"
    assert suite_editor_component._command_group_label("constant") == "variable"
    assert suite_editor_component._command_group_label("action") == "action"
    assert suite_editor_component._command_group_label("assert") == "assert"
    assert suite_editor_component._command_group_intro_label("constant", mode="add") == "Insert new variable"
    assert suite_editor_component._command_group_intro_label("action", mode="edit") == "Modify action"
    assert suite_editor_component._command_group_primary_action_label("context", mode="edit") == "Save variable"
    assert suite_editor_component._command_group_primary_action_label("assert", mode="add") == "Add assert"
    assert suite_editor_component._command_group_added_feedback("context") == "New variable added."
    assert suite_editor_component._command_group_updated_feedback("action") == "Action updated."


def test_build_test_command_draft_for_json_equals_with_manual_expected():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_7"] = ""
    streamlit_module.session_state["suite_add_test_assert_actual_7"] = "$.local.constants.actualPayload"
    streamlit_module.session_state["suite_add_test_assert_expected_mode_7"] = "manual"
    streamlit_module.session_state["suite_add_test_assert_expected_7"] = '{"ok": true}'

    operation, error = suite_editor_component._build_test_command_draft(7, "jsonEquals")

    assert error is None
    assert operation["configuration_json"]["actual"] == "$.local.constants.actualPayload"
    assert operation["configuration_json"]["expected"] == {"ok": True}


def test_build_test_command_draft_for_json_equals_with_expected_variable():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_8"] = ""
    streamlit_module.session_state["suite_add_test_assert_actual_8"] = "$.local.constants.actualPayload"
    streamlit_module.session_state["suite_add_test_assert_expected_mode_8"] = "variable"
    streamlit_module.session_state["suite_add_test_assert_expected_variable_8"] = "$.global.constants.expectedPayload"

    operation, error = suite_editor_component._build_test_command_draft(8, "jsonEquals")

    assert error is None
    assert operation["configuration_json"]["expected"] == {
        "$ref": "$.global.constants.expectedPayload"
    }


def test_build_test_command_draft_for_json_contains_uses_manual_expected_and_compare_keys():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_9"] = ""
    streamlit_module.session_state["suite_add_test_assert_actual_9"] = "$.local.constants.actualPayload"
    streamlit_module.session_state["suite_add_test_assert_expected_mode_9"] = "manual"
    streamlit_module.session_state["suite_add_test_assert_expected_9"] = '{"id": 1, "code": "A"}'
    streamlit_module.session_state["suite_add_test_assert_compare_keys_9"] = ["id", "code"]

    operation, error = suite_editor_component._build_test_command_draft(9, "jsonContains")

    assert error is None
    assert operation["configuration_json"]["expected"] == {"id": 1, "code": "A"}
    assert operation["configuration_json"]["compare_keys"] == ["id", "code"]


def test_build_test_command_draft_for_json_array_asserts_use_multiselect_compare_keys():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_test_command_description_10"] = ""
    streamlit_module.session_state["suite_add_test_assert_actual_10"] = "$.local.constants.actualRows"
    streamlit_module.session_state["suite_add_test_assert_expected_json_array_id_10"] = "ja-1"
    streamlit_module.session_state["suite_add_test_assert_compare_keys_10"] = ["id", "code"]

    equals_operation, equals_error = suite_editor_component._build_test_command_draft(10, "jsonArrayEquals")
    contains_operation, contains_error = suite_editor_component._build_test_command_draft(10, "jsonArrayContains")

    assert equals_error is None
    assert equals_operation["configuration_json"]["expected_json_array_id"] == "ja-1"
    assert equals_operation["configuration_json"]["compare_keys"] == ["id", "code"]
    assert contains_error is None
    assert contains_operation["configuration_json"]["compare_keys"] == ["id", "code"]


def test_build_test_command_draft_for_json_empty_requires_actual_variable():
    _reset_session_state()
    sys.modules["streamlit"].session_state["suite_add_test_command_description_11"] = ""

    operation, error = suite_editor_component._build_test_command_draft(11, "jsonEmpty")

    assert operation is None
    assert error == "Il campo Actual variable e' obbligatorio."


def test_build_test_command_draft_rejects_dataset_runtime_value_type():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state[suite_editor_component.TEST_EDITOR_DATABASE_DATASOURCES_KEY] = [
        {
            "id": "dataset-1",
            "description": "Orders dataset",
            "perimeter": {
                "parameters": [
                    {
                        "name": "pipelineId",
                        "type": "string",
                        "required": True,
                    }
                ]
            },
        }
    ]
    streamlit_module.session_state["suite_add_test_command_description_12"] = ""
    streamlit_module.session_state["suite_add_test_init_constant_name_12"] = "rows"
    streamlit_module.session_state["suite_add_test_init_constant_context_12"] = "local"
    streamlit_module.session_state["suite_add_test_init_constant_source_type_12"] = "dataset"
    streamlit_module.session_state["suite_add_test_init_constant_dataset_id_12"] = "dataset-1"
    streamlit_module.session_state["suite_test_command_init_constant_dataset_param_mode_pipelineId_12"] = "constant"
    streamlit_module.session_state["suite_test_command_init_constant_dataset_param_source_pipelineId_12"] = "$.global.constants.pipelineId"

    operation, error = suite_editor_component._build_test_command_draft(12, "initConstant")

    assert operation is None
    assert error == "Runtime value type non supportato."


def test_build_source_draft_rejects_empty_source_code():
    _reset_session_state()
    source_item, error = suite_editor_component._build_source_draft_with_prefix(
        12,
        [],
        [],
        key_prefix="suite_add_source",
    )

    assert source_item is None
    assert error == "Il campo Source code e' obbligatorio."


def test_build_source_draft_rejects_missing_dataset_selection():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_source_source_code_12"] = "ordersSource"
    streamlit_module.session_state["suite_add_source_source_type_12"] = "dataset"

    source_item, error = suite_editor_component._build_source_draft_with_prefix(
        12,
        [],
        [],
        key_prefix="suite_add_source",
    )

    assert source_item is None
    assert error == "Il campo Dataset e' obbligatorio."


def test_validate_source_code_for_item_rejects_duplicates():
    item = {
        "sources": [
            {"sourceCode": "ordersSource", "sourceType": "jsonArray", "jsonArrayId": "ja-1"}
        ]
    }

    error = suite_editor_component._validate_source_code_for_item(item, "ordersSource")

    assert error == "Source code 'ordersSource' gia' presente in questa sezione."


def test_build_source_draft_for_dataset_copies_perimeter():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    datasources = [
        {
            "id": "dataset-1",
            "description": "Orders dataset",
            "perimeter": {"selected_columns": ["id", "status"]},
        }
    ]
    streamlit_module.session_state["suite_add_source_source_code_12"] = "ordersSource"
    streamlit_module.session_state["suite_add_source_source_type_12"] = "dataset"
    streamlit_module.session_state["suite_add_source_dataset_id_12"] = "dataset-1"

    source_item, error = suite_editor_component._build_source_draft_with_prefix(
        12,
        datasources,
        [],
        key_prefix="suite_add_source",
    )

    assert error is None
    assert source_item == {
        "sourceCode": "ordersSource",
        "sourceType": "dataset",
        "datasetId": "dataset-1",
        "perimeter": {"selected_columns": ["id", "status"]},
    }
    assert source_item["perimeter"] is not datasources[0]["perimeter"]


def test_build_source_draft_for_json_array_serializes_expected_shape():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    json_arrays = [
        {
            "id": "ja-1",
            "description": "Orders array",
        }
    ]
    streamlit_module.session_state["suite_add_source_source_code_12"] = "ordersSource"
    streamlit_module.session_state["suite_add_source_source_type_12"] = "jsonArray"
    streamlit_module.session_state["suite_add_source_json_array_id_12"] = "ja-1"

    source_item, error = suite_editor_component._build_source_draft_with_prefix(
        12,
        [],
        json_arrays,
        key_prefix="suite_add_source",
    )

    assert error is None
    assert source_item == {
        "sourceCode": "ordersSource",
        "sourceType": "jsonArray",
        "jsonArrayId": "ja-1",
    }


def test_resolve_available_assert_expected_constants_for_json_contains_only_returns_inspectable_json():
    draft = {
        "hooks": {
            "before-all": {
                "kind": "hook",
                "hook_phase": "before-all",
                "operations": [
                    {
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "inspectableExpected",
                            "context": "global",
                            "sourceType": "json",
                            "value": {"id": 1, "code": "A"},
                        }
                    },
                    {
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "nonInspectableExpected",
                            "context": "global",
                            "sourceType": "json",
                            "value": [1, 2, 3],
                        }
                    },
                ],
            }
        },
        "tests": [
            {
                "kind": "test",
                "description": "test",
                "operations": [],
            }
        ],
    }

    options = suite_editor_component._resolve_available_assert_constants(
        draft,
        draft["tests"][0],
        command_code="jsonContains",
        role="expected",
    )

    assert [item["path"] for item in options] == ["$.global.constants.inspectableExpected"]


def test_initialize_test_command_form_hydrates_json_contains_expected_ref_and_legacy_array():
    _reset_session_state()
    ref_operation = {
        "description": "",
        "configuration_json": {
            "commandCode": "jsonContains",
            "commandType": "assert",
            "actual": "$.local.constants.actualPayload",
            "expected": {"$ref": "$.global.constants.expectedPayload"},
            "compare_keys": ["id"],
        },
    }

    suite_editor_component._initialize_test_command_form(
        12,
        ref_operation,
        [],
        [],
        key_prefix="suite_edit_test_command",
    )

    session_state = sys.modules["streamlit"].session_state
    assert session_state["suite_edit_test_command_assert_expected_mode_12"] == "variable"
    assert (
        session_state["suite_edit_test_command_assert_expected_variable_12"]
        == "$.global.constants.expectedPayload"
    )

    _reset_session_state()
    legacy_operation = {
        "description": "",
        "configuration_json": {
            "commandCode": "jsonContains",
            "commandType": "assert",
            "actual": "$.local.constants.actualPayload",
            "expected_json_array_id": "ja-legacy",
            "compare_keys": ["id"],
        },
    }

    suite_editor_component._initialize_test_command_form(
        13,
        legacy_operation,
        [{"id": "ja-legacy", "payload": [{"id": 1, "code": "A"}]}],
        [],
        key_prefix="suite_edit_test_command",
    )

    session_state = sys.modules["streamlit"].session_state
    assert session_state["suite_edit_test_command_assert_expected_mode_13"] == "manual"
    assert '"id": 1' in session_state["suite_edit_test_command_assert_expected_13"]
    assert session_state["suite_edit_test_command_assert_compare_keys_13"] == ["id"]


def test_build_assert_summary_uses_requested_restyle_for_empty_and_contains():
    _reset_session_state()
    contains_command = {
        "configuration_json": {
            "commandCode": "jsonContains",
            "commandType": "assert",
            "actual": "$.local.constants.payload",
        }
    }
    empty_command = {
        "configuration_json": {
            "commandCode": "jsonArrayNotEmpty",
            "commandType": "assert",
            "actual": "$.local.constants.rows",
        }
    }

    assert suite_editor_component._build_suite_command_markdown(contains_command) == "**Expected Json contains** *payload*"
    assert suite_editor_component._build_suite_command_markdown(empty_command) == "**JsonArray** *rows* **is not empty**"


def test_build_operation_creation_payload_for_mock_read_api():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state["suite_add_operation_description_31"] = "call audit api"
    streamlit_module.session_state["suite_add_operation_type_31"] = test_command_component.OPERATION_TYPE_READ_API
    streamlit_module.session_state["suite_add_operation_read_api_url_31"] = "https://api.example.com/audit"
    streamlit_module.session_state["suite_add_operation_read_api_query_params_31"] = '{"tenant":"it"}'
    streamlit_module.session_state["suite_add_operation_read_api_headers_31"] = '{"x-api-key":"secret"}'
    streamlit_module.session_state["suite_add_operation_read_api_timeout_seconds_31"] = 20
    streamlit_module.session_state["suite_add_operation_result_target_31"] = "$.result.constants.auditApi"

    payload, error = test_command_component.build_operation_creation_payload(31)

    assert error is None
    assert payload["cfg"]["operationType"] == test_command_component.OPERATION_TYPE_READ_API
    assert payload["cfg"]["commandCode"] == "readApi"
    assert payload["cfg"]["queryParams"] == {"tenant": "it"}


def test_build_draft_operation_from_creation_payload_recovers_http_operation_type():
    operation = test_command_component.build_draft_operation_from_creation_payload(
        {
            "description": "write remote",
            "cfg": {
                "commandCode": "writeApi",
                "commandType": "action",
                "method": "POST",
                "url": "https://api.example.com/orders",
            },
        }
    )

    assert operation["operation_type"] == test_command_component.OPERATION_TYPE_WRITE_API


def test_resolve_export_dataset_mapping_key_options_for_json_json_array_and_dataset():
    draft = {
        "hooks": {
            "before-all": {
                "kind": "hook",
                "hook_phase": "before-all",
                "operations": [
                    {
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "payload",
                            "context": "global",
                            "sourceType": "json",
                            "value": {"id": 1, "code": "A"},
                        }
                    },
                    {
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "rows",
                            "context": "global",
                            "sourceType": "jsonArray",
                            "json_array_id": "ja-1",
                        }
                    },
                    {
                        "configuration_json": {
                            "commandCode": "initConstant",
                            "commandType": "context",
                            "name": "datasetRows",
                            "context": "global",
                            "sourceType": "dataset",
                            "dataset_id": "ds-1",
                        }
                    },
                ],
            }
        },
        "tests": [{"kind": "test", "description": "test", "operations": []}],
    }
    item = draft["tests"][0]
    json_arrays = [{"id": "ja-1", "payload": [{"id": 1, "status": "OK"}]}]
    datasources = [
        {
            "id": "ds-1",
            "payload": {"connection_id": "conn-1"},
            "perimeter": {"selected_columns": ["id", "status"]},
        }
    ]

    json_keys, json_error = suite_editor_component._resolve_export_dataset_mapping_key_options(
        draft,
        item,
        source_path="$.global.constants.payload",
        stop_before_index=None,
        json_arrays=json_arrays,
        datasources=datasources,
    )
    json_array_keys, json_array_error = suite_editor_component._resolve_export_dataset_mapping_key_options(
        draft,
        item,
        source_path="$.global.constants.rows",
        stop_before_index=None,
        json_arrays=json_arrays,
        datasources=datasources,
    )
    dataset_keys, dataset_error = suite_editor_component._resolve_export_dataset_mapping_key_options(
        draft,
        item,
        source_path="$.global.constants.datasetRows",
        stop_before_index=None,
        json_arrays=json_arrays,
        datasources=datasources,
    )

    assert json_error is None
    assert json_keys == ["id", "code"]
    assert json_array_error is None
    assert json_array_keys == ["id", "status"]
    assert dataset_error is None
    assert dataset_keys == ["id", "status"]


def test_test_item_summary_view_only_exposes_modify_button():
    _reset_session_state()
    current_test = {
        "_ui_key": "test-ui-1",
        "description": "Unsaved test",
        "operations": [],
    }

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state
            self.button_calls = []

        def expander(self, *args, **kwargs):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def container(self, *args, **kwargs):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def caption(self, *args, **kwargs):
            return None

        def markdown(self, *args, **kwargs):
            return None

        def divider(self, *args, **kwargs):
            return None

        def button(self, *args, **kwargs):
            payload = dict(kwargs)
            if args:
                payload["label"] = args[0]
            self.button_calls.append(payload)
            return False

        def rerun(self):
            raise AssertionError("rerun should not be called")

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    try:
        suite_editor_component.st = stub
        suite_editor_component._render_test_item(current_test, 1, {})
    finally:
        suite_editor_component.st = original_st

    modify_button_call = next(
        call for call in stub.button_calls if call.get("key") == "test_suite_open_test_editor_test-ui-1"
    )
    assert modify_button_call["label"] == ""
    delete_button_call = next(
        call for call in stub.button_calls if call.get("key") == "test_suite_delete_test_test-ui-1"
    )
    assert delete_button_call["label"] == ""
    assert len(stub.button_calls) == 2


def test_ensure_selected_test_position_clamps_to_last_available():
    _reset_session_state()
    sys.modules["streamlit"].session_state[suite_editor_component.SELECTED_TEST_POSITION_KEY] = 5
    draft = {
        "tests": [
            {"description": "First", "position": 1},
            {"description": "Second", "position": 2},
        ]
    }

    assert suite_editor_component._ensure_selected_test_position(draft) == 2
    assert sys.modules["streamlit"].session_state[suite_editor_component.SELECTED_TEST_POSITION_KEY] == 2


def test_render_add_test_dialog_appends_test_and_selects_it():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state[suite_editor_component.ADD_TEST_DIALOG_NONCE_KEY] = 7
    streamlit_module.session_state["suite_add_test_description_7"] = "Smoke test"
    streamlit_module.session_state["suite_add_test_on_failure_7"] = "CONTINUE"
    draft = {"id": "suite-1", "tests": []}
    persist_calls = []
    close_calls = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = streamlit_module.session_state

        def text_input(self, *args, **kwargs):
            return None

        def selectbox(self, *args, **kwargs):
            return None

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def button(self, label="", **kwargs):
            return label == "Save"

        def rerun(self):
            self.session_state["_rerun_called"] = True

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_persist = suite_editor_component._persist_current_draft
    original_close = suite_editor_component._close_add_test_dialog
    try:
        suite_editor_component.st = stub
        suite_editor_component._persist_current_draft = lambda **kwargs: persist_calls.append(kwargs)
        suite_editor_component._close_add_test_dialog = lambda: close_calls.append(True)
        suite_editor_component._render_add_test_dialog(draft)
    finally:
        suite_editor_component.st = original_st
        suite_editor_component._persist_current_draft = original_persist
        suite_editor_component._close_add_test_dialog = original_close

    assert len(draft["tests"]) == 1
    assert draft["tests"][0]["kind"] == "test"
    assert draft["tests"][0]["description"] == "Smoke test"
    assert draft["tests"][0]["on_failure"] == "CONTINUE"
    assert draft["tests"][0]["position"] == 1
    assert streamlit_module.session_state[suite_editor_component.SELECTED_TEST_POSITION_KEY] == 1
    assert persist_calls == [{"success_message": "Test added.", "rerun": False}]
    assert close_calls == [True]
    assert streamlit_module.session_state["_rerun_called"] is True


def test_move_operation_in_item_swaps_and_resequences():
    item = {
        "operations": [
            {"_ui_key": "op-1", "order": 1, "description": "first"},
            {"_ui_key": "op-2", "order": 2, "description": "second"},
        ]
    }

    assert suite_editor_component._move_operation_in_item(item, 0, 1) is True
    assert [operation["_ui_key"] for operation in item["operations"]] == ["op-2", "op-1"]
    assert [operation["order"] for operation in item["operations"]] == [1, 2]


def test_test_editor_item_read_mode_exposes_inline_command_actions():
    _reset_session_state()
    current_test = {
        "_ui_key": "test-ui-1",
        "description": "Editable test",
        "operations": [
            {
                "_ui_key": "op-ui-1",
                "description": "cleanup",
                "configuration_json": {
                    "commandCode": "dropTable",
                    "commandType": "action",
                    "table_name": "orders_tmp",
                },
            }
        ],
    }
    draft = {"tests": [current_test]}
    sys.modules["streamlit"].session_state[test_editor_component.TEST_EDITOR_SELECTED_COMMAND_UI_KEY] = "op-ui-1"
    rendered_command_ui_keys: list[str] = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def container(self, *args, **kwargs):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def caption(self, *args, **kwargs):
            return None

        def markdown(self, *args, **kwargs):
            return None

        def divider(self, *args, **kwargs):
            return None

        def button(self, *args, **kwargs):
            return False

        def info(self, *args, **kwargs):
            return None

        def rerun(self):
            raise AssertionError("rerun should not be called")

    stub = StreamlitStub()
    original_st = test_editor_component.st
    original_shared_st = suite_editor_component.st
    original_editor_shared_st = test_editor_component.shared.st
    original_load_context = test_editor_component.load_test_editor_context
    original_load_connections = test_editor_component.load_database_connections
    original_render_list = test_editor_component._render_test_editor_command_list_card
    original_render_selected = test_editor_component._render_selected_test_editor_command
    original_render_popover = test_editor_component._render_test_editor_add_command_popover
    try:
        test_editor_component.st = stub
        suite_editor_component.st = stub
        test_editor_component.shared.st = stub
        test_editor_component.load_test_editor_context = lambda force=False: None
        test_editor_component.load_database_connections = lambda force=False: None
        test_editor_component._render_test_editor_command_list_card = lambda *args, **kwargs: None
        test_editor_component._render_selected_test_editor_command = (
            lambda item, draft, operation_ui_key: rendered_command_ui_keys.append(operation_ui_key)
        )
        test_editor_component._render_test_editor_add_command_popover = lambda *args, **kwargs: None
        test_editor_component._render_test_editor_item(current_test, 1, draft, {})
    finally:
        test_editor_component.st = original_st
        suite_editor_component.st = original_shared_st
        test_editor_component.shared.st = original_editor_shared_st
        test_editor_component.load_test_editor_context = original_load_context
        test_editor_component.load_database_connections = original_load_connections
        test_editor_component._render_test_editor_command_list_card = original_render_list
        test_editor_component._render_selected_test_editor_command = original_render_selected
        test_editor_component._render_test_editor_add_command_popover = original_render_popover

    assert rendered_command_ui_keys == ["op-ui-1"]


def test_render_add_source_dialog_appends_source_and_persists():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state[suite_editor_component.SOURCE_ADD_DIALOG_NONCE_KEY] = 9
    streamlit_module.session_state[suite_editor_component.SOURCE_ADD_DIALOG_TARGET_UI_KEY] = "test-ui-1"
    streamlit_module.session_state["suite_add_source_source_code_9"] = "ordersSource"
    streamlit_module.session_state["suite_add_source_source_type_9"] = "dataset"
    streamlit_module.session_state["suite_add_source_dataset_id_9"] = "dataset-1"
    streamlit_module.session_state[suite_editor_component.TEST_SUITE_DRAFT_KEY] = {
        "tests": [
            {
                "_ui_key": "test-ui-1",
                "kind": "test",
                "sources": [],
                "operations": [],
            }
        ]
    }
    draft = streamlit_module.session_state[suite_editor_component.TEST_SUITE_DRAFT_KEY]
    persist_calls = []
    close_calls = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = streamlit_module.session_state

        def caption(self, *args, **kwargs):
            return None

        def markdown(self, *args, **kwargs):
            return None

        def text_input(self, *args, **kwargs):
            return None

        def selectbox(self, *args, **kwargs):
            return None

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def container(self, *args, **kwargs):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def button(self, label="", **kwargs):
            return label == "Add source"

        def rerun(self):
            self.session_state["_rerun_called"] = True

        def error(self, *args, **kwargs):
            raise AssertionError("error should not be called")

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_load_context = suite_editor_component.load_test_editor_context
    original_persist = suite_editor_component._persist_current_draft
    original_close = suite_editor_component._close_add_source_dialog
    original_render_preview = suite_editor_component._render_add_source_preview
    try:
        suite_editor_component.st = stub
        suite_editor_component.load_test_editor_context = lambda force=False: None
        suite_editor_component._persist_current_draft = lambda **kwargs: persist_calls.append(kwargs)
        suite_editor_component._close_add_source_dialog = lambda: close_calls.append(True)
        suite_editor_component._render_add_source_preview = lambda *a, **kw: None
        streamlit_module.session_state[suite_editor_component.TEST_EDITOR_DATABASE_DATASOURCES_KEY] = [
            {
                "id": "dataset-1",
                "description": "Orders dataset",
                "perimeter": {"selected_columns": ["id", "status"]},
            }
        ]
        streamlit_module.session_state[suite_editor_component.TEST_EDITOR_JSON_ARRAYS_KEY] = []
        suite_editor_component._render_add_source_dialog(draft)
    finally:
        suite_editor_component.st = original_st
        suite_editor_component.load_test_editor_context = original_load_context
        suite_editor_component._persist_current_draft = original_persist
        suite_editor_component._close_add_source_dialog = original_close
        suite_editor_component._render_add_source_preview = original_render_preview

    test_item = draft["tests"][0]
    assert test_item["sources"] == [
        {
            "sourceCode": "ordersSource",
            "sourceType": "dataset",
            "datasetId": "dataset-1",
            "perimeter": {"selected_columns": ["id", "status"]},
        }
    ]
    assert persist_calls == [{"success_message": "New source added.", "rerun": False}]
    assert close_calls == [True]
    assert streamlit_module.session_state["_rerun_called"] is True


def test_hook_section_defaults_to_commands_section():
    _reset_session_state()
    draft = {
        "hooks": {
            "before-all": {
                "_ui_key": "hook-ui-1",
                "kind": "hook",
                "hook_phase": "before-all",
                "sources": [],
                "operations": [],
            }
        }
    }
    rendered_sections: list[str] = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def markdown(self, *_args, **_kwargs):
            return None

        def caption(self, *_args, **_kwargs):
            return None

        def segmented_control(self, label, options, key=None, **kwargs):
            return self.session_state.get(key) or options[0]

        def rerun(self):
            raise AssertionError("rerun should not be called")

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_render_commands = suite_editor_component._render_advanced_hook_commands_section
    original_render_datasources = suite_editor_component._render_advanced_hook_datasources_section
    try:
        suite_editor_component.st = stub
        suite_editor_component._render_advanced_hook_commands_section = lambda *args, **kwargs: rendered_sections.append("commands")
        suite_editor_component._render_advanced_hook_datasources_section = lambda *args, **kwargs: rendered_sections.append("datasources")
        suite_editor_component._render_hook_section(draft, "before-all", "Before suite", {})
    finally:
        suite_editor_component.st = original_st
        suite_editor_component._render_advanced_hook_commands_section = original_render_commands
        suite_editor_component._render_advanced_hook_datasources_section = original_render_datasources

    assert rendered_sections == ["commands"]


def test_hook_section_uses_persisted_datasources_selection():
    _reset_session_state()
    draft = {
        "hooks": {
            "before-all": {
                "_ui_key": "hook-ui-1",
                "kind": "hook",
                "hook_phase": "before-all",
                "sources": [],
                "operations": [],
            }
        }
    }
    sys.modules["streamlit"].session_state[
        suite_editor_component._advanced_hook_section_state_key("before-all")
    ] = suite_editor_component.ADVANCED_HOOK_SECTION_DATASOURCES_TAB
    rendered_sections: list[str] = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def markdown(self, *_args, **_kwargs):
            return None

        def caption(self, *_args, **_kwargs):
            return None

        def segmented_control(self, label, options, key=None, **kwargs):
            return self.session_state.get(key) or options[0]

        def rerun(self):
            raise AssertionError("rerun should not be called")

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_render_commands = suite_editor_component._render_advanced_hook_commands_section
    original_render_datasources = suite_editor_component._render_advanced_hook_datasources_section
    try:
        suite_editor_component.st = stub
        suite_editor_component._render_advanced_hook_commands_section = lambda *args, **kwargs: rendered_sections.append("commands")
        suite_editor_component._render_advanced_hook_datasources_section = lambda *args, **kwargs: rendered_sections.append("datasources")
        suite_editor_component._render_hook_section(draft, "before-all", "Before suite", {})
    finally:
        suite_editor_component.st = original_st
        suite_editor_component._render_advanced_hook_commands_section = original_render_commands
        suite_editor_component._render_advanced_hook_datasources_section = original_render_datasources

    assert rendered_sections == ["datasources"]


def test_advanced_hook_sections_use_persisted_hook_phase_keys():
    assert advanced_suite_editor_settings_container.HOOK_SECTIONS == [
        ("before-all", ":material/first_page: Before all"),
        ("before-each", ":material/skip_next: Before each test"),
        ("after-each", ":material/task_alt: After each test"),
        ("after-all", ":material/last_page: After all"),
    ]


def test_suite_editor_hook_command_actions_do_not_expose_modify_button():
    _reset_session_state()
    item = {
        "_ui_key": "hook-ui-1",
        "kind": "hook",
        "hook_phase": "before-all",
        "operations": [
            {
                "_ui_key": "op-ui-1",
                "description": "cleanup",
                "configuration_json": {
                    "commandCode": "dropTable",
                    "commandType": "action",
                    "table_name": "orders_tmp",
                },
            }
        ],
    }
    captured: dict[str, object] = {}

    original_render_card = suite_editor_component._render_suite_command_card
    original_st = suite_editor_component.st
    try:
        def _render_card_stub(operation, key_prefix, action_specs):
            captured["actions"] = [spec["name"] for spec in action_specs]
            return {}

        suite_editor_component._render_suite_command_card = _render_card_stub
        suite_editor_component.st = types.SimpleNamespace(rerun=lambda: None)
        suite_editor_component._render_suite_item_operation(item, item["operations"][0], 0, "hook")
    finally:
        suite_editor_component._render_suite_command_card = original_render_card
        suite_editor_component.st = original_st

    assert captured["actions"] == ["up", "down", "delete"]


def test_advanced_suite_editor_defaults_to_before_all_hook():
    _reset_session_state()
    captured: dict[str, object] = {"rendered_phases": []}

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def button(self, *args, **kwargs):
            return False

        def markdown(self, *args, **kwargs):
            return None

        def caption(self, *args, **kwargs):
            return None

        def divider(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            return None

        def segmented_control(self, label, options, key=None, **kwargs):
            return self.session_state.get(key) or options[0]

    stub = StreamlitStub()
    original_st = advanced_suite_editor_settings_container.st
    original_load_context = advanced_suite_editor_settings_container.load_test_editor_context
    original_shared = advanced_suite_editor_settings_container.shared

    shared_stub = types.SimpleNamespace(
        _load_test_suites=lambda force=False: [{"id": "suite-1", "description": "Suite"}],
        _ensure_selected_suite_id=lambda suites: "suite-1",
        _resolve_editor_draft=lambda selected_suite_id: {"id": "suite-1", "description": "Suite"},
        _render_command_feedback=lambda: None,
        _render_hook_section=lambda draft, hook_phase, section_title, execution_state: captured["rendered_phases"].append(
            (hook_phase, section_title)
        ),
        _consume_add_operation_dialog_request=lambda: False,
        _render_add_operation_dialog=lambda draft: None,
        _consume_add_source_dialog_request=lambda: False,
        _render_add_source_dialog=lambda draft: None,
        _consume_hook_command_dialog_request=lambda: False,
        _render_add_hook_command_dialog=lambda draft: None,
        _consume_edit_command_dialog_request=lambda: False,
        _render_edit_command_dialog=lambda draft: None,
        COMMAND_REORDER_DIALOG_OPEN_KEY="suite_editor_command_reorder_dialog_open",
        _render_reorder_command_dialog=lambda draft: None,
        _select_persisted_tab=lambda options, state_key, default=None: sys.modules["streamlit"].session_state.get(state_key) or options[0],
    )

    try:
        advanced_suite_editor_settings_container.st = stub
        advanced_suite_editor_settings_container.load_test_editor_context = lambda force=False: None
        advanced_suite_editor_settings_container.shared = shared_stub
        advanced_suite_editor_settings_container.render_advanced_suite_editor_settings_container()
    finally:
        advanced_suite_editor_settings_container.st = original_st
        advanced_suite_editor_settings_container.load_test_editor_context = original_load_context
        advanced_suite_editor_settings_container.shared = original_shared

    assert captured["rendered_phases"] == [
        (
            advanced_suite_editor_settings_container.HOOK_SECTIONS[0][0],
            advanced_suite_editor_settings_container.HOOK_SECTIONS[0][1],
        )
    ]


def test_advanced_suite_editor_uses_persisted_hook_selection():
    _reset_session_state()
    captured: dict[str, object] = {"rendered_phases": []}
    selected_label = advanced_suite_editor_settings_container.HOOK_SECTIONS[1][1]
    sys.modules["streamlit"].session_state[
        advanced_suite_editor_settings_container.ADVANCED_SUITE_EDITOR_SELECTED_HOOK_KEY
    ] = selected_label

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def button(self, *args, **kwargs):
            return False

        def markdown(self, *args, **kwargs):
            return None

        def caption(self, *args, **kwargs):
            return None

        def divider(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            return None

        def segmented_control(self, label, options, key=None, **kwargs):
            return self.session_state.get(key) or options[0]

    stub = StreamlitStub()
    original_st = advanced_suite_editor_settings_container.st
    original_load_context = advanced_suite_editor_settings_container.load_test_editor_context
    original_shared = advanced_suite_editor_settings_container.shared

    shared_stub = types.SimpleNamespace(
        _load_test_suites=lambda force=False: [{"id": "suite-1", "description": "Suite"}],
        _ensure_selected_suite_id=lambda suites: "suite-1",
        _resolve_editor_draft=lambda selected_suite_id: {"id": "suite-1", "description": "Suite"},
        _render_command_feedback=lambda: None,
        _render_hook_section=lambda draft, hook_phase, section_title, execution_state: captured["rendered_phases"].append(
            (hook_phase, section_title)
        ),
        _consume_add_operation_dialog_request=lambda: False,
        _render_add_operation_dialog=lambda draft: None,
        _consume_add_source_dialog_request=lambda: False,
        _render_add_source_dialog=lambda draft: None,
        _consume_hook_command_dialog_request=lambda: False,
        _render_add_hook_command_dialog=lambda draft: None,
        _consume_edit_command_dialog_request=lambda: False,
        _render_edit_command_dialog=lambda draft: None,
        COMMAND_REORDER_DIALOG_OPEN_KEY="suite_editor_command_reorder_dialog_open",
        _render_reorder_command_dialog=lambda draft: None,
        _select_persisted_tab=lambda options, state_key, default=None: sys.modules["streamlit"].session_state.get(state_key) or options[0],
    )

    try:
        advanced_suite_editor_settings_container.st = stub
        advanced_suite_editor_settings_container.load_test_editor_context = lambda force=False: None
        advanced_suite_editor_settings_container.shared = shared_stub
        advanced_suite_editor_settings_container.render_advanced_suite_editor_settings_container()
    finally:
        advanced_suite_editor_settings_container.st = original_st
        advanced_suite_editor_settings_container.load_test_editor_context = original_load_context
        advanced_suite_editor_settings_container.shared = original_shared

    assert captured["rendered_phases"] == [
        (
            advanced_suite_editor_settings_container.HOOK_SECTIONS[1][0],
            advanced_suite_editor_settings_container.HOOK_SECTIONS[1][1],
        )
    ]


def test_advanced_hook_add_command_popover_opens_variable_dialog():
    _reset_session_state()
    draft = {"id": "suite-1"}
    hook = {"_ui_key": "hook-ui-1", "kind": "hook", "hook_phase": "before-all"}
    opened_dialogs: list[tuple[str, str]] = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state
            self.button_calls = []

        def popover(self, label, **kwargs):
            self.button_calls.append({"label": label, "kind": "popover"})

            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def button(self, *args, **kwargs):
            payload = dict(kwargs)
            if args:
                payload["label"] = args[0]
            self.button_calls.append(payload)
            return args and args[0] == "+ Variable"

        def rerun(self):
            self.session_state["_rerun_called"] = True

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_open_hook_dialog = suite_editor_component._open_hook_command_dialog_for_hook
    try:
        suite_editor_component.st = stub
        suite_editor_component._open_hook_command_dialog_for_hook = (
            lambda current_draft, hook_phase, group: opened_dialogs.append((hook_phase, group))
        )
        suite_editor_component._render_advanced_hook_add_command_popover(draft, "before-all", hook)
    finally:
        suite_editor_component.st = original_st
        suite_editor_component._open_hook_command_dialog_for_hook = original_open_hook_dialog

    assert opened_dialogs == [("before-all", "context")]
    assert [call["label"] for call in stub.button_calls if "label" in call] == [
        "+ Add command",
        "+ Variable",
        "+ Action",
    ]
    assert sys.modules["streamlit"].session_state["_rerun_called"] is True


def test_advanced_hook_commands_section_renders_selected_command_detail_only():
    _reset_session_state()
    hook = {
        "_ui_key": "hook-ui-1",
        "kind": "hook",
        "hook_phase": "before-all",
        "operations": [
            {
                "_ui_key": "op-ui-1",
                "description": "cleanup",
                "configuration_json": {
                    "commandCode": "dropTable",
                    "commandType": "action",
                    "table_name": "orders_tmp",
                },
            },
            {
                "_ui_key": "op-ui-2",
                "description": "save table",
                "configuration_json": {
                    "commandCode": "saveTable",
                    "commandType": "action",
                    "table_name": "orders_stage",
                },
            },
        ],
    }
    sys.modules["streamlit"].session_state[
        suite_editor_component._advanced_hook_selected_command_state_key("before-all")
    ] = "op-ui-2"
    rendered_command_ui_keys: list[str] = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def container(self, *args, **kwargs):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def button(self, *args, **kwargs):
            return False

        def rerun(self):
            raise AssertionError("rerun should not be called")

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_render_list = suite_editor_component._render_advanced_hook_command_list_card
    original_render_selected = suite_editor_component._render_selected_advanced_hook_command
    original_render_popover = suite_editor_component._render_advanced_hook_add_command_popover
    try:
        suite_editor_component.st = stub
        suite_editor_component._render_advanced_hook_command_list_card = lambda *args, **kwargs: None
        suite_editor_component._render_selected_advanced_hook_command = (
            lambda hook_item, draft, hook_phase, operation_ui_key: rendered_command_ui_keys.append(operation_ui_key)
        )
        suite_editor_component._render_advanced_hook_add_command_popover = lambda *args, **kwargs: None
        suite_editor_component._render_advanced_hook_commands_section({"id": "suite-1"}, hook, "before-all")
    finally:
        suite_editor_component.st = original_st
        suite_editor_component._render_advanced_hook_command_list_card = original_render_list
        suite_editor_component._render_selected_advanced_hook_command = original_render_selected
        suite_editor_component._render_advanced_hook_add_command_popover = original_render_popover

    assert rendered_command_ui_keys == ["op-ui-2"]


def test_advanced_hook_delete_reassigns_selected_command():
    _reset_session_state()
    hook = {
        "_ui_key": "hook-ui-1",
        "kind": "hook",
        "hook_phase": "before-all",
        "operations": [
            {"_ui_key": "op-ui-1", "configuration_json": {"commandCode": "dropTable"}},
            {"_ui_key": "op-ui-2", "configuration_json": {"commandCode": "cleanTable"}},
        ],
    }

    suite_editor_component._set_advanced_hook_selected_command("before-all", "op-ui-1")
    suite_editor_component._reassign_advanced_hook_selected_command_after_delete(hook, "before-all", "op-ui-1")

    assert [operation["_ui_key"] for operation in hook["operations"]] == ["op-ui-2"]
    assert (
        sys.modules["streamlit"].session_state[
            suite_editor_component._advanced_hook_selected_command_state_key("before-all")
        ]
        == "op-ui-2"
    )


def test_save_advanced_hook_api_command_preserves_selected_api_tab():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    operation_ui_key = "op-ui-1"
    prefix = f"advanced_hook_api_command_{operation_ui_key}"
    api_tab_key = suite_editor_component._advanced_hook_api_tab_state_key(operation_ui_key)
    streamlit_module.session_state[api_tab_key] = "Headers"
    streamlit_module.session_state[f"{prefix}_url"] = "https://api.example.com/orders/42"
    streamlit_module.session_state[f"{prefix}_timeout"] = 15
    streamlit_module.session_state[f"{prefix}_result_target"] = "apiResult"
    streamlit_module.session_state[f"{prefix}_auth_type"] = "none"

    item = {"operations": []}
    current_operation = {
        "_ui_key": operation_ui_key,
        "description": "Read orders",
        "operation_type": "readApi",
        "configuration_json": {
            "commandCode": "readApi",
            "commandType": "action",
            "url": "https://api.example.com/orders",
            "timeoutSeconds": 30,
        },
    }
    item["operations"].append(current_operation)

    class StreamlitStub:
        def __init__(self):
            self.session_state = streamlit_module.session_state

        def error(self, *args, **kwargs):
            raise AssertionError(f"Unexpected validation error: {args!r} {kwargs!r}")

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_rows_to_dict = suite_editor_component.rows_to_dict
    original_collect_auth = suite_editor_component.collect_auth_editor_value
    original_persist = suite_editor_component._persist_current_draft
    try:
        suite_editor_component.st = stub
        suite_editor_component.rows_to_dict = lambda rows, field_label: ({}, None)
        suite_editor_component.collect_auth_editor_value = lambda auth_state_key: ({}, None)
        suite_editor_component._persist_current_draft = lambda **kwargs: None
        saved = suite_editor_component._save_advanced_hook_command(
            item,
            current_operation,
            0,
            operation_ui_key,
            {
                "editor_kind": "api",
                "prefix": prefix,
                "is_write": False,
                "url_key": f"{prefix}_url",
                "params_state_key": f"{prefix}_params_rows",
                "auth_state_key": f"{prefix}_auth",
                "headers_state_key": f"{prefix}_headers_rows",
                "body_type_key": f"{prefix}_body_type",
                "body_key": f"{prefix}_body",
                "timeout_key": f"{prefix}_timeout",
                "result_target_key": f"{prefix}_result_target",
                "method_key": f"{prefix}_method",
            },
        )
    finally:
        suite_editor_component.st = original_st
        suite_editor_component.rows_to_dict = original_rows_to_dict
        suite_editor_component.collect_auth_editor_value = original_collect_auth
        suite_editor_component._persist_current_draft = original_persist

    assert saved is True
    assert streamlit_module.session_state[api_tab_key] == "Headers"
    assert f"{prefix}_url" not in streamlit_module.session_state


def test_save_advanced_hook_api_command_serializes_form_urlencoded_runtime_refs():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    operation_ui_key = "op-ui-form"
    prefix = f"advanced_hook_api_command_{operation_ui_key}"
    form_rows_key = f"{prefix}_form_body_rows"
    form_row_prefix = f"{form_rows_key}_row"

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
                        "operation_type": "readApi",
                        "configuration_json": {
                            "commandCode": "readApi",
                            "commandType": "action",
                            "url": "https://api.example.com/token",
                            "result_target": "$.result.constants.tokenResponse",
                        },
                    },
                    {
                        "_ui_key": operation_ui_key,
                        "order": 2,
                        "description": "submit form",
                        "operation_type": "writeApi",
                        "configuration_json": {
                            "commandCode": "writeApi",
                            "commandType": "action",
                            "method": "POST",
                            "url": "https://api.example.com/form",
                            "bodyType": "formUrlEncoded",
                            "timeoutSeconds": 30,
                        },
                    },
                ],
            }
        },
        "tests": [],
    }
    hook = draft["hooks"]["before-all"]
    current_operation = hook["operations"][1]
    streamlit_module.session_state[suite_editor_component.TEST_SUITE_DRAFT_KEY] = draft
    streamlit_module.session_state[f"{prefix}_url"] = "https://api.example.com/form"
    streamlit_module.session_state[f"{prefix}_timeout"] = 20
    streamlit_module.session_state[f"{prefix}_result_target"] = ""
    streamlit_module.session_state[f"{prefix}_method"] = "POST"
    streamlit_module.session_state[f"{prefix}_body_type"] = "formUrlEncoded"
    streamlit_module.session_state[f"{prefix}_auth_type"] = "none"
    streamlit_module.session_state[form_rows_key] = [
        {
            "row_id": "row-token",
            "key": "access_token",
            "node": {
                "kind": "runtimeValue",
                "definitionId": "$.result.constants.tokenResponse",
                "fieldPath": "payload.access_token",
            },
        }
    ]
    streamlit_module.session_state[f"{form_row_prefix}_val_row-token_gv_mode"] = "runtimeValue"
    streamlit_module.session_state[f"{form_row_prefix}_val_row-token_gv_definitionId"] = (
        "$.result.constants.tokenResponse"
    )
    streamlit_module.session_state[f"{form_row_prefix}_val_row-token_gv_fieldPath"] = "payload.access_token"
    persisted_payloads = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = streamlit_module.session_state

        def error(self, *args, **kwargs):
            raise AssertionError(f"Unexpected validation error: {args!r} {kwargs!r}")

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_rows_to_dict = suite_editor_component.rows_to_dict
    original_collect_auth = suite_editor_component.collect_auth_editor_value
    original_update = suite_editor_component.update_test_suite
    original_load_selected = suite_editor_component._load_selected_draft
    original_load_suites = suite_editor_component._load_test_suites
    try:
        suite_editor_component.st = stub
        suite_editor_component.rows_to_dict = lambda rows, field_label: ({}, None)
        suite_editor_component.collect_auth_editor_value = lambda auth_state_key: ({}, None)
        suite_editor_component.update_test_suite = lambda payload: persisted_payloads.append(payload)
        suite_editor_component._load_selected_draft = lambda: None
        suite_editor_component._load_test_suites = lambda force=False: None
        saved = suite_editor_component._save_advanced_hook_command(
            hook,
            current_operation,
            1,
            operation_ui_key,
            {
                "editor_kind": "api",
                "prefix": prefix,
                "is_write": True,
                "url_key": f"{prefix}_url",
                "params_state_key": f"{prefix}_params_rows",
                "auth_state_key": f"{prefix}_auth",
                "headers_state_key": f"{prefix}_headers_rows",
                "form_body_state_key": form_rows_key,
                "body_type_key": f"{prefix}_body_type",
                "body_key": f"{prefix}_body",
                "timeout_key": f"{prefix}_timeout",
                "result_target_key": f"{prefix}_result_target",
                "method_key": f"{prefix}_method",
            },
        )
    finally:
        suite_editor_component.st = original_st
        suite_editor_component.rows_to_dict = original_rows_to_dict
        suite_editor_component.collect_auth_editor_value = original_collect_auth
        suite_editor_component.update_test_suite = original_update
        suite_editor_component._load_selected_draft = original_load_selected
        suite_editor_component._load_test_suites = original_load_suites

    assert saved is True
    assert len(persisted_payloads) == 1
    read_cfg = persisted_payloads[0]["hooks"][0]["commands"][0]["cfg"]
    write_cfg = persisted_payloads[0]["hooks"][0]["commands"][1]["cfg"]
    assert write_cfg["body"]["access_token"]["definitionId"] == read_cfg["resultConstant"]["definitionId"]
    assert write_cfg["body"]["access_token"]["fieldPath"] == "payload.access_token"


def test_test_editor_item_renders_commands_tab_by_default():
    _reset_session_state()
    current_test = {
        "_ui_key": "test-ui-1",
        "description": "Editable test",
        "sources": [],
        "operations": [],
    }
    rendered_sections: list[str] = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def button(self, *args, **kwargs):
            return False

        def segmented_control(self, label, options, key=None, **kwargs):
            return self.session_state.get(key) or options[0]

        def rerun(self):
            raise AssertionError("rerun should not be called")

    stub = StreamlitStub()
    original_st = test_editor_component.st
    original_shared_st = suite_editor_component.st
    original_editor_shared_st = test_editor_component.shared.st
    original_render_commands = test_editor_component._render_test_editor_commands_section
    original_render_datasources = test_editor_component._render_test_editor_datasources_section
    try:
        test_editor_component.st = stub
        suite_editor_component.st = stub
        test_editor_component.shared.st = stub
        test_editor_component._render_test_editor_commands_section = lambda *args, **kwargs: rendered_sections.append("commands")
        test_editor_component._render_test_editor_datasources_section = lambda *args, **kwargs: rendered_sections.append("datasources")
        test_editor_component._render_test_editor_item(current_test, 1, {"tests": [current_test]}, {})
    finally:
        test_editor_component.st = original_st
        suite_editor_component.st = original_shared_st
        test_editor_component.shared.st = original_editor_shared_st
        test_editor_component._render_test_editor_commands_section = original_render_commands
        test_editor_component._render_test_editor_datasources_section = original_render_datasources

    assert rendered_sections == ["commands"]


def test_test_editor_item_uses_persisted_datasources_tab_selection():
    _reset_session_state()
    current_test = {
        "_ui_key": "test-ui-1",
        "description": "Editable test",
        "sources": [],
        "operations": [],
    }
    streamlit_module = sys.modules["streamlit"]
    streamlit_module.session_state[
        f"{test_editor_component.TEST_EDITOR_SECTION_TAB_KEY}_test-ui-1"
    ] = test_editor_component.TEST_EDITOR_SECTION_DATASOURCES_TAB
    rendered_sections: list[str] = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = streamlit_module.session_state

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def button(self, *args, **kwargs):
            return False

        def segmented_control(self, label, options, key=None, **kwargs):
            return self.session_state.get(key) or options[0]

        def rerun(self):
            raise AssertionError("rerun should not be called")

    stub = StreamlitStub()
    original_st = test_editor_component.st
    original_shared_st = suite_editor_component.st
    original_editor_shared_st = test_editor_component.shared.st
    original_render_commands = test_editor_component._render_test_editor_commands_section
    original_render_datasources = test_editor_component._render_test_editor_datasources_section
    try:
        test_editor_component.st = stub
        suite_editor_component.st = stub
        test_editor_component.shared.st = stub
        test_editor_component._render_test_editor_commands_section = lambda *args, **kwargs: rendered_sections.append("commands")
        test_editor_component._render_test_editor_datasources_section = lambda *args, **kwargs: rendered_sections.append("datasources")
        test_editor_component._render_test_editor_item(current_test, 1, {"tests": [current_test]}, {})
    finally:
        test_editor_component.st = original_st
        suite_editor_component.st = original_shared_st
        test_editor_component.shared.st = original_editor_shared_st
        test_editor_component._render_test_editor_commands_section = original_render_commands
        test_editor_component._render_test_editor_datasources_section = original_render_datasources

    assert rendered_sections == ["datasources"]


def test_test_editor_add_command_popover_opens_specific_dialog():
    _reset_session_state()
    current_test = {
        "_ui_key": "test-ui-1",
        "description": "Editable test",
    }
    opened_dialogs: list[tuple[str, str]] = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state
            self.button_calls = []

        def popover(self, label, **kwargs):
            self.button_calls.append({"label": label, "kind": "popover"})

            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def button(self, *args, **kwargs):
            payload = dict(kwargs)
            if args:
                payload["label"] = args[0]
            self.button_calls.append(payload)
            return args and args[0] == "Variable"

        def rerun(self):
            self.session_state["_rerun_called"] = True

    stub = StreamlitStub()
    original_st = test_editor_component.st
    original_open_dialog = test_editor_component.shared._open_test_command_dialog_for_item
    try:
        test_editor_component.st = stub
        test_editor_component.shared._open_test_command_dialog_for_item = (
            lambda item_ui_key, command_group: opened_dialogs.append((item_ui_key, command_group))
        )
        test_editor_component._render_test_editor_add_command_popover(current_test)
    finally:
        test_editor_component.st = original_st
        test_editor_component.shared._open_test_command_dialog_for_item = original_open_dialog

    assert opened_dialogs == [("test-ui-1", "constant")]
    labels = [call["label"] for call in stub.button_calls if "label" in call]
    assert labels == ["+ Add command", "Action", "Variable", "Assert"]
    assert sys.modules["streamlit"].session_state["_rerun_called"] is True


def test_test_editor_api_command_editor_defaults_to_params_tab():
    _reset_session_state()
    item = {
        "_ui_key": "test-ui-1",
        "operations": [
            {
                "_ui_key": "op-ui-1",
                "description": "Call API",
                "configuration_json": {
                    "commandCode": "readApi",
                    "commandType": "action",
                    "url": "https://api.example.com/orders",
                },
            }
        ],
    }
    draft = {"tests": [item]}
    rendered_sections: list[str] = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def text_input(self, *args, **kwargs):
            return None

        def selectbox(self, *args, **kwargs):
            return None

        def number_input(self, *args, **kwargs):
            return None

        def segmented_control(self, label, options, key=None, **kwargs):
            return self.session_state.get(key) or options[0]

    stub = StreamlitStub()
    original_st = test_editor_component.st
    original_render_kv = test_editor_component._render_api_kv_section
    original_render_auth = test_editor_component._render_api_auth_section
    original_render_body = test_editor_component._render_api_body_section
    try:
        test_editor_component.st = stub
        test_editor_component._render_api_kv_section = (
            lambda item, operation_ui_key, section, rows, runtime_values: rendered_sections.append(section)
        )
        test_editor_component._render_api_auth_section = (
            lambda item, operation_ui_key, prefix, runtime_values: rendered_sections.append("auth")
        )
        test_editor_component._render_api_body_section = (
            lambda item, operation_ui_key, prefix, runtime_values, body_sources: rendered_sections.append("body")
        )
        test_editor_component._render_api_command_editor(item, draft, item["operations"][0], 0, "op-ui-1")
    finally:
        test_editor_component.st = original_st
        test_editor_component._render_api_kv_section = original_render_kv
        test_editor_component._render_api_auth_section = original_render_auth
        test_editor_component._render_api_body_section = original_render_body

    assert rendered_sections == ["params"]


def test_test_editor_api_command_save_forces_persist():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    operation_ui_key = "op-ui-1"
    prefix = f"test_editor_api_command_{operation_ui_key}"
    streamlit_module.session_state[f"{prefix}_url"] = "https://api.example.com/orders/42"
    streamlit_module.session_state[f"{prefix}_timeout"] = 15
    streamlit_module.session_state[f"{prefix}_result_target"] = "apiResult"

    item = {"operations": []}
    current_operation = {
        "_ui_key": operation_ui_key,
        "description": "Read orders",
        "operation_type": "readApi",
        "configuration_json": {
            "commandCode": "readApi",
            "commandType": "action",
            "url": "https://api.example.com/orders",
            "timeoutSeconds": 30,
        },
    }
    item["operations"].append(current_operation)
    persist_calls = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = streamlit_module.session_state

        def error(self, *args, **kwargs):
            raise AssertionError(f"Unexpected validation error: {args!r} {kwargs!r}")

    stub = StreamlitStub()
    original_st = test_editor_component.st
    original_persist = test_editor_component._persist_test_editor_operation_update
    try:
        test_editor_component.st = stub

        def _persist_spy(*args, **kwargs):
            persist_calls.append({"args": args, "kwargs": kwargs})
            return False

        test_editor_component._persist_test_editor_operation_update = _persist_spy
        saved = test_editor_component._save_test_editor_command(
            {"tests": [item]},
            item,
            current_operation,
            0,
            operation_ui_key,
            {
                "editor_kind": "api",
                "prefix": prefix,
                "is_write": False,
                "description_key": f"{prefix}_description",
                "method_key": f"{prefix}_method",
                "url_key": f"{prefix}_url",
                "params_state_key": f"{prefix}_params_rows",
                "path_state_key": f"{prefix}_path_rows",
                "auth_state_key": f"{prefix}_auth",
                "headers_state_key": f"{prefix}_headers_rows",
                "body_type_key": f"{prefix}_body_type",
                "body_node_key": f"{prefix}_body_node",
                "timeout_key": f"{prefix}_timeout",
                "result_target_key": f"{prefix}_result_target",
            },
        )
    finally:
        test_editor_component.st = original_st
        test_editor_component._persist_test_editor_operation_update = original_persist

    assert saved is False
    assert len(persist_calls) == 1
    persist_call = persist_calls[0]
    assert persist_call["kwargs"]["force_persist"] is True
    assert persist_call["args"][3]["configuration_json"]["url"] == "https://api.example.com/orders/42"
    assert persist_call["args"][3]["configuration_json"]["timeoutSeconds"] == 15
    assert persist_call["args"][3]["configuration_json"]["result_target"] == "$.result.constants.apiResult"


def test_test_editor_collect_visible_form_runtime_values_filters_dataset_and_json_array(monkeypatch):
    filtered_input = [
        {"definitionId": "def-json", "name": "payload", "value_type": "json"},
        {"definitionId": "def-raw", "name": "tenant", "value_type": "raw"},
        {"definitionId": "def-dataset", "name": "rows", "value_type": "dataset"},
        {"definitionId": "def-array", "name": "items", "value_type": "jsonArray"},
    ]
    monkeypatch.setattr(
        test_editor_component,
        "_collect_visible_api_runtime_values",
        lambda draft, item, stop_before_index: filtered_input,
    )

    values = test_editor_component._collect_visible_api_form_runtime_values(
        {"tests": []},
        {"operations": []},
        stop_before_index=0,
    )

    assert values == [
        {"definitionId": "def-json", "name": "payload", "value_type": "json"},
        {"definitionId": "def-raw", "name": "tenant", "value_type": "raw"},
    ]


def test_test_editor_api_command_save_persists_form_urlencoded_body():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    operation_ui_key = "op-ui-form"
    prefix = f"test_editor_api_command_{operation_ui_key}"
    streamlit_module.session_state[f"{prefix}_url"] = "https://api.example.com/oauth/token"
    streamlit_module.session_state[f"{prefix}_timeout"] = 12
    streamlit_module.session_state[f"{prefix}_result_target"] = "tokenResult"
    streamlit_module.session_state[f"{prefix}_method"] = "POST"
    streamlit_module.session_state[f"{prefix}_body_type"] = "formUrlEncoded"
    streamlit_module.session_state[f"{prefix}_auth_type"] = "none"
    streamlit_module.session_state[f"{prefix}_form_body_rows"] = [
        {
            "row_id": "row-literal",
            "key": "grant_type",
            "node": {"kind": "literal", "value": "client_credentials"},
        },
        {
            "row_id": "row-runtime",
            "key": "access_token",
            "node": {
                "kind": "runtimeValue",
                "definitionId": "def-json",
                "fieldPath": "payload.access_token",
            },
        },
    ]

    item = {"operations": []}
    current_operation = {
        "_ui_key": operation_ui_key,
        "description": "Write token",
        "operation_type": "writeApi",
        "configuration_json": {
            "commandCode": "writeApi",
            "commandType": "action",
            "method": "POST",
            "url": "https://api.example.com/oauth/token",
            "bodyType": "formUrlEncoded",
            "timeoutSeconds": 30,
        },
    }
    item["operations"].append(current_operation)
    persist_calls = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = streamlit_module.session_state

        def error(self, *args, **kwargs):
            raise AssertionError(f"Unexpected validation error: {args!r} {kwargs!r}")

    stub = StreamlitStub()
    original_st = test_editor_component.st
    original_persist = test_editor_component._persist_test_editor_operation_update
    try:
        test_editor_component.st = stub

        def _persist_spy(*args, **kwargs):
            persist_calls.append({"args": args, "kwargs": kwargs})
            return False

        test_editor_component._persist_test_editor_operation_update = _persist_spy
        saved = test_editor_component._save_test_editor_command(
            {"tests": [item]},
            item,
            current_operation,
            0,
            operation_ui_key,
            {
                "editor_kind": "api",
                "prefix": prefix,
                "is_write": True,
                "description_key": f"{prefix}_description",
                "method_key": f"{prefix}_method",
                "url_key": f"{prefix}_url",
                "params_state_key": f"{prefix}_params_rows",
                "path_state_key": f"{prefix}_path_rows",
                "auth_state_key": f"{prefix}_auth",
                "headers_state_key": f"{prefix}_headers_rows",
                "body_type_key": f"{prefix}_body_type",
                "body_node_key": f"{prefix}_body_node",
                "form_body_rows_key": f"{prefix}_form_body_rows",
                "timeout_key": f"{prefix}_timeout",
                "result_target_key": f"{prefix}_result_target",
            },
        )
    finally:
        test_editor_component.st = original_st
        test_editor_component._persist_test_editor_operation_update = original_persist

    assert saved is False
    assert len(persist_calls) == 1
    persisted_cfg = persist_calls[0]["args"][3]["configuration_json"]
    assert persisted_cfg["bodyType"] == "formUrlEncoded"
    assert persisted_cfg["body"] == {
        "grant_type": {"kind": "literal", "value": "client_credentials"},
        "access_token": {
            "kind": "runtimeValue",
            "definitionId": "def-json",
            "fieldPath": "payload.access_token",
        },
    }


def test_save_test_editor_api_command_preserves_selected_api_tab():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    operation_ui_key = "op-ui-1"
    prefix = f"test_editor_api_command_{operation_ui_key}"
    api_tab_key = test_editor_component._api_editor_tab_state_key(operation_ui_key)
    streamlit_module.session_state[api_tab_key] = "Headers"
    streamlit_module.session_state[f"{prefix}_url"] = "https://api.example.com/orders/42"
    streamlit_module.session_state[f"{prefix}_timeout"] = 15
    streamlit_module.session_state[f"{prefix}_result_target"] = "apiResult"
    streamlit_module.session_state[f"{prefix}_auth_type"] = "none"

    item = {"operations": []}
    current_operation = {
        "_ui_key": operation_ui_key,
        "description": "Read orders",
        "operation_type": "readApi",
        "configuration_json": {
            "commandCode": "readApi",
            "commandType": "action",
            "url": "https://api.example.com/orders",
            "timeoutSeconds": 30,
        },
    }
    item["operations"].append(current_operation)

    class StreamlitStub:
        def __init__(self):
            self.session_state = streamlit_module.session_state

        def error(self, *args, **kwargs):
            raise AssertionError(f"Unexpected validation error: {args!r} {kwargs!r}")

    stub = StreamlitStub()
    original_st = test_editor_component.st
    original_persist = test_editor_component._persist_test_editor_operation_update
    try:
        test_editor_component.st = stub
        test_editor_component._persist_test_editor_operation_update = lambda *args, **kwargs: True
        saved = test_editor_component._save_test_editor_command(
            {"tests": [item]},
            item,
            current_operation,
            0,
            operation_ui_key,
            {
                "editor_kind": "api",
                "prefix": prefix,
                "is_write": False,
                "description_key": f"{prefix}_description",
                "method_key": f"{prefix}_method",
                "url_key": f"{prefix}_url",
                "params_state_key": f"{prefix}_params_rows",
                "path_state_key": f"{prefix}_path_rows",
                "auth_state_key": f"{prefix}_auth",
                "headers_state_key": f"{prefix}_headers_rows",
                "body_type_key": f"{prefix}_body_type",
                "body_node_key": f"{prefix}_body_node",
                "timeout_key": f"{prefix}_timeout",
                "result_target_key": f"{prefix}_result_target",
            },
        )
    finally:
        test_editor_component.st = original_st
        test_editor_component._persist_test_editor_operation_update = original_persist

    assert saved is True
    assert streamlit_module.session_state[api_tab_key] == "Headers"
    assert f"{prefix}_url" not in streamlit_module.session_state


def test_test_editor_api_command_editor_uses_persisted_tab_selection():
    _reset_session_state()
    item = {
        "_ui_key": "test-ui-1",
        "operations": [
            {
                "_ui_key": "op-ui-1",
                "description": "Call API",
                "configuration_json": {
                    "commandCode": "readApi",
                    "commandType": "action",
                    "url": "https://api.example.com/orders",
                },
            }
        ],
    }
    draft = {"tests": [item]}
    rendered_sections: list[str] = []
    sys.modules["streamlit"].session_state[
        test_editor_component._api_editor_tab_state_key("op-ui-1")
    ] = "Headers"

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def text_input(self, *args, **kwargs):
            return None

        def selectbox(self, *args, **kwargs):
            return None

        def number_input(self, *args, **kwargs):
            return None

        def segmented_control(self, label, options, key=None, **kwargs):
            return self.session_state.get(key) or options[0]

    stub = StreamlitStub()
    original_st = test_editor_component.st
    original_render_kv = test_editor_component._render_api_kv_section
    original_render_auth = test_editor_component._render_api_auth_section
    original_render_body = test_editor_component._render_api_body_section
    try:
        test_editor_component.st = stub
        test_editor_component._render_api_kv_section = (
            lambda item, operation_ui_key, section, rows, runtime_values: rendered_sections.append(section)
        )
        test_editor_component._render_api_auth_section = (
            lambda item, operation_ui_key, prefix, runtime_values: rendered_sections.append("auth")
        )
        test_editor_component._render_api_body_section = (
            lambda item, operation_ui_key, prefix, runtime_values, body_sources: rendered_sections.append("body")
        )
        test_editor_component._render_api_command_editor(item, draft, item["operations"][0], 0, "op-ui-1")
    finally:
        test_editor_component.st = original_st
        test_editor_component._render_api_kv_section = original_render_kv
        test_editor_component._render_api_auth_section = original_render_auth
        test_editor_component._render_api_body_section = original_render_body

    assert rendered_sections == ["headers"]


def test_suite_editor_inline_api_command_reopens_when_requested():
    _reset_session_state()
    sys.modules["streamlit"].session_state[suite_editor_component.INLINE_API_REOPEN_COMMAND_UI_KEY] = "op-ui-1"
    item = {"_ui_key": "item-ui-1"}
    operation = {
        "_ui_key": "op-ui-1",
        "description": "Call API",
        "configuration_json": {
            "commandCode": "readApi",
            "commandType": "action",
            "url": "https://api.example.com/orders",
        },
    }
    captured: dict[str, object] = {}

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def expander(self, label, expanded=False):
            captured["label"] = label
            captured["expanded"] = expanded

            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def button(self, *args, **kwargs):
            return False

        def text_input(self, *args, **kwargs):
            return None

        def selectbox(self, *args, **kwargs):
            return None

        def tabs(self, labels):
            class _Tab:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Tab() for _ in labels]

        def number_input(self, *args, **kwargs):
            return None

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_render_kv = suite_editor_component.render_kv_rows_container
    original_render_auth = suite_editor_component.render_auth_editor
    try:
        suite_editor_component.st = stub
        suite_editor_component.render_kv_rows_container = lambda **kwargs: []
        suite_editor_component.render_auth_editor = lambda *args, **kwargs: None
        suite_editor_component._render_api_command_inline(
            item,
            operation,
            0,
            "hook",
            "item-ui-1",
            "op-ui-1",
            "action",
            operation["configuration_json"],
            "readApi",
            operation_index=0,
            is_first=True,
            is_last=True,
            action_label="command",
        )
    finally:
        suite_editor_component.st = original_st
        suite_editor_component.render_kv_rows_container = original_render_kv
        suite_editor_component.render_auth_editor = original_render_auth

    assert captured["expanded"] is True


def test_suite_editor_inline_api_command_delete_button_is_inside_expander():
    _reset_session_state()
    item = {"_ui_key": "item-ui-1"}
    operation = {
        "_ui_key": "op-ui-1",
        "description": "Call API",
        "configuration_json": {
            "commandCode": "readApi",
            "commandType": "action",
            "url": "https://api.example.com/orders",
        },
    }
    captured_keys: list[str] = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = sys.modules["streamlit"].session_state

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def expander(self, label, expanded=False):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def button(self, *args, **kwargs):
            captured_keys.append(str(kwargs.get("key") or ""))
            return False

        def text_input(self, *args, **kwargs):
            return None

        def selectbox(self, *args, **kwargs):
            return None

        def tabs(self, labels):
            class _Tab:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Tab() for _ in labels]

        def number_input(self, *args, **kwargs):
            return None

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_render_kv = suite_editor_component.render_kv_rows_container
    original_render_auth = suite_editor_component.render_auth_editor
    try:
        suite_editor_component.st = stub
        suite_editor_component.render_kv_rows_container = lambda **kwargs: []
        suite_editor_component.render_auth_editor = lambda *args, **kwargs: None
        suite_editor_component._render_api_command_inline(
            item,
            operation,
            0,
            "hook",
            "item-ui-1",
            "op-ui-1",
            "action",
            operation["configuration_json"],
            "readApi",
            operation_index=0,
            is_first=True,
            is_last=True,
            action_label="command",
        )
    finally:
        suite_editor_component.st = original_st
        suite_editor_component.render_kv_rows_container = original_render_kv
        suite_editor_component.render_auth_editor = original_render_auth

    assert "suite_inline_api_item-ui-1_op-ui-1_delete" in captured_keys
    assert "suite_editor_delete_command_item-ui-1_op-ui-1" not in captured_keys


def test_suite_editor_inline_api_command_save_persists_current_draft():
    _reset_session_state()
    streamlit_module = sys.modules["streamlit"]
    item = {
        "_ui_key": "hook-ui-1",
        "kind": "hook",
        "hook_phase": "before-all",
        "operations": [],
    }
    operation = {
        "_ui_key": "op-ui-1",
        "description": "Call API",
        "configuration_json": {
            "commandCode": "readApi",
            "commandType": "action",
            "url": "https://api.example.com/orders",
            "timeoutSeconds": 30,
        },
    }
    item["operations"].append(operation)
    prefix = "suite_inline_api_hook-ui-1_op-ui-1"
    streamlit_module.session_state[f"{prefix}_url"] = "https://api.example.com/orders/42"
    streamlit_module.session_state[f"{prefix}_timeout"] = 10
    streamlit_module.session_state[f"{prefix}_result_target"] = "apiResult"
    persist_calls = []

    class StreamlitStub:
        def __init__(self):
            self.session_state = streamlit_module.session_state

        def columns(self, spec, **kwargs):
            class _Col:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Col() for _ in spec]

        def expander(self, label, expanded=False):
            class _Ctx:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def button(self, *args, **kwargs):
            return kwargs.get("key") == f"{prefix}_save"

        def text_input(self, *args, **kwargs):
            return None

        def selectbox(self, *args, **kwargs):
            return None

        def tabs(self, labels):
            class _Tab:
                def __enter__(self_inner):
                    return None

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return [_Tab() for _ in labels]

        def number_input(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            raise AssertionError(f"Unexpected error: {args!r} {kwargs!r}")

        def rerun(self):
            self.session_state["_rerun_called"] = True

    stub = StreamlitStub()
    original_st = suite_editor_component.st
    original_render_kv = suite_editor_component.render_kv_rows_container
    original_render_auth = suite_editor_component.render_auth_editor
    original_collect_auth = suite_editor_component.collect_auth_editor_value
    original_rows_to_dict = suite_editor_component.rows_to_dict
    original_persist = suite_editor_component._persist_current_draft
    try:
        suite_editor_component.st = stub
        suite_editor_component.render_kv_rows_container = lambda **kwargs: []
        suite_editor_component.render_auth_editor = lambda *args, **kwargs: None
        suite_editor_component.collect_auth_editor_value = lambda *args, **kwargs: ({}, None)
        suite_editor_component.rows_to_dict = lambda rows, field_label: ({}, None)
        suite_editor_component._persist_current_draft = lambda **kwargs: persist_calls.append(kwargs)
        suite_editor_component._render_api_command_inline(
            item,
            operation,
            0,
            "hook",
            "hook-ui-1",
            "op-ui-1",
            "action",
            operation["configuration_json"],
            "readApi",
            operation_index=0,
            is_first=True,
            is_last=True,
            action_label="command",
        )
    finally:
        suite_editor_component.st = original_st
        suite_editor_component.render_kv_rows_container = original_render_kv
        suite_editor_component.render_auth_editor = original_render_auth
        suite_editor_component.collect_auth_editor_value = original_collect_auth
        suite_editor_component.rows_to_dict = original_rows_to_dict
        suite_editor_component._persist_current_draft = original_persist

    assert persist_calls == [{"success_message": "Command updated.", "rerun": False}]
    assert operation["configuration_json"]["url"] == "https://api.example.com/orders/42"
    assert operation["configuration_json"]["timeoutSeconds"] == 10
    assert operation["configuration_json"]["result_target"] == "$.result.constants.apiResult"
    assert streamlit_module.session_state["_rerun_called"] is True
