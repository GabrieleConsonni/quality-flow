from datetime import UTC, datetime

from sqlalchemy.orm import Session

from _alembic.models.suite_item_command_execution_entity import (
    SuiteItemOperationExecutionEntity,
)
from _alembic.models.suite_item_command_entity import SuiteItemOperationEntity
from _alembic.models.test_operation_execution_entity import TestOperationExecutionEntity
from _alembic.models.test_operation_entity import TestOperationEntity
from elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
    CleanDatasetConfigurationCommandDto,
    CleanTableConfigurationCommandDto,
    ConfigurationCommandDto,
    ConfigurationOperationTypes,
    DataConfigurationOperationDto,
    DeleteConstantConfigurationCommandDto,
    DropDatasetConfigurationCommandDto,
    DropTableConfigurationCommandDto,
    ExportDatasetConfigurationCommandDto,
    QueryDatabaseConfigurationCommandDto,
    ReadApiConfigurationCommandDto,
    ReceiveQueueConfigurationCommandDto,
    RunSuiteConfigurationCommandDto,
    SaveTableConfigurationCommandDto,
    SendMessageQueueConfigurationCommandDto,
    SleepConfigurationCommandDto,
    WriteApiConfigurationCommandDto,
    convert_to_config_command_type,
)
from elaborations.services.alembic.suite_item_command_execution_service import (
    SuiteItemOperationExecutionService,
)
from elaborations.services.alembic.test_operation_execution_service import (
    TestOperationExecutionService,
)
from elaborations.services.operations.assert_command_executor import (
    AssertOperationExecutor,
)
from elaborations.services.operations.clean_dataset_command_executor import (
    CleanDatasetOperationExecutor,
)
from elaborations.services.operations.clean_table_command_executor import (
    CleanTableOperationExecutor,
)
from elaborations.services.operations.init_constant_command_executor import (
    DataOperationExecutor,
)
from elaborations.services.operations.delete_constant_command_executor import (
    DeleteConstantOperationExecutor,
)
from elaborations.services.operations.drop_dataset_command_executor import (
    DropDatasetOperationExecutor,
)
from elaborations.services.operations.drop_table_command_executor import (
    DropTableOperationExecutor,
)
from elaborations.services.operations.http_command_executor import (
    HttpOperationExecutor,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.operations.command_policy_validator import (
    validate_operation_policy,
)
from elaborations.services.operations.command_scope import resolve_execution_scope
from elaborations.services.operations.query_database_command_executor import (
    QueryDatabaseOperationExecutor,
)
from elaborations.services.operations.receive_queue_command_executor import (
    ReceiveQueueOperationExecutor,
)
from elaborations.services.operations.send_message_queue_command_executor import (
    PublishToQueueOperationExecutor,
)
from elaborations.services.operations.run_suite_command_executor import (
    RunSuiteOperationExecutor,
)
from elaborations.services.operations.export_dataset_command_executor import (
    SaveToExternalDbOperationExecutor,
)
from elaborations.services.operations.save_table_command_executor import (
    SaveInternalDbOperationExecutor,
)
from elaborations.services.operations.sleep_command_executor import SleepOperationExecutor
from elaborations.services.suite_runs.execution_event_bus import (
    publish_execution_event,
    publish_runtime_log_event,
)
from elaborations.services.suite_runs.execution_runtime_context import (
    get_execution_id,
    get_suite_execution_id,
    get_suite_item_execution_id,
    get_suite_item_id,
    get_suite_test_execution_id,
    get_suite_test_id,
    get_test_suite_execution_id,
)
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService

_EXECUTOR_MAPPING: dict[type[ConfigurationCommandDto], type[OperationExecutor]] = {
    DataConfigurationOperationDto: DataOperationExecutor,
    DeleteConstantConfigurationCommandDto: DeleteConstantOperationExecutor,
    SleepConfigurationCommandDto: SleepOperationExecutor,
    ReadApiConfigurationCommandDto: HttpOperationExecutor,
    WriteApiConfigurationCommandDto: HttpOperationExecutor,
    SendMessageQueueConfigurationCommandDto: PublishToQueueOperationExecutor,
    SaveTableConfigurationCommandDto: SaveInternalDbOperationExecutor,
    DropTableConfigurationCommandDto: DropTableOperationExecutor,
    CleanTableConfigurationCommandDto: CleanTableOperationExecutor,
    ExportDatasetConfigurationCommandDto: SaveToExternalDbOperationExecutor,
    DropDatasetConfigurationCommandDto: DropDatasetOperationExecutor,
    CleanDatasetConfigurationCommandDto: CleanDatasetOperationExecutor,
    RunSuiteConfigurationCommandDto: RunSuiteOperationExecutor,
    ReceiveQueueConfigurationCommandDto: ReceiveQueueOperationExecutor,
    QueryDatabaseConfigurationCommandDto: QueryDatabaseOperationExecutor,
    AssertConfigurationCommandDto: AssertOperationExecutor,
}


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def log(message: str, level: LogLevel = LogLevel.INFO):
    log_dto = LogDto(
        subject_type=LogSubjectType.OPERATION_EXECUTION,
        subject="N/A",
        message=message,
        level=level,
    )
    LogService().log(log_dto)
    publish_runtime_log_event(
        subject_type=LogSubjectType.OPERATION_EXECUTION,
        subject="N/A",
        level=level,
        message=message,
    )


def _resolve_operation_payload(
    operation_input: TestOperationEntity | SuiteItemOperationEntity,
) -> tuple[str, dict, str, int]:
    if not isinstance(operation_input, (TestOperationEntity, SuiteItemOperationEntity)):
        message = "Unsupported command input. Commands must be persisted on their owning context."
        log(message, level=LogLevel.ERROR)
        raise TypeError(message)

    operation_id = str(operation_input.id)
    cfg_json = (
        operation_input.configuration_json
        if isinstance(operation_input.configuration_json, dict)
        else {}
    )
    operation_description = str(operation_input.description or "")
    operation_order = int(operation_input.order or 0)
    return operation_id, cfg_json, operation_description, operation_order


def execute_operations(
    session: Session,
    operations: list[TestOperationEntity] | list[SuiteItemOperationEntity],
    data,
    execution_scope: str | None = None,
) -> ExecutionResultDto:
    execution_result = ExecutionResultDto(data=data, result=[])
    operation_execution_service = TestOperationExecutionService()
    suite_operation_execution_service = SuiteItemOperationExecutionService()
    resolved_execution_scope = resolve_execution_scope(execution_scope)

    log(f"Starting execution {len(operations)} commands")

    for operation_input in operations:
        op_id, op_cfg_json, op_description, op_order = _resolve_operation_payload(operation_input)

        suite_execution_id = str(get_suite_execution_id() or "").strip()
        suite_test_execution_id = str(get_suite_test_execution_id() or "").strip()
        suite_test_id = str(get_suite_test_id() or "").strip()
        test_suite_execution_id = str(get_test_suite_execution_id() or "").strip()
        suite_item_execution_id = str(get_suite_item_execution_id() or "").strip()
        suite_item_id = str(get_suite_item_id() or "").strip()

        operation_execution_id = ""
        suite_operation_execution_id = ""
        if suite_execution_id and suite_test_execution_id:
            operation_execution_id = operation_execution_service.insert(
                session,
                TestOperationExecutionEntity(
                    suite_execution_id=suite_execution_id,
                    suite_test_execution_id=suite_test_execution_id,
                    suite_test_id=suite_test_id or None,
                    test_operation_id=op_id or None,
                    operation_description=op_description,
                    operation_order=op_order,
                    status="running",
                ),
            )
        if test_suite_execution_id and suite_item_execution_id:
            suite_operation_execution_id = suite_operation_execution_service.insert(
                session,
                SuiteItemOperationExecutionEntity(
                    test_suite_execution_id=test_suite_execution_id,
                    suite_item_execution_id=suite_item_execution_id,
                    suite_item_id=suite_item_id or None,
                    suite_item_operation_id=op_id or None,
                    operation_description=op_description,
                    operation_order=op_order,
                    status="running",
                ),
            )

        cfg = convert_to_config_command_type(op_cfg_json)
        contract = None
        try:
            contract = validate_operation_policy(cfg, resolved_execution_scope)
            new_execution_result = execute_operation(session, op_id, cfg, execution_result.data)
            execution_result.extend(new_execution_result)
            if operation_execution_id:
                operation_execution_service.update(
                    session,
                    operation_execution_id,
                    status="success",
                    error_message=None,
                    finished_at=_utc_now(),
                )
            if suite_operation_execution_id:
                suite_operation_execution_service.update(
                    session,
                    suite_operation_execution_id,
                    status="success",
                    error_message=None,
                    finished_at=_utc_now(),
                )
            execution_id = get_execution_id()
            if execution_id:
                publish_execution_event(
                    execution_id,
                    "command_finished",
                    {
                        "suite_test_id": suite_test_id,
                        "suite_test_execution_id": suite_test_execution_id or None,
                        "test_operation_execution_id": operation_execution_id or None,
                        "suite_item_id": suite_item_id or None,
                        "suite_item_execution_id": suite_item_execution_id or None,
                        "suite_item_operation_execution_id": suite_operation_execution_id or None,
                        "command_id": op_id,
                        "command_description": op_description,
                        "command_scope": resolved_execution_scope,
                        "command_family": contract.family if contract else None,
                        "status": "success",
                        "result": new_execution_result.result,
                    },
                )
        except Exception as op_exception:
            if operation_execution_id:
                operation_execution_service.update(
                    session,
                    operation_execution_id,
                    status="error",
                    error_message=str(op_exception),
                    finished_at=_utc_now(),
                )
            if suite_operation_execution_id:
                suite_operation_execution_service.update(
                    session,
                    suite_operation_execution_id,
                    status="error",
                    error_message=str(op_exception),
                    finished_at=_utc_now(),
                )
            execution_id = get_execution_id()
            if execution_id:
                publish_execution_event(
                    execution_id,
                    "command_finished",
                    {
                        "suite_test_id": suite_test_id,
                        "suite_test_execution_id": suite_test_execution_id or None,
                        "test_operation_execution_id": operation_execution_id or None,
                        "suite_item_id": suite_item_id or None,
                        "suite_item_execution_id": suite_item_execution_id or None,
                        "suite_item_operation_execution_id": suite_operation_execution_id or None,
                        "command_id": op_id,
                        "command_description": op_description,
                        "command_scope": resolved_execution_scope,
                        "command_family": contract.family if contract else None,
                        "status": "error",
                        "error": str(op_exception),
                    },
                )
            raise

    return execution_result


def execute_operation(
    session: Session,
    operation_id: str,
    cfg: ConfigurationOperationTypes,
    data,
) -> ExecutionResultDto:
    clazz = _EXECUTOR_MAPPING.get(type(cfg))
    if clazz is None:
        supported_types = list(_EXECUTOR_MAPPING.keys())
        message = f"Unsupported command type: {cfg}. Supported types: {supported_types}"
        log(message, level=LogLevel.ERROR)
        raise ValueError(message)
    command_executor = clazz()
    return command_executor.execute(session, operation_id, cfg, data)

