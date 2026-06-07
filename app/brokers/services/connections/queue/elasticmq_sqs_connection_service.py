import os

import boto3
from botocore.client import BaseClient

from brokers.models.connections.elastiqmq.broker_elasticmq_connection_config import BrokerElasticmqConnectionConfig
from brokers.models.dto.configurations.queue_configuration_dto import QueueConfigurationDto
from brokers.services.connections.queue.amazon_sqs_connection_service import AmazonSQSConnectionService

DOCKER_HOST_IP = "host.docker.internal"

class ElasticmqSQSConnectionService(AmazonSQSConnectionService):

    def _client(self, config: BrokerElasticmqConnectionConfig)->BaseClient:
        return boto3.client(
            "sqs",
            region_name="region",
            endpoint_url=config.endpointUrl,
            aws_access_key_id="xxx",
            aws_secret_access_key="yyy",
        )

    def _extract_url_from_queue(self,queue_cfg_dto: QueueConfigurationDto) -> str:
        if not queue_cfg_dto:
            raise Exception(f"Queue {queue_cfg_dto} not found")

        if os.getenv("HOST_IP", DOCKER_HOST_IP) == DOCKER_HOST_IP:
            return queue_cfg_dto.url.replace("localhost", DOCKER_HOST_IP)
        else:
            return queue_cfg_dto.url
