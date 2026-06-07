"""Executor for the `receiveQueue` command (Phase 2 of the Test Suites refactor).

Receives up to `cfg.max_messages` messages from a queue, retrying up to
`cfg.retry` times waiting `cfg.wait_time_seconds` between empty polls. The
collected payloads are written to `cfg.target` (path inside the run context)
and returned as the `ExecutionResultDto.data` so downstream commands (typically
an assert) can consume them via `actualRef`.

Side-effect free at the protocol level: messages are received but NOT acked.
Whether the queue connector auto-acks on receive is broker-specific.
"""

from __future__ import annotations

import json
import time

from sqlalchemy.orm import Session

from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service_factory import (
    QueueConnectionServiceFactory,
)
from elaborations.models.dtos.configuration_command_dto import (
    ReceiveQueueConfigurationCommandDto,
)
from elaborations.services.operations.command_executor import (
    ExecutionResultDto,
    OperationExecutor,
)
from elaborations.services.suite_runs.run_context import write_context_path


class ReceiveQueueOperationExecutor(OperationExecutor):
    def execute(
        self,
        session: Session,
        operation_id: str,
        cfg: ReceiveQueueConfigurationCommandDto,
        data: list[dict],
    ) -> ExecutionResultDto:
        del data

        queue = QueueService().get_by_id(session, cfg.queue_id)
        if not queue:
            raise ValueError(f"Queue '{cfg.queue_id}' not found")
        broker_connection: BrokerConnectionConfigTypes = load_broker_connection(
            queue.broker_id
        )
        service = QueueConnectionServiceFactory.get_service(broker_connection)

        retries_remaining = max(cfg.retry, 0)
        collected: list[dict] = []
        while retries_remaining >= 0 and len(collected) < cfg.max_messages:
            remaining_slots = cfg.max_messages - len(collected)
            messages = service.receive_messages(
                broker_connection,
                queue_id=cfg.queue_id,
                max_messages=remaining_slots,
            )
            if messages:
                collected.extend(messages)
                continue
            if retries_remaining == 0:
                break
            time.sleep(cfg.wait_time_seconds)
            retries_remaining -= 1

        rows: list[dict] = []
        for index, message in enumerate(collected):
            if not isinstance(message, dict):
                raise ValueError(f"Message {index + 1} is not valid JSON.")
            body = message.get("Body") if "Body" in message else message
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid body in message {index + 1}: {str(exc)}"
                    ) from exc
            rows.append(body)

        if cfg.target:
            write_context_path(cfg.target, rows)

        message = f"Loaded {len(rows)} row(s) from queue '{queue.code}'."
        self.log(operation_id, message)
        return ExecutionResultDto(
            data=rows,
            result=[{"message": message}],
        )
