from datetime import date, datetime, time

from ui.home.services import home_service


def test_reset_page_number_on_filter_change_resets_only_when_signature_changes():
    session_state = {
        home_service.HOME_PAGE_NUMBER_KEY: 4,
        home_service.HOME_FILTER_SIGNATURE_KEY: "",
    }
    filters = {
        "status": "success",
        "test_suite_id": "suite-1",
        "started_from": datetime(2026, 3, 20, 8, 0, 0),
        "started_to": None,
        "page_size": 50,
    }

    home_service.reset_page_number_on_filter_change(session_state, filters)

    assert session_state[home_service.HOME_PAGE_NUMBER_KEY] == 1
    signature = session_state[home_service.HOME_FILTER_SIGNATURE_KEY]

    session_state[home_service.HOME_PAGE_NUMBER_KEY] = 3
    home_service.reset_page_number_on_filter_change(session_state, filters)

    assert session_state[home_service.HOME_PAGE_NUMBER_KEY] == 3
    assert session_state[home_service.HOME_FILTER_SIGNATURE_KEY] == signature


def test_read_home_filters_combines_date_and_time_and_clamps_paging():
    session_state = {}
    home_service.ensure_home_state(session_state)
    session_state.update(
        {
            home_service.HOME_FILTER_STATUS_KEY: "running",
            home_service.HOME_FILTER_TEST_SUITE_KEY: "suite-42",
            home_service.HOME_FILTER_STARTED_FROM_ENABLED_KEY: True,
            home_service.HOME_FILTER_STARTED_FROM_DATE_KEY: date(2026, 3, 21),
            home_service.HOME_FILTER_STARTED_FROM_TIME_KEY: time(9, 30),
            home_service.HOME_FILTER_STARTED_TO_ENABLED_KEY: True,
            home_service.HOME_FILTER_STARTED_TO_DATE_KEY: date(2026, 3, 21),
            home_service.HOME_FILTER_STARTED_TO_TIME_KEY: time(18, 15),
            home_service.HOME_PAGE_SIZE_KEY: 999,
            home_service.HOME_PAGE_NUMBER_KEY: 0,
        }
    )

    filters = home_service.read_home_filters(session_state)

    assert filters == {
        "status": "running",
        "test_suite_id": "suite-42",
        "started_from": datetime(2026, 3, 21, 9, 30),
        "started_to": datetime(2026, 3, 21, 18, 15),
        "page_size": 100,
        "page_number": 1,
    }


def test_build_chart_rows_and_formatters_keep_suite_view():
    rows = home_service.build_chart_rows(
        [
            {
                "id": "exec-1",
                "test_suite_description": "Suite One",
                "test_suite_id": "suite-1",
                "status": "success",
                "started_at": "2026-03-21T10:15:00",
                "finished_at": "2026-03-21T10:20:00",
                "error_message": "",
                "requested_test_id": "test-1",
                "items": [
                    {
                        "suite_item_id": "test-1",
                        "item_description": "Smoke test",
                    }
                ],
            }
        ]
    )

    assert rows == [
        {
            "test_name": "Smoke test",
            "status": "success",
            "duration_seconds": 300.0,
            "duration_label": "5m 0s",
            "started_at": "2026-03-21T10:15:00",
            "started_at_label": "2026-03-21 10:15:00",
            "started_at_sort": "2026-03-21T10:15:00",
            "finished_at": "2026-03-21T10:20:00",
            "error_message": "-",
        }
    ]
    assert home_service.format_execution_datetime("2026-03-21T10:15:00") == "2026-03-21 10:15:00"
    assert home_service.format_status_label("error") == "KO"


def test_compute_execution_duration_seconds_uses_reference_time_for_running():
    duration_seconds = home_service.compute_execution_duration_seconds(
        {
            "status": "running",
            "started_at": "2026-03-21T10:15:00",
            "finished_at": None,
        },
        reference_time=datetime(2026, 3, 21, 10, 17, 30),
    )

    assert duration_seconds == 150.0
    assert home_service.format_duration_label(duration_seconds) == "2m 30s"


def test_build_table_rows_exposes_real_table_shape_and_internal_link():
    rows = home_service.build_table_rows(
        [
            {
                "id": "exec-1",
                "test_suite_id": "suite-1",
                "test_suite_description": "Suite One",
                "status": "success",
                "started_at": "2026-03-21T10:15:00",
                "finished_at": "2026-03-21T10:20:00",
                "error_message": "",
                "requested_test_id": "test-1",
                "items": [
                    {
                        "suite_item_id": "test-1",
                        "position": 3,
                    }
                ],
            }
        ]
    )

    assert rows == [
        {
            "Suite": "Suite One",
            "Start at": "2026-03-21 10:15:00",
            "Finish at": "2026-03-21 10:20:00",
            "Status": "OK",
            "Error message": "-",
            "Open suite": "test-suites?suite_id=suite-1&test_position=3",
        }
    ]


def test_normalize_search_result_clamps_page_number_and_defaults_items():
    result = home_service.normalize_search_result(
        {
            "items": None,
            "total": 5,
            "page_size": 120,
            "page_number": 7,
            "total_pages": 3,
        }
    )

    assert result == {
        "items": [],
        "total": 5,
        "page_size": 100,
        "page_number": 3,
        "total_pages": 3,
    }
