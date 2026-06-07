from datetime import datetime

import streamlit as st

from api_client import api_delete, api_get


def _parse_dt(value):
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


def _matches(log, selected_levels, selected_types, subject_query, message_query, date_range):
    if selected_levels and log.get("level") not in selected_levels:
        return False
    if selected_types and log.get("subject_type") not in selected_types:
        return False
    if subject_query and subject_query.lower() not in str(log.get("subject", "")).lower():
        return False
    if message_query and message_query.lower() not in str(log.get("message", "")).lower():
        return False
    if date_range and len(date_range) == 2:
        log_dt = _parse_dt(log.get("created_at"))
        if log_dt is None:
            return False
        if not (date_range[0] <= log_dt.date() <= date_range[1]):
            return False
    return True


def _load_logs(show_error: bool = True) -> list[dict]:
    try:
        logs_data = api_get("/logs/")
        if isinstance(logs_data, list):
            st.session_state["logs"] = logs_data
        else:
            st.session_state["logs"] = []
    except Exception:
        st.session_state["logs"] = []
        if show_error:
            st.error("Errore caricamento logs")
    return st.session_state.get("logs", [])


st.header("Logs")
st.caption("Visualizzazione e pulizia dei log applicativi.")

if "logs" not in st.session_state:
    _load_logs(show_error=False)

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Ricarica Logs"):
        _load_logs(show_error=True)
with col2:
    days = st.number_input("Cancella log piu vecchi di (giorni)", min_value=1, value=30)
    if st.button("Pulisci Logs"):
        try:
            api_delete(f"/logs/{int(days)}")
            _load_logs(show_error=False)
            st.success("Logs puliti")
        except Exception:
            st.error("Errore pulizia logs")

logs = st.session_state.get("logs", [])

if not logs:
    st.info("Nessun log caricato.")


st.subheader("Filtri")
levels = sorted({l.get("level") for l in logs if l.get("level")})
subject_types = sorted({l.get("subject_type") for l in logs if l.get("subject_type")})

parsed_dates = [_parse_dt(l.get("created_at")) for l in logs]
parsed_dates = [d for d in parsed_dates if d is not None]
min_date = min(parsed_dates).date() if parsed_dates else None
max_date = max(parsed_dates).date() if parsed_dates else None

colf1, colf2, colf3, colf4 = st.columns(4)
with colf1:
    selected_levels = st.multiselect("Livelli", options=levels, default=levels)
with colf2:
    selected_types = st.multiselect("Subject Type", options=subject_types, default=subject_types)
with colf3:
    subject_query = st.text_input("Subject contiene")
with colf4:
    message_query = st.text_input("Messaggio contiene")

date_range = None
if min_date and max_date:
    date_range = st.date_input(
        "Intervallo date",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
else:
    st.caption("Intervallo date non disponibile: formato data non riconosciuto.")

filtered = [
    l
    for l in logs
    if _matches(l, selected_levels, selected_types, subject_query, message_query, date_range)
]
st.caption(f"Log filtrati: {len(filtered)} / {len(logs)}")

st.dataframe(
    [
        {
            "created_at": l.get("created_at"),
            "level": l.get("level"),
            "subject_type": l.get("subject_type"),
            "subject": l.get("subject"),
            "message": l.get("message"),
        }
        for l in filtered[:500]
    ],
    use_container_width=True,
    hide_index=True,
)
