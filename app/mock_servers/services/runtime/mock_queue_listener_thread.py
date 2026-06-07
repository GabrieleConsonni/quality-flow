import json
import threading
import time
from uuid import uuid4

from _alembic.models.mock_server_invocation_entity import MockServerInvocationEntity
from _alembic.services.session_context_manager import managed_session
from brokers.models.connections.broker_connection_config_types import (
    BrokerConnectionConfigTypes,
)
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service_factory import (
    QueueConnectionServiceFactory,
)
from elaborations.services.suite_runs.run_context import create_run_context
from logs.models.enums.log_level import LogLevel
from mock_servers.models.runtime_models import MockQueueBinding
from mock_servers.services.alembic.mock_server_invocation_service import (
    MockServerInvocationService,
)
from mock_servers.services.runtime.mock_event_envelope import build_queue_event_envelope
from mock_servers.services.runtime.mock_runtime_logger import log_mock_server_event
from mock_servers.services.runtime.mock_trigger_executor import execute_mock_operations


def _extract_payload_from_messages(messages: list[dict]) -> list[dict]:
    payload: list[dict] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        body_value = message.get("Body")
        if isinstance(body_value, str):
            try:
                body_value = json.loads(body_value)
            except json.JSONDecodeError:
                body_value = {"raw_body": body_value}
        if isinstance(body_value, dict):
            payload.append(body_value)
        elif isinstance(body_value, list):
            dict_items = [item for item in body_value if isinstance(item, dict)]
            if dict_items:
                payload.extend(dict_items)
        elif body_value is not None:
            payload.append({"value": body_value})
    return payload


class MockQueueListenerThread(threading.Thread):
    def __init__(
        self,
        mock_server_id: str,
        queue_binding: MockQueueBinding,
        tenant_id: str = None,
    ):
        super().__init__(
            name=f"mock-queue-{mock_server_id}-{queue_binding.queue_id}",
            daemon=True,
        )
        self._stop_event = threading.Event()
        self.mock_server_id = mock_server_id
        self.queue_binding = queue_binding
        self.tenant_id = tenant_id

        with managed_session(tenant_id) as session:
            queue = QueueService().get_by_id(session, queue_binding.queue_id)
            if not queue:
                raise ValueError(f"Queue '{queue_binding.queue_id}' not found.")
            self.broker_connection: BrokerConnectionConfigTypes = load_broker_connection(
                queue.broker_id
            )
        self.queue_service = QueueConnectionServiceFactory.get_service(self.broker_connection)

    def stop(self):
        self._stop_event.set()

    def run(self):
        queue_id = self.queue_binding.queue_id
        poll_seconds = max(int(self.queue_binding.polling_interval_seconds or 1), 1)
        max_messages = max(min(int(self.queue_binding.max_messages or 10), 10), 1)
        while not self._stop_event.is_set():
            messages = []
            try:
                messages = self.queue_service.receive_messages(
                    self.broker_connection,
                    queue_id=queue_id,
                    max_messages=max_messages,
                )
            except Exception as exc:
                log_mock_server_event(
                    self.mock_server_id,
                    f"Queue listener error for queue '{queue_id}': {str(exc)}",
                    level=LogLevel.ERROR,
                )
                time.sleep(poll_seconds)
                continue

            if not messages:
                time.sleep(poll_seconds)
                continue

            trigger_id = str(uuid4())
            payload = _extract_payload_from_messages(messages)
            event = build_queue_event_envelope(
                mock_server_id=self.mock_server_id,
                queue_id=self.queue_binding.queue_id,
                queue_code=queue_id,
                payload=payload,
                messages=messages,
            )
            with managed_session(self.tenant_id) as session:
                invocation_id = MockServerInvocationService().insert(
                    session,
                    MockServerInvocationEntity(
                        mock_server_id=self.mock_server_id,
                        trigger_type="queue",
                        event_json=event,
                    ),
                )
            execute_mock_operations(
                mock_server_id=self.mock_server_id,
                trigger_id=trigger_id,
                source_type="queue",
                source_ref=self.queue_binding.id,
                operations=self.queue_binding.commands,
                data=payload,
                run_context=create_run_context(
                    run_id=invocation_id,
                    event=event,
                    initial_vars={},
                    invocation_id=invocation_id,
                ),
                tenant_id=self.tenant_id,
            )

            try:
                # QSM-031 requirement: ACK always, even when operations fail.
                self.queue_service.ack_messages(
                    self.broker_connection,
                    queue_id=queue_id,
                    messages=messages,
                )
            except Exception as exc:
                log_mock_server_event(
                    self.mock_server_id,
                    f"Queue ACK error for queue '{queue_id}': {str(exc)}",
                    level=LogLevel.ERROR,
                    payload={"trigger_id": trigger_id, "invocation_id": invocation_id},
                )
