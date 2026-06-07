import os

import requests


API_BASE_URL = os.getenv("QUALITY_FLOW_API_BASE_URL", "http://localhost:9082").rstrip("/")
API_TIMEOUT_SECONDS = float(os.getenv("QUALITY_FLOW_API_TIMEOUT_SECONDS", "30"))


def _raise_for_status_with_detail(response: requests.Response):
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("detail")
        except ValueError:
            detail = None
        if detail:
            raise requests.HTTPError(
                f"{response.status_code} Server Error: {detail}",
                response=response,
                request=response.request,
            ) from exc
        raise


def api_get(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=API_TIMEOUT_SECONDS)
    _raise_for_status_with_detail(response)
    return response.json()


def api_post(path: str, payload: dict):
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=API_TIMEOUT_SECONDS)
    _raise_for_status_with_detail(response)
    return response.json()


def api_put(path: str, payload: dict):
    response = requests.put(f"{API_BASE_URL}{path}", json=payload, timeout=API_TIMEOUT_SECONDS)
    _raise_for_status_with_detail(response)
    return response.json()


def api_delete(path: str):
    response = requests.delete(f"{API_BASE_URL}{path}", timeout=API_TIMEOUT_SECONDS)
    _raise_for_status_with_detail(response)
    return response.json()
