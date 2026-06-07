from datetime import date, datetime, time

import streamlit as st

from api_client import api_delete, api_get, api_post, api_put
from test_suites.services.api_service import get_all_test_suites


SCHEDULES_STATE_KEY = "test_suite_schedules_data"
SCHEDULES_FILTER_KEY = "test_suite_schedules_filter_suite_id"
SCHEDULES_FEEDBACK_KEY = "test_suite_schedules_feedback"


def _parse_datetime(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        raw = value.rstrip("Z")
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return None


def _format_datetime(value) -> str:
    parsed = _parse_datetime(value)
    if not parsed:
        return "-"
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _format_frequency(schedule: dict) -> str:
    value = int(schedule.get("frequency_value") or 0)
    unit = str(schedule.get("frequency_unit") or "").strip()
    if value == 1 and unit.endswith("s"):
        unit = unit[:-1]
    return f"Every {value} {unit}".strip()


def _get_schedules(test_suite_id: str | None = None) -> list[dict]:
    suite_id = str(test_suite_id or "").strip()
    path = "/elaborations/test-suite-schedule"
    if suite_id:
        path = f"{path}?test_suite_id={suite_id}"
    result = api_get(path)
    return result if isinstance(result, list) else []


def _refresh_schedules():
    selected_suite_id = st.session_state.get(SCHEDULES_FILTER_KEY)
    st.session_state[SCHEDULES_STATE_KEY] = _get_schedules(selected_suite_id)


def _show_feedback():
    message = str(st.session_state.get(SCHEDULES_FEEDBACK_KEY) or "").strip()
    if message:
        st.success(message)
        st.session_state.pop(SCHEDULES_FEEDBACK_KEY, None)


def _combine_datetime_parts(input_date: date, input_time: time) -> datetime:
    return datetime.combine(input_date, input_time)


def _datetime_field(prefix: str, label: str, value) -> datetime | None:
    parsed = _parse_datetime(value) or datetime.now().replace(microsecond=0)
    enabled_key = f"{prefix}_{label}_enabled"
    date_key = f"{prefix}_{label}_date"
    time_key = f"{prefix}_{label}_time"

    default_enabled = _parse_datetime(value) is not None
    enabled = st.checkbox(f"{label}", value=default_enabled, key=enabled_key)
    if not enabled:
        return None

    selected_date = st.date_input(
        f"{label} date",
        value=parsed.date(),
        key=date_key,
    )
    selected_time = st.time_input(
        f"{label} time",
        value=parsed.time(),
        key=time_key,
    )
    return _combine_datetime_parts(selected_date, selected_time)


def _read_datetime_field(prefix: str, label: str) -> datetime | None:
    enabled = bool(st.session_state.get(f"{prefix}_{label}_enabled"))
    if not enabled:
        return None
    selected_date = st.session_state.get(f"{prefix}_{label}_date")
    selected_time = st.session_state.get(f"{prefix}_{label}_time")
    if not selected_date or not selected_time:
        return None
    return _combine_datetime_parts(selected_date, selected_time)


def _build_schedule_payload(prefix: str, *, schedule_id: str | None = None) -> dict | None:
    description = str(st.session_state.get(f"{prefix}_description") or "").strip()
    test_suite_id = str(st.session_state.get(f"{prefix}_test_suite_id") or "").strip()
    active = bool(st.session_state.get(f"{prefix}_active", True))
    frequency_value = int(st.session_state.get(f"{prefix}_frequency_value") or 0)
    frequency_unit = str(st.session_state.get(f"{prefix}_frequency_unit") or "").strip()
    start_at = _read_datetime_field(f"{prefix}_start", "Start at")
    end_at = _read_datetime_field(f"{prefix}_end", "End at")

    if not test_suite_id:
        st.error("Test suite is required.")
        return None
    if frequency_value <= 0:
        st.error("Frequency value must be greater than zero.")
        return None
    if start_at and end_at and start_at >= end_at:
        st.error("Start at must be earlier than End at.")
        return None

    payload = {
        "test_suite_id": test_suite_id,
        "description": description,
        "active": active,
        "frequency_unit": frequency_unit,
        "frequency_value": frequency_value,
        "start_at": start_at.isoformat() if start_at else None,
        "end_at": end_at.isoformat() if end_at else None,
    }
    if schedule_id:
        payload["id"] = schedule_id
    return payload


@st.dialog("New schedule", width="medium")
def _create_schedule_dialog(suites: list[dict]):
    prefix = "schedule_create"
    suite_options = {str(item.get("id")): str(item.get("description") or item.get("id")) for item in suites}
    suite_ids = list(suite_options.keys())

    st.text_input("Description", key=f"{prefix}_description")
    st.selectbox(
        "Test suite",
        options=suite_ids,
        format_func=lambda suite_id: suite_options.get(suite_id, suite_id),
        key=f"{prefix}_test_suite_id",
    )
    st.checkbox("Active", value=True, key=f"{prefix}_active")
    freq_cols = st.columns(2)
    with freq_cols[0]:
        st.number_input("Frequency value", min_value=1, value=5, key=f"{prefix}_frequency_value")
    with freq_cols[1]:
        st.selectbox(
            "Frequency unit",
            options=["minutes", "hours", "days"],
            key=f"{prefix}_frequency_unit",
        )
    if f"{prefix}_start_at_value" not in st.session_state:
        st.session_state[f"{prefix}_start_at_value"] = None
    if f"{prefix}_end_at_value" not in st.session_state:
        st.session_state[f"{prefix}_end_at_value"] = None
    _datetime_field(f"{prefix}_start", "Start at", None)
    _datetime_field(f"{prefix}_end", "End at", None)

    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button("Save", type="secondary", use_container_width=True, key=f"{prefix}_save"):
            payload = _build_schedule_payload(prefix)
            if not payload:
                return
            try:
                api_post("/elaborations/test-suite-schedule", payload)
            except Exception as exc:
                st.error(f"Error creating schedule: {str(exc)}")
                return
            _refresh_schedules()
            st.session_state[SCHEDULES_FEEDBACK_KEY] = "Schedule created."
            st.rerun()
    with action_cols[1]:
        if st.button("Cancel", use_container_width=True, key=f"{prefix}_cancel"):
            st.rerun()


@st.dialog("Edit schedule", width="medium")
def _edit_schedule_dialog(schedule: dict, suites: list[dict]):
    schedule_id = str(schedule.get("id") or "").strip()
    prefix = f"schedule_edit_{schedule_id}"
    suite_options = {str(item.get("id")): str(item.get("description") or item.get("id")) for item in suites}
    suite_ids = list(suite_options.keys())

    st.text_input(
        "Description",
        value=str(schedule.get("description") or ""),
        key=f"{prefix}_description",
    )
    st.selectbox(
        "Test suite",
        options=suite_ids,
        index=suite_ids.index(str(schedule.get("test_suite_id"))) if str(schedule.get("test_suite_id")) in suite_ids else 0,
        format_func=lambda suite_id: suite_options.get(suite_id, suite_id),
        key=f"{prefix}_test_suite_id",
    )
    st.checkbox("Active", value=bool(schedule.get("active")), key=f"{prefix}_active")
    freq_cols = st.columns(2)
    with freq_cols[0]:
        st.number_input(
            "Frequency value",
            min_value=1,
            value=int(schedule.get("frequency_value") or 1),
            key=f"{prefix}_frequency_value",
        )
    with freq_cols[1]:
        unit_options = ["minutes", "hours", "days"]
        current_unit = str(schedule.get("frequency_unit") or "minutes")
        st.selectbox(
            "Frequency unit",
            options=unit_options,
            index=unit_options.index(current_unit) if current_unit in unit_options else 0,
            key=f"{prefix}_frequency_unit",
        )
    if f"{prefix}_start_at_value" not in st.session_state:
        st.session_state[f"{prefix}_start_at_value"] = schedule.get("start_at")
    if f"{prefix}_end_at_value" not in st.session_state:
        st.session_state[f"{prefix}_end_at_value"] = schedule.get("end_at")
    _datetime_field(f"{prefix}_start", "Start at", schedule.get("start_at"))
    _datetime_field(f"{prefix}_end", "End at", schedule.get("end_at"))

    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button("Save", type="secondary", use_container_width=True, key=f"{prefix}_save"):
            payload = _build_schedule_payload(prefix, schedule_id=schedule_id)
            if not payload:
                return
            try:
                api_put("/elaborations/test-suite-schedule", payload)
            except Exception as exc:
                st.error(f"Error updating schedule: {str(exc)}")
                return
            _refresh_schedules()
            st.session_state[SCHEDULES_FEEDBACK_KEY] = "Schedule updated."
            st.rerun()
    with action_cols[1]:
        if st.button("Cancel", use_container_width=True, key=f"{prefix}_cancel"):
            st.rerun()


def _toggle_schedule(schedule_id: str, active: bool):
    endpoint = "deactivate" if active else "activate"
    api_post(f"/elaborations/test-suite-schedule/{schedule_id}/{endpoint}", {})
    _refresh_schedules()
    st.session_state[SCHEDULES_FEEDBACK_KEY] = "Schedule updated."


def _run_now(schedule_id: str):
    response = api_post(f"/elaborations/test-suite-schedule/{schedule_id}/run-now", {})
    status = str((response or {}).get("status") or "").strip() or "started"
    _refresh_schedules()
    st.session_state[SCHEDULES_FEEDBACK_KEY] = f"Run now completed with status: {status}."


def _delete_schedule(schedule_id: str):
    api_delete(f"/elaborations/test-suite-schedule/{schedule_id}")
    _refresh_schedules()
    st.session_state[SCHEDULES_FEEDBACK_KEY] = "Schedule deleted."


st.subheader("Test Suite Schedules")
st.caption("Configure recurring test suite executions on top of the existing suite runtime.")
st.divider()

suites = get_all_test_suites()

if SCHEDULES_FILTER_KEY not in st.session_state:
    st.session_state[SCHEDULES_FILTER_KEY] = ""
if SCHEDULES_STATE_KEY not in st.session_state:
    _refresh_schedules()

filter_options = [""] + [str(item.get("id")) for item in suites]
suite_labels = {str(item.get("id")): str(item.get("description") or item.get("id")) for item in suites}

toolbar = st.columns([4, 1, 1], vertical_alignment="center")
with toolbar[0]:
    selected_suite_id = st.selectbox(
        "",
        options=filter_options,
        index=filter_options.index(st.session_state.get(SCHEDULES_FILTER_KEY, "")) if st.session_state.get(SCHEDULES_FILTER_KEY, "") in filter_options else 0,
        format_func=lambda suite_id: "All test suites" if not suite_id else suite_labels.get(suite_id, suite_id),
        key=SCHEDULES_FILTER_KEY,
        label_visibility="collapsed",
    )
    if selected_suite_id != st.session_state.get("_last_schedule_filter"):
        st.session_state["_last_schedule_filter"] = selected_suite_id
        _refresh_schedules()
with toolbar[1]:
    if st.button("Refresh", use_container_width=True, icon=":material/refresh:"):
        _refresh_schedules()
with toolbar[2]:
    if st.button("New", type="secondary", use_container_width=True, icon=":material/add:"):
        if not suites:
            st.error("Create a test suite before adding schedules.")
        else:
            _create_schedule_dialog(suites)

schedules = st.session_state.get(SCHEDULES_STATE_KEY, [])
if not schedules:
    st.info("No schedules configured.")
    st.stop()

for schedule in schedules:
    schedule_id = str(schedule.get("id") or "").strip()
    suite_description = str(schedule.get("test_suite_description") or "").strip() or str(schedule.get("test_suite_id") or "")
    description = str(schedule.get("description") or "").strip() or "No description"
    status = str(schedule.get("last_status") or "idle").strip()
    active = bool(schedule.get("active"))

    with st.container(border=True):
        header_cols = st.columns([5, 2, 2, 2], vertical_alignment="center")
        with header_cols[0]:
            st.write(f"**{description}**")
            st.caption(f"{suite_description} | {_format_frequency(schedule)}")
        with header_cols[1]:
            st.caption("Next run")
            st.write(_format_datetime(schedule.get("next_run_at")))
        with header_cols[2]:
            st.caption("Last run")
            st.write(_format_datetime(schedule.get("last_run_at")))
        with header_cols[3]:
            st.caption("Status")
            st.write(f"{status} {'| active' if active else '| inactive'}")

        if schedule.get("last_error_message"):
            st.caption(str(schedule.get("last_error_message")))

        action_cols = st.columns([1, 1, 1, 1], vertical_alignment="center")
        with action_cols[0]:
            if st.button("Run now", key=f"run_now_{schedule_id}", use_container_width=True):
                try:
                    _run_now(schedule_id)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error starting schedule: {str(exc)}")
        with action_cols[1]:
            toggle_label = "Deactivate" if active else "Activate"
            if st.button(toggle_label, key=f"toggle_{schedule_id}", use_container_width=True):
                try:
                    _toggle_schedule(schedule_id, active)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error updating schedule: {str(exc)}")
        with action_cols[2]:
            if st.button("Edit", key=f"edit_{schedule_id}", use_container_width=True):
                _edit_schedule_dialog(schedule, suites)
        with action_cols[3]:
            if st.button("Delete", key=f"delete_{schedule_id}", use_container_width=True):
                try:
                    _delete_schedule(schedule_id)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error deleting schedule: {str(exc)}")

_show_feedback()
