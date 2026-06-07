import json
import time

from sqlalchemy.orm import Session

from _alembic.models.suite_test_entity import SuiteTestEntity
from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service_factory import QueueConnectionServiceFactory
from elaborations.models.dtos.configuration_test_dtos import DataFromQueueConfigurationTestDto
from elaborations.services.suite_tests.test_executor import TestExecutor
from logs.models.enums.log_level import LogLevel


class DataFromQueueTestExecutor(TestExecutor):

    def execute(
        self,
        session: Session,
        suite_test: SuiteTestEntity,
        cfg: DataFromQueueConfigurationTestDto,
    ) -> list[dict[str, str]]:
        test_code = str(suite_test.code or suite_test.id)
        queue = QueueService().get_by_id(session, cfg.queue_id)
        if not queue:
            raise ValueError(f"Queue '{cfg.queue_id}' not found")
        broker_connection:BrokerConnectionConfigTypes = load_broker_connection(queue.broker_id)

        service = QueueConnectionServiceFactory.get_service(broker_connection)

        retry = cfg.retry
        wait_time_seconds = cfg.wait_time_seconds
        max_messages = cfg.max_messages

        all_msgs = []

        while self.work_is_not_finished(all_msgs, max_messages, retry):
            remaining_messages = max_messages - len(all_msgs)
            if remaining_messages <= 0:
                break

            msgs = service.receive_messages(
                broker_connection,
                queue_id=cfg.queue_id,
                max_messages=remaining_messages,
            )

            if len(msgs) == 0:
                time.sleep(wait_time_seconds)
                retry -= 1
                continue

            all_msgs.extend(msgs)

        self.log(
            test_code,
            f"Try to export {len(all_msgs)} messages read from queue '{queue.code}'",
        )

        extracted_payload, error = self._extract_json_array_from_messages(all_msgs)

        return (
            self.execute_operations(
                session,
                suite_test.id,
                test_code,
                extracted_payload,
            )
            if not error
            else self._handle_error(suite_test, error)
        )
    
    def _extract_json_array_from_messages(self, messages: list[object]) -> tuple[list[object] | None, str | None]:
        extracted: list[object] = []
        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                return None, f"Messaggio {index + 1} non valido."

            # Accept both SQS-shaped messages (with Body) and already-decoded payloads.
            body_value = message.get("Body") if "Body" in message else message
            if isinstance(body_value, str):
                try:
                    body_value = json.loads(body_value)
                except json.JSONDecodeError as exc:
                    return None, f"Body non valido nel messaggio {index + 1}: {str(exc)}"
            extracted.append(body_value)
        return extracted, None
    
    def _handle_error(self, suite_test: SuiteTestEntity, error_message: str) -> list[dict[str, str]]:
        self.log(
            str(suite_test.code or suite_test.id),
            f"Error extracting messages: {error_message}",
            level=LogLevel.ERROR,
        )
        return [{"error": error_message}]

    @staticmethod
    def work_is_not_finished(all_msgs, max_messages, retry):
        right_size = len(all_msgs) < max_messages
        return  retry > 0 and right_size
