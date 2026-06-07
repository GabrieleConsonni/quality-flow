"""Executor for the `queryDatabase` command (Phase 2 of the Test Suites refactor).

Runs an arbitrary SQL query on a configured database connection and writes
the resulting rows (list[dict]) to `cfg.target` (path inside the run context).
The data is also returned as `ExecutionResultDto.data` so downstream commands
(typically an assert) can consume it via `actualRef`.

Implementation notes:
* Uses the workspace's `create_sqlalchemy_engine` factory so all supported
  drivers (Postgres / Oracle / SQL Server) are covered transparently.
* The query is executed inside a single `engine.connect()` block; the engine
  is disposed at the end to avoid leaking connections on long-running tests.
* Rows are mapped to plain dicts (`row._mapping`) to keep the payload
  serializable end-to-end (logs, run context, assert evaluation).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from data_sources.services.alembic.database_connection_service import (
    load_database_connection,
)
from elaborations.models.dtos.configuration_command_dto import (
    QueryDatabaseConfigurationCommandDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import write_context_path
from exceptions.app_exception import QualityFlowAppException
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import (
    create_sqlalchemy_engine,
)


class QueryDatabaseOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: QueryDatabaseConfigurationCommandDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del data
        del session

        connection = load_database_connection(cfg.connection_id)
        if not connection:
            raise QualityFlowAppException(
                f"No database connection found with id [ {cfg.connection_id} ]"
            )

        engine = create_sqlalchemy_engine(connection)
        try:
            with engine.connect() as db_connection:
                result = db_connection.execute(text(cfg.query))
                rows = [dict(row._mapping) for row in result]
        finally:
            engine.dispose()

        if cfg.target:
            write_context_path(cfg.target, rows)

        message = (
            f"Query on connection '{cfg.connection_id}' returned {len(rows)} row(s)."
        )
        self.log(operation_id, message)
        return ExecutionResultDto(
            data=rows,
            result=[{"message": message}],
        )
