from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.elaborations.api.test_suite_executions_api import router


def test_search_endpoint_rejects_page_size_greater_than_100():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/elaborations/test-suite-execution/search?page_size=101&page_number=1")

    assert response.status_code == 422
