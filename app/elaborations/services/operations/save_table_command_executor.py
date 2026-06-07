import json
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from _alembic.services.alembic_config_service import url_from_env
from elaborations.models.dtos.configuration_command_dto import SaveTableConfigurationCommandDto
from elaborations.services.operations.command_data_resolver import (
    coerce_rows,
    resolve_input_reference,
    write_result_constant,
)
from elaborations.services.operations.command_executor import OperationExecutor, ExecutionResultDto
from sqlalchemy_utils.database_table_writer import DatabaseTableWriter


class SaveInternalDbOperationExecutor(OperationExecutor):
    def execute(self, session:Session,  operation_id:str, cfg: SaveTableConfigurationCommandDto, data)->ExecutionResultDto:
        engine = create_engine(url_from_env())
        input_data, _input_type = resolve_input_reference(session, cfg.inputRef, data)
        rows = coerce_rows(input_data)

        if not rows:
            message = f"No data to insert into {cfg.table_name} table"
            self.log(operation_id, message)
            return ExecutionResultDto(
                data=input_data,
                result=[{"message": message}]
            )

        sample_row = {}
        for d in rows:
            for key, value in d.items():
                sample_row[key] = value

        table = DatabaseTableWriter.ensure_table_exists(engine, cfg.table_name, sample_row)
        DatabaseTableWriter.insert_rows(engine, table, rows)

        message = f"Created {len(rows)} rows in {cfg.table_name} table"
        result_payload = {
            "table_name": cfg.table_name,
            "inserted_rows": len(rows),
        }
        if cfg.resultConstant:
            write_result_constant(session, cfg.resultConstant, result_payload)

        self.log(operation_id, message)

        return ExecutionResultDto(
            data=input_data,
            result=[{"message": message}]
        )

