from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    RunSuiteConfigurationCommandDto,
)
from elaborations.services.constants.command_constant_definition_registry import (
    resolve_definition_path,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import (
    build_run_context_scope,
    get_run_context,
)
from elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value
from elaborations.services.operations.command_data_resolver import write_result_constant


class RunSuiteOperationExecutor(OperationExecutor):
    @staticmethod
    def _resolve_suite_id(session: Session, cfg: RunSuiteConfigurationCommandDto) -> str:
        del session
        return str(cfg.suite_id or "").strip()

    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: RunSuiteConfigurationCommandDto,
        data,
    ) -> ExecutionResultDto:
        # Local import avoids circular dependency with test executor modules.
        from elaborations.services.test_suites.test_suite_executor_service import (
            execute_test_suite_by_id,
        )

        suite_id = self._resolve_suite_id(session, cfg)
        run_context = get_run_context()
        constants_payload: dict[str, object] = {}
        scope = build_run_context_scope(run_context)
        for constant_ref in cfg.runtimeValueRefs or []:
            definition, path = resolve_definition_path(session, constant_ref.definitionId)
            resolved_value = resolve_dynamic_value(path, scope)
            if resolved_value is not None:
                constants_payload[definition.name] = resolved_value

        execution_id = execute_test_suite_by_id(
            suite_id,
            run_event=run_context.event if run_context else {},
            vars_init=constants_payload,
            invocation_id=run_context.invocation_id if run_context else None,
        )
        message = (
            f"Test suite '{suite_id}' started with execution_id '{execution_id}'"
        )
        self.log(
            operation_id,
            message=message,
            payload={
                "suite_id": suite_id,
                "execution_id": execution_id,
                "constants": constants_payload,
                "invocation_id": run_context.invocation_id if run_context else None,
            },
        )
        result_payload = {
            "suite_id": suite_id,
            "execution_id": execution_id,
            "constants": constants_payload,
        }
        if cfg.resultConstant:
            write_result_constant(session, cfg.resultConstant, result_payload)
        return ExecutionResultDto(
            data=data,
            result=[
                {
                    "message": message,
                    **result_payload,
                }
            ],
        )


RunSuiteOperationExecutor = RunSuiteOperationExecutor

