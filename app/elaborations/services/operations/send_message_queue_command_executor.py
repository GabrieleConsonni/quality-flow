

from sqlalchemy.orm import Session

from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service_factory import QueueConnectionServiceFactory
from elaborations.models.dtos.configuration_command_dto import (
    SendMessageQueueConfigurationCommandDto,
)
from elaborations.services.operations.command_data_resolver import (
    resolve_input_reference,
    write_result_constant,
)
from elaborations.services.operations.command_executor import OperationExecutor, ExecutionResultDto
from elaborations.services.operations.send_message_template_service import (
    build_send_message_payloads,
)
from json_utils.services.json_service import make_json_safe


class PublishToQueueOperationExecutor(OperationExecutor):
    def execute(self,session:Session,  operation_id:str, cfg: SendMessageQueueConfigurationCommandDto, data)->ExecutionResultDto:
        queue = QueueService().get_by_id(session,cfg.queue_id)
        if not queue:
            raise ValueError(f"Queue '{cfg.queue_id}' not found")
        connection_config: BrokerConnectionConfigTypes = load_broker_connection(queue.broker_id)
        service = QueueConnectionServiceFactory().get_service(connection_config)
        input_data, input_type = resolve_input_reference(session, cfg.inputRef, data)
        payload = build_send_message_payloads(
            input_data,
            source_type=input_type,
            message_template=cfg.message_template,
        )
        msg = [make_json_safe(item) for item in payload]
        service.publish_messages(connection_config, cfg.queue_id, msg)
        message=f"Published {len(payload)} message(s) to queue '{queue.code}'"
        result_payload = {
            "queue_id": cfg.queue_id,
            "queue_code": str(queue.code or ""),
            "published": len(payload),
            "renderedPayloads": msg,
        }
        if cfg.resultConstant:
            write_result_constant(session, cfg.resultConstant, result_payload)
        self.log(operation_id, message=message)
        return ExecutionResultDto(
            data=input_data,
            result=[{"message": message}]
        )



