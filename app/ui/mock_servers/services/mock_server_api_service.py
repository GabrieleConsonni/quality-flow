from api_client import api_delete, api_get, api_post, api_put


def get_all_mock_servers() -> list[dict]:
    result = api_get("/mock-server")
    return result if isinstance(result, list) else []


def get_mock_server_by_id(mock_server_id: str) -> dict:
    return api_get(f"/mock-server/{mock_server_id}")


def create_mock_server(payload: dict) -> dict:
    return api_post("/mock-server", payload)


def update_mock_server(payload: dict) -> dict:
    return api_put("/mock-server", payload)


def delete_mock_server(mock_server_id: str) -> dict:
    return api_delete(f"/mock-server/{mock_server_id}")


def activate_mock_server(mock_server_id: str) -> dict:
    return api_post(f"/mock-server/{mock_server_id}/activate", {})


def deactivate_mock_server(mock_server_id: str) -> dict:
    return api_post(f"/mock-server/{mock_server_id}/deactivate", {})
