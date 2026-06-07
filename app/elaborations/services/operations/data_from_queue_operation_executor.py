import json
import time

from sqlalchemy.orm import Session

from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service_factory import QueueConnectionServiceFactory
from elaborations.models.dtos.configuration_command_dto import (
    DataFromQueueConfigurationOperationDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import write_context_path


class DataFromQueueOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: DataFromQueueConfigurationOperationDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del data
        queue = QueueService().get_by_id(session, cfg.queue_id)
        if not queue:
            raise ValueError(f"Queue '{cfg.queue_id}' not found")
        broker_connection: BrokerConnectionConfigTypes = load_broker_connection(queue.broker_id)
        service = QueueConnectionServiceFactory.get_service(broker_connection)

        retry = cfg.retry
        all_msgs = []
        while retry > 0 and len(all_msgs) < cfg.max_messages:
            remaining_messages = cfg.max_messages - len(all_msgs)
            msgs = service.receive_messages(
                broker_connection,
                queue_id=cfg.queue_id,
                max_messages=remaining_messages,
            )
            if not msgs:
                time.sleep(cfg.wait_time_seconds)
                retry -= 1
                continue
            all_msgs.extend(msgs)

        payload_rows = []
        for index, message in enumerate(all_msgs):
            if not isinstance(message, dict):
                raise ValueError(f"Message {index + 1} is not valid JSON.")
            body_value = message.get("Body") if "Body" in message else message
            if isinstance(body_value, str):
                try:
                    body_value = json.loads(body_value)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid body in message {index + 1}: {str(exc)}") from exc
            payload_rows.append(body_value)

        if cfg.target:
            write_context_path(cfg.target, payload_rows)
        self.log(operation_id, f"Loaded {len(payload_rows)} row(s) from queue '{queue.code}'.")
        return ExecutionResultDto(
            data=payload_rows,
            result=[{"message": f"Loaded {len(payload_rows)} row(s) from queue '{queue.code}'."}],
        )

