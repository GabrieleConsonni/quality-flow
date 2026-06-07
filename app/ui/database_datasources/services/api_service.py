from api_client import api_delete, api_post, api_put


def create_database_datasource(payload: dict) -> dict:
    result = api_post("/data-source/database", payload)
    return result if isinstance(result, dict) else {}


def update_database_datasource(payload: dict) -> dict:
    result = api_put("/data-source/database", payload)
    return result if isinstance(result, dict) else {}


def delete_database_datasource_by_id(datasource_id: str) -> dict:
    result = api_delete(f"/data-source/database/{datasource_id}")
    return result if isinstance(result, dict) else {}
