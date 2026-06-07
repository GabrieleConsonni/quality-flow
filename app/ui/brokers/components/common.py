from datetime import datetime


BROKER_TYPE_OPTIONS = {
    "Elasticmq": "elasticmq",
    "Amazon": "amazon-sqs",
}
BROKER_TYPE_LABELS = {value: label for label, value in BROKER_TYPE_OPTIONS.items()}


def pick_broker_type_label(source_type: str | None) -> str:
    return BROKER_TYPE_LABELS.get(source_type or "", "Elasticmq")


def format_count(value):
    if isinstance(value, int):
        return str(value)
    return value if value is not None else "-"


def format_last_update(value):
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", ""))
        except ValueError:
            return value
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)

