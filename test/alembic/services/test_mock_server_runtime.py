import asyncio

from fastapi import BackgroundTasks

from app.mock_servers.api.mock_server_api import (
    activate_mock_server_api,
    create_mock_server_api,
    deactivate_mock_server_api,
    find_all_mock_servers_api,
    update_mock_server_api,
)
from app.mock_servers.models.dtos.mock_server_dto import (
    CreateMockServerDto,
    UpdateMockServerDto,
)
from app.mock_servers.models.runtime_models import (
    MockApiRoute,
    MockCommandSnapshot,
    MockRuntimeServer,
)
from app.mock_servers.services.runtime.mock_runtime_dispatcher import (
    dispatch_mock_runtime_request,
)


def _create_mock_server_payload(code_suffix: str = "1") -> dict:
    return {
        "code": f"mock_{code_suffix}",
        "description": "mock server test",
        "cfg": {"endpoint": f"orders-{code_suffix}"},
        "apis": [
            {
                "order": 1,
                "code": "get-orders",
                "description": "GET orders",
                "cfg": {
                    "method": "GET",
                    "path": "/orders",
                    "params": {"tenant": "it"},
                    "headers": {"x-env": "test"},
                    "response_status": 200,
                    "response_headers": {"Content-Type": "application/json"},
                    "response_body": {"ok": True},
                    "priority": 0,
                    "pre_response_commands": [],
                    "post_response_commands": [],
                },
                "commands": [],
            }
        ],
        "queues": [],
        "is_active": False,
    }


def test_mock_server_api_crud(monkeypatch, alembic_container):
    import app.mock_servers.api.mock_server_api as api_module

    monkeypatch.setattr(
        api_module.MockServerRuntimeRegistry,
        "start_server",
        lambda _mock_server_id: None,
    )
    monkeypatch.setattr(
        api_module.MockServerRuntimeRegistry,
        "stop_server",
        lambda _mock_server_id: None,
    )
    monkeypatch.setattr(
        api_module.MockServerRuntimeRegistry,
        "remove_server",
        lambda _mock_server_id: None,
    )

    create_response = asyncio.run(
        create_mock_server_api(CreateMockServerDto(**_create_mock_server_payload("crud")))
    )
    mock_server_id = str(create_response.get("id") or "").strip()
    assert mock_server_id

    all_servers = asyncio.run(find_all_mock_servers_api())
    created_server = next((item for item in all_servers if item.get("id") == mock_server_id), {})
    assert created_server.get("endpoint") == "orders-crud"
    assert len(created_server.get("apis") or []) == 1

    update_payload = _create_mock_server_payload("crud")
    update_payload["id"] = mock_server_id
    update_payload["description"] = "updated mock server"
    update_payload["is_active"] = True
    update_response = asyncio.run(update_mock_server_api(UpdateMockServerDto(**update_payload)))
    assert update_response.get("id") == mock_server_id

    activate_response = asyncio.run(activate_mock_server_api(mock_server_id))
    deactivate_response = asyncio.run(deactivate_mock_server_api(mock_server_id))
    assert activate_response["id"] == mock_server_id
    assert deactivate_response["id"] == mock_server_id


def test_dispatch_mock_runtime_request_matches_and_schedules_post_command(monkeypatch):
    import app.mock_servers.services.runtime.mock_runtime_dispatcher as dispatcher_module

    captured: dict[str, object] = {}

    def _fake_execute_mock_operations(**kwargs):
        captured.update(kwargs)

    runtime_server = MockRuntimeServer(
        id="server-1",
        code="mock_1",
        description="server",
        endpoint="orders",
        is_active=True,
        apis=[
            MockApiRoute(
                id="api-1",
                code="get_orders",
                description="get orders",
                order=1,
                method="GET",
                path="/orders",
                params={"tenant": "it"},
                headers={"x-env": "test"},
                body=None,
                body_match="contains",
                priority=0,
                response_status=200,
                response_headers={"Content-Type": "application/json"},
                response_body={"ok": True},
                commands=[
                    MockCommandSnapshot(
                        id="cmd-1",
                        code="runSuite",
                        description="run suite",
                        command_code="runSuite",
                        command_type="action",
                        configuration_json={
                            "commandCode": "runSuite",
                            "commandType": "action",
                            "suite_id": "suite-1",
                            "constants": [],
                        },
                        order=1,
                    )
                ],
            )
        ],
        queues=[],
    )

    monkeypatch.setattr(
        dispatcher_module.MockServerRuntimeRegistry,
        "get_server_by_endpoint",
        lambda _endpoint: runtime_server,
    )
    monkeypatch.setattr(
        dispatcher_module,
        "execute_mock_operations",
        _fake_execute_mock_operations,
    )
    monkeypatch.setattr(
        dispatcher_module,
        "_persist_mock_invocation",
        lambda **_kwargs: "inv-1",
    )
    monkeypatch.setattr(
        dispatcher_module,
        "log_mock_server_event",
        lambda *_args, **_kwargs: None,
    )

    background_tasks = BackgroundTasks()
    dispatch_result = dispatch_mock_runtime_request(
        server_endpoint="orders",
        method="GET",
        path="/orders",
        query_params={"tenant": "it"},
        headers={"x-env": "test"},
        body_raw="",
        body_json=None,
        background_tasks=background_tasks,
    )

    assert dispatch_result is not None
    status_code, headers, body = dispatch_result
    assert status_code == 200
    assert headers.get("X-QualityFlow-Trigger-Id")
    assert headers.get("X-QualityFlow-Invocation-Id") == "inv-1"
    assert isinstance(body, dict)
    assert body.get("ok") is True
    assert body.get("trigger_id")
    assert len(background_tasks.tasks) == 1

    task = background_tasks.tasks[0]
    task.func(*task.args, **task.kwargs)

    assert captured["mock_server_id"] == "server-1"
    assert captured["source_type"] == "api"
    assert captured["source_ref"] == "api-1"


def test_dispatch_mock_runtime_request_builds_response_from_run_envelope(monkeypatch):
    import app.mock_servers.services.runtime.mock_runtime_dispatcher as dispatcher_module

    runtime_server = MockRuntimeServer(
        id="server-1",
        code="mock_2",
        description="server",
        endpoint="orders-dynamic",
        is_active=True,
        apis=[
            MockApiRoute(
                id="api-1",
                code="post_orders",
                description="post orders",
                order=1,
                method="POST",
                path="/orders",
                params={},
                headers={},
                body=None,
                body_match="contains",
                priority=0,
                response_status={"$const": 202},
                response_headers={"Content-Type": "application/json"},
                response_body={
                    "ok": True,
                    "payload_id": {"$ref": "$.runEnvelope.event.payload.id"},
                },
            )
        ],
        queues=[],
    )

    monkeypatch.setattr(
        dispatcher_module.MockServerRuntimeRegistry,
        "get_server_by_endpoint",
        lambda _endpoint: runtime_server,
    )
    monkeypatch.setattr(
        dispatcher_module,
        "_persist_mock_invocation",
        lambda **_kwargs: "inv-2",
    )
    monkeypatch.setattr(
        dispatcher_module,
        "log_mock_server_event",
        lambda *_args, **_kwargs: None,
    )

    background_tasks = BackgroundTasks()
    dispatch_result = dispatch_mock_runtime_request(
        server_endpoint="orders-dynamic",
        method="POST",
        path="/orders",
        query_params={},
        headers={},
        body_raw="",
        body_json={"id": 1},
        background_tasks=background_tasks,
    )

    assert dispatch_result is not None
    status_code, headers, body = dispatch_result
    assert status_code == 202
    assert headers.get("X-QualityFlow-Invocation-Id") == "inv-2"
    assert body.get("ok") is True
    assert body.get("payload_id") == 1
