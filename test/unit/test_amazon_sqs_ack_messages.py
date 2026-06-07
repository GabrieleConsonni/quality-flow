from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.brokers.services.connections.queue.amazon_sqs_connection_service import (
    AmazonSQSConnectionService,
)
from app.brokers.models.dto.configurations.queue_configuration_dto import (
    QueueConfigurationDto,
)
from exceptions.app_exception import QualityFlowAppException


def test_ack_messages_returns_deleted_messages_when_all_delete_succeed(monkeypatch):
    service = AmazonSQSConnectionService()
    sqs = MagicMock()
    monkeypatch.setattr(service, "test_connection", lambda _config, _queue_id: (sqs, "queue-url"))
    messages = [
        {"MessageId": "m1", "ReceiptHandle": "rh1"},
        {"MessageId": "m2", "ReceiptHandle": "rh2"},
    ]

    result = service.ack_messages(None, "queue-id", messages)

    assert result == [
        {"status": "ok", "message_id": "m1"},
        {"status": "ok", "message_id": "m2"},
    ]
    assert sqs.delete_message.call_count == 2


def test_ack_messages_raises_on_partial_delete_failures(monkeypatch):
    service = AmazonSQSConnectionService()
    sqs = MagicMock()
    sqs.delete_message.side_effect = [
        None,
        ClientError(
            {
                "Error": {
                    "Code": "ReceiptHandleIsInvalid",
                    "Message": "The input receipt handle is invalid.",
                }
            },
            "DeleteMessage",
        ),
    ]
    monkeypatch.setattr(service, "test_connection", lambda _config, _queue_id: (sqs, "queue-url"))
    messages = [
        {"MessageId": "m1", "ReceiptHandle": "rh1"},
        {"MessageId": "m2", "ReceiptHandle": "rh2"},
    ]

    with pytest.raises(QualityFlowAppException) as exc_info:
        service.ack_messages(None, "queue-id", messages)

    error_message = str(exc_info.value)
    assert "ACK failed for 1 of 2 message(s)." in error_message
    assert "Deleted=1" in error_message
    assert "m2" in error_message


def test_receive_messages_uses_queue_receive_wait(monkeypatch):
    service = AmazonSQSConnectionService()
    sqs = MagicMock()
    sqs.receive_message.return_value = {"Messages": []}
    cfg = QueueConfigurationDto(
        sourceType="amazon-sqs",
        url="queue-url",
        receiveMessageWait=5,
    )
    monkeypatch.setattr(service, "_load_queue_configuration", lambda _queue_id: cfg)
    monkeypatch.setattr(service, "test_url_connection", lambda _config, _url: sqs)

    result = service.receive_messages(None, "queue-id", max_messages=3)

    assert result == []
    sqs.receive_message.assert_called_once_with(
        QueueUrl="queue-url",
        MaxNumberOfMessages=3,
        WaitTimeSeconds=5,
    )


def test_receive_messages_clamps_receive_wait_to_sqs_limits(monkeypatch):
    service = AmazonSQSConnectionService()
    sqs = MagicMock()
    sqs.receive_message.return_value = {"Messages": []}
    cfg = QueueConfigurationDto(
        sourceType="amazon-sqs",
        url="queue-url",
        receiveMessageWait=999,
    )
    monkeypatch.setattr(service, "_load_queue_configuration", lambda _queue_id: cfg)
    monkeypatch.setattr(service, "test_url_connection", lambda _config, _url: sqs)

    service.receive_messages(None, "queue-id", max_messages=20)

    sqs.receive_message.assert_called_once_with(
        QueueUrl="queue-url",
        MaxNumberOfMessages=10,
        WaitTimeSeconds=20,
    )


def test_receive_messages_clamps_negative_receive_wait_to_zero(monkeypatch):
    service = AmazonSQSConnectionService()
    sqs = MagicMock()
    sqs.receive_message.return_value = {"Messages": []}
    cfg = QueueConfigurationDto(
        sourceType="amazon-sqs",
        url="queue-url",
        receiveMessageWait=-3,
    )
    monkeypatch.setattr(service, "_load_queue_configuration", lambda _queue_id: cfg)
    monkeypatch.setattr(service, "test_url_connection", lambda _config, _url: sqs)

    service.receive_messages(None, "queue-id", max_messages=1)

    sqs.receive_message.assert_called_once_with(
        QueueUrl="queue-url",
        MaxNumberOfMessages=1,
        WaitTimeSeconds=0,
    )
