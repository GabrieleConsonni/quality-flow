from sqlalchemy.orm import Session

from elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
)
from elaborations.services.asserts.assert_evaluator_composite import evaluate_assert
from elaborations.services.operations.command_data_resolver import resolve_input_reference
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import append_assert_artifact, build_run_context_scope
from elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value
from logs.models.enums.log_level import LogLevel


class AssertOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: AssertConfigurationCommandDto,
        data,
    ) -> ExecutionResultDto:
        scope = build_run_context_scope()
        resolved_actual, _actual_type = resolve_input_reference(session, cfg.actualRef, data)
        resolved_expected = (
            resolve_dynamic_value(cfg.expected, scope)
            if cfg.expected is not None
            else None
        )
        if resolved_expected is None and cfg.expectedRef is not None:
            resolved_expected, _expected_type = resolve_input_reference(session, cfg.expectedRef, data)
        data_to_evaluate = (
            resolved_actual if isinstance(resolved_actual, list) else data
        )

        try:
            evaluate_assert(
                session,
                cfg,
                data_to_evaluate,
                actual=resolved_actual,
                expected=resolved_expected,
            )
            append_assert_artifact(
                {
                    "command_id": operation_id,
                    "assert_type": cfg.assert_type,
                    "status": "passed",
                    "actual": resolved_actual,
                    "expected": resolved_expected,
                }
            )
        except Exception as exc:
            technical_message = str(exc)
            configured_message = str(cfg.error_message or "").strip()
            error_message = configured_message or technical_message
            append_assert_artifact(
                {
                    "command_id": operation_id,
                    "assert_type": cfg.assert_type,
                    "status": "failed",
                    "actual": resolved_actual,
                    "expected": resolved_expected,
                    "error": technical_message,
                }
            )
            self.log(
                operation_id,
                message=error_message,
                payload={"error": technical_message},
                level=LogLevel.ERROR,
            )
            raise ValueError(error_message) from exc

        message = (
            f"Assert '{cfg.commandCode}' passed for "
            f"'{cfg.evaluated_object_type}' data."
        )
        self.log(operation_id, message=message)
        return ExecutionResultDto(data=data, result=[{"message": message}])

