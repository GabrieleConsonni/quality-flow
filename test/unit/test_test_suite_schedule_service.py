from datetime import datetime, timedelta

from app.elaborations.services.alembic.test_suite_schedule_service import compute_next_run_at


def test_compute_next_run_at_uses_interval_from_now():
    now = datetime(2026, 3, 16, 10, 0, 0)

    next_run_at = compute_next_run_at(
        active=True,
        frequency_unit="minutes",
        frequency_value=15,
        now=now,
    )

    assert next_run_at == now + timedelta(minutes=15)


def test_compute_next_run_at_uses_future_start_at_as_first_run():
    now = datetime(2026, 3, 16, 10, 0, 0)
    start_at = datetime(2026, 3, 16, 12, 0, 0)

    next_run_at = compute_next_run_at(
        active=True,
        frequency_unit="hours",
        frequency_value=1,
        start_at=start_at,
        now=now,
    )

    assert next_run_at == start_at


def test_compute_next_run_at_returns_none_when_inactive_or_past_end():
    now = datetime(2026, 3, 16, 10, 0, 0)

    assert (
        compute_next_run_at(
            active=False,
            frequency_unit="days",
            frequency_value=1,
            now=now,
        )
        is None
    )
    assert (
        compute_next_run_at(
            active=True,
            frequency_unit="days",
            frequency_value=1,
            end_at=now + timedelta(hours=1),
            now=now,
            reference_time=now + timedelta(hours=2),
        )
        is None
    )
