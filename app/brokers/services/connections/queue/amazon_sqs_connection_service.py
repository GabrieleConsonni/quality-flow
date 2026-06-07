import json
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from _alembic.models.queue_entity import QueueEntity
from _alembic.services.session_context_manager import managed_session
from brokers.models.connections.amazon.broker_amazon_connection_config import BrokerAmazonConnectionConfig
from brokers.models.dto.configurations.queue_configuration_dto import QueueConfigurationDto
from brokers.models.dto.configurations.queue_configuration_types import convert_queue_configuration_types
from brokers.services.alembic.queue_service import QueueService
from brokers.services.connections.queue.queue_connection_service import QueueConnectionService, LONG_VISIBILITY_TIMEOUT
from exceptions.app_exception import QualityFlowAppException

MAX_NUMBER_OF_MESSAGES = 10
MAX_WAIT_TIME_SECONDS = 20
DEFAULT_WAIT_TIME_SECONDS = 0


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _timestamp_to_iso(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

class AmazonSQSConnectionService(QueueConnectionService):

    def _client(self, config: BrokerAmazonConnectionConfig)->BaseClient:
        return boto3.client(
            "sqs",
            region_name=config.region,
            endpoint_url=config.endpointUrl,
            aws_access_key_id=config.accessKeyId,
            aws_secret_access_key=config.secretsAccessKey,
        )
    def _extract_url_from_queue(self,queue_cfg_dto:QueueConfigurationDto) -> str:
        if not queue_cfg_dto:
            raise Exception(f"Queue {queue_cfg_dto} not found")
        return queue_cfg_dto.url

    def _load_queue_configuration(self, queue_id: str) -> QueueConfigurationDto:
        with managed_session() as session:
            queue: QueueEntity | None = QueueService().get_by_id(session, queue_id)
            if queue is None:
                raise QualityFlowAppException(f"Queue with id '{queue_id}' not found")
            return convert_queue_configuration_types(queue.configuration_json)

    def _resolve_wait_time_seconds(self, queue_cfg: QueueConfigurationDto) -> int:
        raw_wait = queue_cfg.receiveMessageWait
        try:
            wait_seconds = int(raw_wait)
        except (TypeError, ValueError):
            return DEFAULT_WAIT_TIME_SECONDS
        return max(0, min(wait_seconds, MAX_WAIT_TIME_SECONDS))

    def test_connection(self, config:BrokerAmazonConnectionConfig, queue_id:str) -> tuple[BaseClient, str]:
        queue_cfg = self._load_queue_configuration(queue_id)
        queue_url = self._extract_url_from_queue(queue_cfg)
        sqs = self.test_url_connection(config, queue_url)

        return sqs, queue_url

    def test_url_connection(self, config, url):
        try:
            sqs = self._client(config)
            sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["All"])
        except ClientError as e:
            raise Exception(f"Error accessing SQS queue: {e}")
        return sqs

    def publish_messages(self, config:BrokerAmazonConnectionConfig, queue_id:str, messages:list[Any]) -> list[dict[str, Any]]:

        sqs,queue_url = self.test_connection(config,queue_id)

        results = []
        for msg in messages:

            try:
                if queue_url.endswith(".fifo"):
                    resp = sqs.send_message(
                        QueueUrl=queue_url,
                        MessageBody=json.dumps(msg),
                        MessageGroupId= "default"
                    )
                else:
                    resp = sqs.send_message(
                        QueueUrl=queue_url,
                        MessageBody=json.dumps(msg)
                    )

                mid = resp.get("MessageId")
                http_status = resp.get("ResponseMetadata", {}).get("HTTPStatusCode")

                results.append({"status": "ok", "message_id": mid, "http_status": http_status})

            except Exception as e:
                raise QualityFlowAppException(f"Error publishing message to SQS queue: {e}")

        return results

    def receive_messages(self, config:BrokerAmazonConnectionConfig, queue_id:str, max_messages: int = 10) -> list[Any]:
        queue_cfg = self._load_queue_configuration(queue_id)
        queue_url = self._extract_url_from_queue(queue_cfg)
        sqs = self.test_url_connection(config, queue_url)

        all_msgs = []

        to_receive = min(MAX_NUMBER_OF_MESSAGES, max_messages)
        wait_time_seconds = self._resolve_wait_time_seconds(queue_cfg)
        resp = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=to_receive,
            WaitTimeSeconds=wait_time_seconds,
        )

        msgs = resp.get("Messages", []) or []

        if not msgs:
            return all_msgs

        for m in msgs:
            self._change_message_visibility(sqs, queue_url, m)
            all_msgs.append(m)

        return all_msgs

    def change_message_visibility(self, sqs, queue_url:str, messages: list[Any], visibility_timeout:int=LONG_VISIBILITY_TIMEOUT):
        for m in messages:
            self._change_message_visibility(sqs,queue_url,m,visibility_timeout)

    def ack_messages(self, config:BrokerAmazonConnectionConfig, queue_id:str, messages: list[Any])-> list[dict]:

        sqs,queue_url = self.test_connection(config,queue_id)

        deleted_msgs:list[dict] = []
        failures: list[dict[str, str]] = []
        for index, m in enumerate(messages, start=1):
            if not isinstance(m, dict):
                failures.append(
                    {
                        "message_id": f"index-{index}",
                        "error": "Invalid message format.",
                    }
                )
                continue

            mid = str(m.get("MessageId") or f"index-{index}")
            receipt_handle = m.get("ReceiptHandle")
            if not receipt_handle:
                failures.append(
                    {
                        "message_id": mid,
                        "error": "Missing ReceiptHandle.",
                    }
                )
                continue

            try:
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
                deleted_msgs.append({
                    "status": "ok",
                    "message_id": mid
                })
            except ClientError as e:
                error_info = e.response.get("Error", {})
                error_code = str(error_info.get("Code") or "ClientError")
                error_message = str(error_info.get("Message") or str(e))
                failures.append(
                    {
                        "message_id": mid,
                        "error": f"{error_code}: {error_message}",
                    }
                )

        if failures:
            failed_ids = ", ".join(item["message_id"] for item in failures[:5])
            if len(failures) > 5:
                failed_ids = f"{failed_ids}, ..."
            raise QualityFlowAppException(
                f"ACK failed for {len(failures)} of {len(messages)} message(s). "
                f"Deleted={len(deleted_msgs)}. Failed IDs: {failed_ids}"
            )

        return deleted_msgs

    def get_queue_metrics(self, config: BrokerAmazonConnectionConfig, queue_id: str) -> dict[str, Any]:
        sqs, queue_url = self.test_connection(config, queue_id)
        resp = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=[
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
                "LastModifiedTimestamp",
            ],
        )
        attrs = resp.get("Attributes", {})
        return {
            "messages_sent": _safe_int(attrs.get("ApproximateNumberOfMessages")),
            "messages_received": _safe_int(attrs.get("ApproximateNumberOfMessagesNotVisible")),
            "last_update": _timestamp_to_iso(attrs.get("LastModifiedTimestamp")),
        }

    def _change_message_visibility(self, sqs, queue_url, m, visibility_timeout:int=LONG_VISIBILITY_TIMEOUT):
        try:
            sqs.change_message_visibility(
                QueueUrl=queue_url,
                ReceiptHandle=m['ReceiptHandle'],
                VisibilityTimeout=visibility_timeout
            )
        except ClientError as e:
            mid = m.get("MessageId", "unknown")
            raise QualityFlowAppException(f" Errore modifica visibilità messaggio  MessageId={mid} Error={e}")
