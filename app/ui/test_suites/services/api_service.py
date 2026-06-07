from datetime import datetime
from urllib.parse import quote_plus

from api_client import api_delete, api_get, api_post, api_put


def get_all_test_suites() -> list[dict]:
    result = api_get("/elaborations/test-suite")
    return result if isinstance(result, list) else []


def get_test_suite_by_id(test_suite_id: str) -> dict:
    return api_get(f"/elaborations/test-suite/{test_suite_id}")


def create_test_suite(payload: dict) -> dict:
    return api_post("/elaborations/test-suite", payload)


def update_test_suite(payload: dict) -> dict:
    return api_put("/elaborations/test-suite", payload)


def delete_test_suite_by_id(test_suite_id: str) -> dict:
    return api_delete(f"/elaborations/test-suite/{test_suite_id}")


def execute_test_suite_by_id(test_suite_id: str) -> dict:
    return api_get(f"/elaborations/test-suite/{test_suite_id}/execute")


def execute_test_by_id(test_suite_id: str, suite_item_id: str) -> dict:
    return api_post(
        f"/elaborations/test-suite/{test_suite_id}/test/{suite_item_id}/execute",
        {},
    )


def get_test_suite_executions(
    test_suite_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    limit_value = max(int(limit or 50), 1)
    suite_id = str(test_suite_id or "").strip()
    query_parts = [f"limit={limit_value}"]
    if suite_id:
        query_parts.append(f"test_suite_id={quote_plus(suite_id)}")
    result = api_get(f"/elaborations/test-suite-execution?{'&'.join(query_parts)}")
    return result if isinstance(result, list) else []


def search_test_suite_executions(
    *,
    test_suite_id: str | None = None,
    status: str | None = None,
    started_from: datetime | str | None = None,
    started_to: datetime | str | None = None,
    page_size: int = 20,
    page_number: int = 1,
) -> dict:
    page_size_value = min(max(int(page_size or 20), 1), 100)
    page_number_value = max(int(page_number or 1), 1)
    query_parts = [
        f"page_size={page_size_value}",
        f"page_number={page_number_value}",
    ]
    suite_id = str(test_suite_id or "").strip()
    if suite_id:
        query_parts.append(f"test_suite_id={quote_plus(suite_id)}")
    normalized_status = str(status or "").strip().lower()
    if normalized_status:
        query_parts.append(f"status={quote_plus(normalized_status)}")
    for key, raw_value in (("started_from", started_from), ("started_to", started_to)):
        if raw_value is None:
            continue
        value = raw_value.isoformat() if isinstance(raw_value, datetime) else str(raw_value).strip()
        if value:
            query_parts.append(f"{key}={quote_plus(value)}")
    result = api_get(f"/elaborations/test-suite-execution/search?{'&'.join(query_parts)}")
    return result if isinstance(result, dict) else {}


def delete_test_suite_execution_by_id(execution_id: str) -> dict:
    return api_delete(f"/elaborations/test-suite-execution/{execution_id}")


def preview_send_message_template_rows_via_api(
    *,
    input_data,
    source_type: str,
    for_each: object = None,
) -> list[dict]:
    result = api_post(
        "/elaborations/test-suite/send-message-template/preview",
        {
            "input_data": input_data,
            "source_type": source_type,
            "for_each": for_each,
        },
    )
    return result if isinstance(result, list) else []


def preview_suite_source_via_api(*, source: dict) -> dict:
    result = api_post(
        "/elaborations/test-suite/source/preview",
        {
            "source": source,
        },
    )
    return result if isinstance(result, dict) else {}
