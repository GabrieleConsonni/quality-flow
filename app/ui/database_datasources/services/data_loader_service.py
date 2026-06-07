from urllib.parse import quote_plus

import streamlit as st

from api_client import api_get
from database_datasources.services.state_keys import (
    DATABASE_CONNECTIONS_KEY,
    DATABASE_DATASOURCE_PREVIEW_CACHE_KEY,
    DATABASE_DATASOURCES_KEY,
    DATABASE_OBJECT_PREVIEW_CACHE_KEY,
    DATABASE_OBJECTS_CACHE_KEY,
)


def load_database_datasources(force: bool = False) -> list[dict]:
    if force or DATABASE_DATASOURCES_KEY not in st.session_state:
        try:
            result = api_get("/data-source/database")
            st.session_state[DATABASE_DATASOURCES_KEY] = result if isinstance(result, list) else []
        except Exception:
            st.session_state[DATABASE_DATASOURCES_KEY] = []
    value = st.session_state.get(DATABASE_DATASOURCES_KEY, [])
    return value if isinstance(value, list) else []


def load_database_connections(force: bool = False) -> list[dict]:
    if force or DATABASE_CONNECTIONS_KEY not in st.session_state:
        try:
            result = api_get("/database/connection")
            st.session_state[DATABASE_CONNECTIONS_KEY] = result if isinstance(result, list) else []
        except Exception:
            st.session_state[DATABASE_CONNECTIONS_KEY] = []
    value = st.session_state.get(DATABASE_CONNECTIONS_KEY, [])
    return value if isinstance(value, list) else []


def load_database_connection_objects(connection_id: str, force: bool = False) -> dict:
    cache = st.session_state.setdefault(DATABASE_OBJECTS_CACHE_KEY, {})
    cache_key = str(connection_id or "")
    if not cache_key:
        return {"tables": [], "views": [], "items": [], "schema": None}

    if force or cache_key not in cache:
        try:
            result = api_get(f"/database/connection/{cache_key}/objects")
            cache[cache_key] = result if isinstance(result, dict) else {}
        except Exception:
            cache[cache_key] = {"tables": [], "views": [], "items": [], "schema": None}
    return cache.get(cache_key) or {"tables": [], "views": [], "items": [], "schema": None}


def load_database_object_preview(
    connection_id: str,
    object_name: str,
    object_type: str = "table",
    schema: str | None = None,
    limit: int = 1,
    force: bool = False,
) -> dict | None:
    cache = st.session_state.setdefault(DATABASE_OBJECT_PREVIEW_CACHE_KEY, {})
    cache_key = "|".join(
        [
            str(connection_id or ""),
            str(schema or ""),
            str(object_type or "table"),
            str(object_name or ""),
            str(limit),
        ]
    )
    if not connection_id or not object_name:
        return None
    if force or cache_key not in cache:
        try:
            query_params = (
                f"object_name={quote_plus(str(object_name))}"
                f"&object_type={quote_plus(str(object_type))}"
                f"&limit={int(limit)}"
            )
            if schema:
                query_params += f"&schema={quote_plus(str(schema))}"
            result = api_get(f"/database/connection/{connection_id}/object-preview?{query_params}")
            cache[cache_key] = result if isinstance(result, dict) else None
        except Exception as exc:
            cache[cache_key] = {"error": str(exc), "columns": [], "rows": []}
    return cache.get(cache_key)


def load_database_datasource_preview(datasource_id: str, force: bool = False) -> dict | None:
    cache = st.session_state.setdefault(DATABASE_DATASOURCE_PREVIEW_CACHE_KEY, {})
    cache_key = str(datasource_id or "")
    if not cache_key:
        return None
    if force or cache_key not in cache:
        try:
            result = api_get(f"/data-source/database/{cache_key}/preview")
            cache[cache_key] = result if isinstance(result, dict) else None
        except Exception as exc:
            cache[cache_key] = {"error": str(exc), "rows": []}
    return cache.get(cache_key)


def invalidate_database_datasource_preview(datasource_id: str | None = None):
    cache = st.session_state.setdefault(DATABASE_DATASOURCE_PREVIEW_CACHE_KEY, {})
    if datasource_id is None:
        cache.clear()
        return
    cache.pop(str(datasource_id), None)
