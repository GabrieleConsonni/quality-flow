from __future__ import annotations

from datetime import date, datetime, time
from urllib.parse import urlencode


HOME_FILTER_STATUS_KEY = "home_execution_status"
HOME_FILTER_TEST_SUITE_KEY = "home_execution_test_suite_id"
HOME_FILTER_STARTED_FROM_ENABLED_KEY = "home_execution_started_from_enabled"
HOME_FILTER_STARTED_FROM_DATE_KEY = "home_execution_started_from_date"
HOME_FILTER_STARTED_FROM_TIME_KEY = "home_execution_started_from_time"
HOME_FILTER_STARTED_TO_ENABLED_KEY = "home_execution_started_to_enabled"
HOME_FILTER_STARTED_TO_DATE_KEY = "home_execution_started_to_date"
HOME_FILTER_STARTED_TO_TIME_KEY = "home_execution_started_to_time"
HOME_PAGE_SIZE_KEY = "home_execution_page_size"
HOME_PAGE_NUMBER_KEY = "home_execution_page_number"
HOME_FILTER_SIGNATURE_KEY = "home_execution_filter_signature"
HOME_TOTAL_PAGES_KEY = "home_execution_total_pages"
TEST_SUITES_URL_PATH = "test-suites"

STATUS_LABELS = {
    "success": "OK",
    "running": "In corso",
    "error": "KO",
}


def ensure_home_state(session_state: dict):
    today = date.today()
    session_state.setdefault(HOME_FILTER_STATUS_KEY, "")
    session_state.setdefault(HOME_FILTER_TEST_SUITE_KEY, "")
    session_state.setdefault(HOME_FILTER_STARTED_FROM_ENABLED_KEY, False)
    session_state.setdefault(HOME_FILTER_STARTED_FROM_DATE_KEY, today)
    session_state.setdefault(HOME_FILTER_STARTED_FROM_TIME_KEY, time(hour=0, minute=0))
    session_state.setdefault(HOME_FILTER_STARTED_TO_ENABLED_KEY, False)
    session_state.setdefault(HOME_FILTER_STARTED_TO_DATE_KEY, today)
    session_state.setdefault(HOME_FILTER_STARTED_TO_TIME_KEY, time(hour=23, minute=59))
    session_state.setdefault(HOME_PAGE_SIZE_KEY, 50)
    session_state.setdefault(HOME_PAGE_NUMBER_KEY, 1)
    session_state.setdefault(HOME_FILTER_SIGNATURE_KEY, "")
    session_state.setdefault(HOME_TOTAL_PAGES_KEY, 1)


def combine_datetime(
    *,
    enabled: bool,
    selected_date: date | None,
    selected_time: time | None,
) -> datetime | None:
    if not enabled or selected_date is None or selected_time is None:
        return None
    return datetime.combine(selected_date, selected_time)


def read_home_filters(session_state: dict) -> dict:
    started_from = combine_datetime(
        enabled=bool(session_state.get(HOME_FILTER_STARTED_FROM_ENABLED_KEY)),
        selected_date=session_state.get(HOME_FILTER_STARTED_FROM_DATE_KEY),
        selected_time=session_state.get(HOME_FILTER_STARTED_FROM_TIME_KEY),
    )
    started_to = combine_datetime(
        enabled=bool(session_state.get(HOME_FILTER_STARTED_TO_ENABLED_KEY)),
        selected_date=session_state.get(HOME_FILTER_STARTED_TO_DATE_KEY),
        selected_time=session_state.get(HOME_FILTER_STARTED_TO_TIME_KEY),
    )
    return {
        "status": str(session_state.get(HOME_FILTER_STATUS_KEY) or "").strip().lower(),
        "test_suite_id": str(session_state.get(HOME_FILTER_TEST_SUITE_KEY) or "").strip(),
        "started_from": started_from,
        "started_to": started_to,
        "page_size": min(max(int(session_state.get(HOME_PAGE_SIZE_KEY) or 20), 1), 100),
        "page_number": max(int(session_state.get(HOME_PAGE_NUMBER_KEY) or 1), 1),
    }


def build_filter_signature(filters: dict) -> str:
    return "|".join(
        [
            str(filters.get("status") or ""),
            str(filters.get("test_suite_id") or ""),
            filters.get("started_from").isoformat() if isinstance(filters.get("started_from"), datetime) else "",
            filters.get("started_to").isoformat() if isinstance(filters.get("started_to"), datetime) else "",
            str(min(max(int(filters.get("page_size") or 20), 1), 100)),
        ]
    )


def reset_page_number_on_filter_change(session_state: dict, filters: dict):
    signature = build_filter_signature(filters)
    if session_state.get(HOME_FILTER_SIGNATURE_KEY) != signature:
        session_state[HOME_PAGE_NUMBER_KEY] = 1
        session_state[HOME_FILTER_SIGNATURE_KEY] = signature


def normalize_search_result(payload: dict | None) -> dict:
    data = payload if isinstance(payload, dict) else {}
    items = data.get("items")
    total = int(data.get("total") or 0)
    page_size = min(max(int(data.get("page_size") or 20), 1), 100)
    total_pages = max(int(data.get("total_pages") or 1), 1)
    page_number = min(max(int(data.get("page_number") or 1), 1), total_pages)
    return {
        "items": items if isinstance(items, list) else [],
        "total": total,
        "page_size": page_size,
        "page_number": page_number,
        "total_pages": total_pages,
    }


def format_execution_datetime(value: object) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    text = str(value or "").strip()
    if not text:
        return "-"
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return text.replace("T", " ")
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def format_status_label(status: object) -> str:
    normalized = str(status or "").strip().lower()
    return STATUS_LABELS.get(normalized, normalized or "-")


def parse_execution_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def resolve_execution_chart_name(execution: dict | None) -> str:
    if not isinstance(execution, dict):
        return "-"

    explicit_name = str(execution.get("help") or execution.get("item_description") or "").strip()
    if explicit_name:
        return explicit_name

    requested_test_id = str(execution.get("requested_test_id") or "").strip()
    items = execution.get("items") or []
    if requested_test_id and isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            if str(item.get("suite_item_id") or "").strip() != requested_test_id:
                continue
            item_name = str(
                item.get("help")
                or item.get("item_description")
                or item.get("description")
                or ""
            ).strip()
            if item_name:
                return item_name

    return str(
        execution.get("test_suite_description")
        or execution.get("test_suite_id")
        or execution.get("id")
        or "-"
    ).strip() or "-"


def _resolve_reference_datetime(started_at: datetime) -> datetime:
    if started_at.tzinfo is not None:
        return datetime.now(started_at.tzinfo)
    return datetime.now()


def compute_execution_duration_seconds(
    execution: dict | None,
    *,
    reference_time: datetime | None = None,
) -> float:
    if not isinstance(execution, dict):
        return 0.0

    started_at = parse_execution_datetime(execution.get("started_at"))
    if started_at is None:
        return 0.0

    finished_at = parse_execution_datetime(execution.get("finished_at"))
    status = str(execution.get("status") or "").strip().lower()
    if finished_at is None and status == "running":
        finished_at = reference_time or _resolve_reference_datetime(started_at)
    if finished_at is None:
        return 0.0

    return max((finished_at - started_at).total_seconds(), 0.0)


def format_duration_label(duration_seconds: float) -> str:
    total_seconds = max(int(round(duration_seconds)), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def build_chart_rows(executions: list[dict]) -> list[dict]:
    rows: list[dict] = []
    reference_time = datetime.now()
    for execution in executions if isinstance(executions, list) else []:
        started_at = execution.get("started_at")
        started_at_value = parse_execution_datetime(started_at)
        if started_at_value is None:
            continue
        duration_seconds = compute_execution_duration_seconds(execution, reference_time=reference_time)
        rows.append(
            {
                "test_name": resolve_execution_chart_name(execution),
                "status": str(execution.get("status") or "").strip().lower() or "-",
                "duration_seconds": duration_seconds,
                "duration_label": format_duration_label(duration_seconds),
                "started_at": started_at,
                "started_at_label": format_execution_datetime(started_at),
                "started_at_sort": started_at_value.isoformat(),
                "finished_at": execution.get("finished_at"),
                "error_message": str(execution.get("error_message") or "").strip() or "-",
            }
        )
    return rows


def resolve_execution_test_position(execution: dict | None) -> int | None:
    if not isinstance(execution, dict):
        return None
    requested_test_id = str(execution.get("requested_test_id") or "").strip()
    if not requested_test_id:
        return None
    items = execution.get("items") or []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        if str(item.get("suite_item_id") or "").strip() != requested_test_id:
            continue
        try:
            position = int(item.get("position") or 0)
        except (TypeError, ValueError):
            return None
        return position if position > 0 else None
    return None


def build_test_suites_link(
    execution: dict | None,
    *,
    target_path: str = TEST_SUITES_URL_PATH,
) -> str:
    if not isinstance(execution, dict):
        return ""
    suite_id = str(execution.get("test_suite_id") or "").strip()
    if not suite_id:
        return ""
    query_params: dict[str, str | int] = {"suite_id": suite_id}
    test_position = resolve_execution_test_position(execution)
    if test_position:
        query_params["test_position"] = test_position
    encoded_params = urlencode(query_params)
    return f"{target_path}?{encoded_params}" if encoded_params else target_path


def build_table_rows(executions: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for execution in executions if isinstance(executions, list) else []:
        rows.append(
            {
                "Suite": str(
                    execution.get("test_suite_description")
                    or execution.get("test_suite_id")
                    or "-"
                ),
                "Start at": format_execution_datetime(execution.get("started_at")),
                "Finish at": format_execution_datetime(execution.get("finished_at")),
                "Status": format_status_label(execution.get("status")),
                "Error message": str(execution.get("error_message") or "-"),
                "Open suite": build_test_suites_link(execution),
            }
        )
    return rows
