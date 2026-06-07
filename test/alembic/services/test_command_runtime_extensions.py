from app.elaborations.models.dtos.configuration_command_dto import (
    DataConfigurationOperationDto,
    RunSuiteConfigurationOperationDto,
)
from app.elaborations.services.operations.init_constant_command_executor import (
    DataOperationExecutor,
)
from app.elaborations.services.operations.run_suite_command_executor import (
    RunSuiteOperationExecutor,
)
from elaborations.services.suite_runs.run_context import (
    bind_run_context,
    create_run_context,
)


def _disable_command_logging(monkeypatch):
    import elaborations.services.operations.command_executor as command_executor_module

    monkeypatch.setattr(
        command_executor_module.OperationExecutor,
        "log",
        classmethod(lambda cls, *args, **kwargs: None),
    )


def test_init_constant_command_writes_local_constant(monkeypatch):
    _disable_command_logging(monkeypatch)
    cfg = DataConfigurationOperationDto(
        definitionId="def-data",
        data=[{"id": 1}],
        target="$.local.actualRows",
    )
    run_context = create_run_context(run_id="run-data-target")

    with bind_run_context(run_context):
        DataOperationExecutor().execute(None, "cmd-data", cfg, [])

    assert run_context.local_vars["actualRows"] == [{"id": 1}]


def test_run_suite_command_writes_result_target(monkeypatch):
    _disable_command_logging(monkeypatch)
    import elaborations.services.test_suites.test_suite_executor_service as suite_service_module
    import app.elaborations.services.operations.run_suite_command_executor as run_suite_module

    monkeypatch.setattr(
        suite_service_module,
        "execute_test_suite_by_id",
        lambda suite_id, **kwargs: "suite-exec-1",
    )
    monkeypatch.setattr(
        run_suite_module,
        "resolve_definition_path",
        lambda _session, definition_id: (
            type("Definition", (), {"name": "order_id" if definition_id == "def-order-id" else "trigger"})(),
            "$.local.constants.order_id" if definition_id == "def-order-id" else "$.result.constants.trigger",
        ),
    )
    cfg = RunSuiteConfigurationOperationDto(
        suite_id="suite-1",
        constantRefs=[{"definitionId": "def-order-id"}],
        resultConstant={"definitionId": "def-trigger", "name": "trigger", "valueType": "json"},
    )
    run_context = create_run_context(
        run_id="run-suite-target",
        event={"payload": {"id": 1}},
    )
    run_context.local_scope["constants"]["order_id"] = "ORD-100"
    monkeypatch.setattr(
        run_suite_module,
        "write_result_constant",
        lambda _session, _result_constant, value: run_context.result_scope["constants"].__setitem__("trigger", value),
    )

    with bind_run_context(run_context):
        result = RunSuiteOperationExecutor().execute(
            None,
            "cmd-run-suite",
            cfg,
            [{"id": 1}],
        )

    assert result.result[0]["execution_id"] == "suite-exec-1"
    assert result.result[0]["constants"] == {"order_id": "ORD-100"}
    assert run_context.result_scope["constants"]["trigger"]["execution_id"] == "suite-exec-1"
    assert run_context.result_scope["constants"]["trigger"]["suite_id"] == "suite-1"
