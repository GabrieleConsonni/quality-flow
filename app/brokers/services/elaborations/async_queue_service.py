from brokers.models.connections.broker_connection_config_types import BrokerConnectionConfigTypes
from brokers.services.alembic.broker_connection_service import load_broker_connection
from brokers.services.connections.queue.queue_connection_service_factory import QueueConnectionServiceFactory
from brokers.services.elaborations.queue_reader_thread import QueueReaderThread
from brokers.services.elaborations.queue_writer_thread import QueueWriterThread
from config.user_context_config import get_current_user_ctx

threads: dict[str, QueueReaderThread] = {}

class AsyncQueueService:
    @classmethod
    def start_receiving_messages(cls, broker_id: str, queue_id: str)->dict:
        connection_config: BrokerConnectionConfigTypes = load_broker_connection(broker_id)
        service = QueueConnectionServiceFactory.get_service(connection_config)
        tenant_id = get_current_user_ctx().tenant_id
        thread = QueueReaderThread(queue_id, service, connection_config, tenant_id)
        if broker_id in threads:
            existing_thread = threads[broker_id]
            if existing_thread.is_alive():
                return {"status":"already_running"}
        threads[queue_id]=thread
        thread.start()
        return {"status":"started"}

    @classmethod
    def stop_receiving_messages(cls, queue_id:str)->dict:
        if queue_id in threads:
            thread = threads[queue_id]
            if thread.is_alive():
                thread.stop()
                thread.join()
            del threads[queue_id]
        return {"status":"stopped"}

    @classmethod
    def publish_from_table(cls, broker_id:str, queue_id:str, export_table_name:str)->dict:
        connection_config: BrokerConnectionConfigTypes = load_broker_connection(broker_id)
        service = QueueConnectionServiceFactory.get_service(connection_config)
        tenant_id = get_current_user_ctx().tenant_id
        thread = QueueWriterThread(export_table_name,queue_id, service, connection_config, tenant_id)
        thread.start()
        return {"status":"started"}



