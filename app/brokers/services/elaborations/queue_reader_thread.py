import json
import threading
import time
import uuid

from sqlalchemy import create_engine, Table

from _alembic.services.session_context_manager import managed_session
from brokers.models.dto.configurations.queue_configuration_types import convert_queue_configuration_types
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service import QueueConnectionService
from logs.models.dtos.log_dto import LogDto
from logs.models.enums.log_level import LogLevel
from logs.models.enums.log_subject_type import LogSubjectType
from logs.services.alembic.log_service import LogService
from services.multitenant.multitenant_service import get_tenant, url_from_tenant
from sqlalchemy_utils.database_table_writer import DatabaseTableWriter


MAX_RETRY_ATTEMPTS = 5


class QueueReaderThread(threading.Thread):

    def __init__(self, queue_id: str, service: QueueConnectionService, connection_config, tenant_id: str):
        super().__init__(name=f"queue_reader-{queue_id}", daemon=True)
        self._stop_event = threading.Event()
        self.service = service
        self.queue_id = queue_id
        self.connection_config = connection_config
        self.tenant_id = tenant_id
        self.round_counter = 0
        with managed_session(tenant_id) as session:
            queue_entity = QueueService().get_by_id(session, queue_id)
            self.code = queue_entity.code
            cfg = convert_queue_configuration_types(queue_entity.configuration_json)
            self.receiveMessageWait = cfg.receiveMessageWait if cfg.receiveMessageWait else 20

    def loop(self):
        batch = []
        sqs, queue_url = self.service.test_connection(self.connection_config, queue_id=self.queue_id)

        tenant = get_tenant(self.tenant_id)
        engine = create_engine(url_from_tenant(tenant))
        sample_row = {"id": "sample", "body": {}}
        table_name = f"{self.code}_export".replace("-","_").replace(".","_").lower()
        export_table:Table = DatabaseTableWriter.ensure_table_exists(engine,table_name , sample_row)

        retry_counter = 0

        while not self._stop_event.is_set():
            try:
                msgs = self.service.receive_messages(self.connection_config, queue_id=self.queue_id)

                if not msgs or len(msgs) == 0:
                    retry_counter += 1

                    if len(batch) > 0:
                        self.save_body_messages(engine, export_table, batch)
                        self.service.change_message_visibility(sqs, queue_url, batch, 300)  # 5 minutes
                        batch = []

                    if retry_counter >= MAX_RETRY_ATTEMPTS:
                        self.log(f"No messages received from queue {self.code} after {MAX_RETRY_ATTEMPTS} attempts. Stopping reader thread.",LogLevel.WARNING)
                        break

                    time.sleep(self.receiveMessageWait)
                    continue

                batch.extend(msgs)

                self.round_counter += 1

                self.log(f"{len(msgs)} Messages received from queue {self.code} in round {str(self.round_counter)}",LogLevel.INFO)

            except Exception as e:
                self.log(f"Error in queue reader thread for queue {self.code}: {str(e)}",LogLevel.ERROR)


    def log(self, message:str, level: LogLevel):
        log_dto = LogDto(
            subject_type=LogSubjectType.SERVICE,
            subject=self.name,
            message=message,
            level=level
        )
        LogService().log(log_dto, self.tenant_id)


    def save_body_messages(self,engine, export_table, msgs):
        rows=[]
        for m in msgs:
            body = m["Body"]
            if isinstance(body, str):
                body = json.loads(body)
            if isinstance(body, list):
                bodies = []
                for b in body:
                    bodies.append(b)
                body=bodies
            rows.append({
                "id": str(uuid.uuid4()),
                "body": body,
                "date_created": time.strftime('%Y-%m-%d %H:%M:%S')
            })
        DatabaseTableWriter.insert_rows(engine, export_table, rows)


    def run(self):
        self.loop()


    def stop(self):
        self._stop_event.set()
        log_dto = LogDto(
            subject_type=LogSubjectType.SERVICE,
            subject=self.name,
            message=f"Queue reader thread for queue {self.code} is stopping.",
            level=LogLevel.INFO
        )
        LogService().log(log_dto, self.tenant_id)
