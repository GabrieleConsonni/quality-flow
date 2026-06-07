from api_client import api_get


def get_all_json_arrays() -> list[dict]:
    result = api_get("/data-source/json-array")
    return result if isinstance(result, list) else []


def get_all_database_datasources() -> list[dict]:
    result = api_get("/data-source/database")
    return result if isinstance(result, list) else []


def get_all_brokers() -> list[dict]:
    result = api_get("/broker/connection")
    return result if isinstance(result, list) else []


def get_queues_by_broker_id(broker_id: str) -> list[dict]:
    broker_id_value = str(broker_id or "").strip()
    if not broker_id_value:
        return []
    result = api_get(f"/broker/{broker_id_value}/queue")
    return result if isinstance(result, list) else []
