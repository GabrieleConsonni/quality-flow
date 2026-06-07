import json
import re
from dataclasses import dataclass, field


HTTP_METHOD_OPTIONS = ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS")
BODY_TYPE_ANY = "any"
BODY_TYPE_STRING = "string"
BODY_TYPE_JSON = "json"


@dataclass(slots=True)
class OpenApiImportResult:
    apis_to_append: list[dict] = field(default_factory=list)
    skipped_duplicates: list[str] = field(default_factory=list)
    templated_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def imported_count(self) -> int:
        return len(self.apis_to_append)


def _normalize_path(path: object) -> str:
    raw = str(path or "").strip()
    if not raw:
        return "/"
    if not raw.startswith("/"):
        raw = f"/{raw}"
    if len(raw) > 1:
        raw = raw.rstrip("/")
    return raw


def _route_label(method: str, path: str) -> str:
    return f"{str(method or '').strip().upper()} {_normalize_path(path)}"


def _normalize_existing_routes(
    existing_routes: set[tuple[str, str]] | None,
) -> set[tuple[str, str]]:
    normalized: set[tuple[str, str]] = set()
    for route in existing_routes or set():
        if not isinstance(route, tuple) or len(route) != 2:
            continue
        method, path = route
        normalized.add((str(method or "").strip().upper(), _normalize_path(path)))
    return normalized


def _is_openapi_3(payload: dict) -> bool:
    version = str(payload.get("openapi") or "").strip()
    return version.startswith("3.")


def _iter_json_media_types(content: dict) -> list[dict]:
    preferred_items: list[tuple[int, dict]] = []
    for media_type, media_entry in content.items():
        if not isinstance(media_entry, dict):
            continue
        media_type_value = str(media_type or "").strip().lower()
        score = 99
        if media_type_value == "application/json":
            score = 0
        elif media_type_value.endswith("+json"):
            score = 1
        elif "json" in media_type_value:
            score = 2
        preferred_items.append((score, media_entry))
    preferred_items.sort(key=lambda item: item[0])
    return [item[1] for item in preferred_items]


def _extract_example_from_media_entry(media_entry: dict) -> object | None:
    if "example" in media_entry:
        return media_entry.get("example")

    examples = media_entry.get("examples")
    if isinstance(examples, dict):
        for example_entry in examples.values():
            if isinstance(example_entry, dict) and "value" in example_entry:
                return example_entry.get("value")
            if example_entry is not None:
                return example_entry

    schema = media_entry.get("schema")
    if isinstance(schema, dict) and "example" in schema:
        return schema.get("example")

    return None


def _pick_response_entry(responses: dict) -> tuple[int, dict]:
    response_200 = responses.get("200")
    if isinstance(response_200, dict):
        return 200, response_200

    for status_key, response_entry in responses.items():
        if not isinstance(response_entry, dict):
            continue
        status_value = str(status_key or "").strip()
        if re.fullmatch(r"2\d\d", status_value):
            return int(status_value), response_entry

    default_entry = responses.get("default")
    if isinstance(default_entry, dict):
        return 200, default_entry

    return 200, {}


def _extract_response_body(response_entry: dict) -> object:
    content = response_entry.get("content")
    if not isinstance(content, dict):
        return {"status": "ok"}

    for media_entry in _iter_json_media_types(content):
        example_value = _extract_example_from_media_entry(media_entry)
        if example_value is not None:
            return example_value

    return {"status": "ok"}


def _response_body_type(response_body: object) -> str:
    if isinstance(response_body, str):
        return BODY_TYPE_STRING
    if isinstance(response_body, (dict, list, int, float, bool)):
        return BODY_TYPE_JSON
    return BODY_TYPE_ANY


def _response_headers(response_body: object) -> dict:
    if isinstance(response_body, (dict, list)):
        return {"Content-Type": "application/json"}
    return {}


def _operation_description(method: str, path: str, operation: dict) -> str:
    summary = str(operation.get("summary") or "").strip()
    if summary:
        return summary
    operation_id = str(operation.get("operationId") or "").strip()
    if operation_id:
        return operation_id
    return _route_label(method, path)


def _build_mock_api(method: str, path: str, operation: dict, order: int) -> dict:
    responses = operation.get("responses") if isinstance(operation.get("responses"), dict) else {}
    response_status, response_entry = _pick_response_entry(responses)
    response_body = _extract_response_body(response_entry)
    response_body_type = _response_body_type(response_body)
    normalized_path = _normalize_path(path)
    return {
        "id": None,
        "order": order,
        "description": _operation_description(method, normalized_path, operation),
        "method": str(method or "").strip().upper(),
        "path": normalized_path,
        "configuration_json": {
            "method": str(method or "").strip().upper(),
            "path": normalized_path,
            "params": {},
            "authMode": "inherit",
            "authorization": {},
            "headers": {},
            "body": None,
            "body_type": BODY_TYPE_ANY,
            "body_match": "contains",
            "response_status": response_status,
            "response_headers": _response_headers(response_body),
            "response_body": response_body,
            "response_body_type": response_body_type,
            "priority": 0,
            "pre_response_commands": [],
            "response_operations": [],
            "post_response_commands": [],
        },
        "operations": [],
        "pre_response_commands": [],
        "response_operations": [],
        "post_response_commands": [],
    }


def import_openapi_json(
    raw_bytes: bytes,
    existing_routes: set[tuple[str, str]] | None,
) -> OpenApiImportResult:
    result = OpenApiImportResult()

    try:
        payload = json.loads(raw_bytes.decode("utf-8-sig"))
    except UnicodeDecodeError:
        result.errors.append("Il file deve essere un JSON UTF-8 valido.")
        return result
    except json.JSONDecodeError as exc:
        result.errors.append(f"JSON non valido: {str(exc)}")
        return result

    if not isinstance(payload, dict):
        result.errors.append("Il file OpenAPI deve contenere un oggetto JSON.")
        return result

    if not _is_openapi_3(payload):
        result.errors.append("Sono supportati solo file OpenAPI 3.x in formato JSON.")
        return result

    paths = payload.get("paths")
    if not isinstance(paths, dict):
        result.errors.append("Spec OpenAPI non valida: sezione 'paths' mancante o non valida.")
        return result

    known_routes = _normalize_existing_routes(existing_routes)
    discovered_routes: set[tuple[str, str]] = set()

    for raw_path, path_item in paths.items():
        if not isinstance(path_item, dict):
            result.warnings.append(
                f"Path {_normalize_path(raw_path)} ignorato: definizione path non valida."
            )
            continue

        normalized_path = _normalize_path(raw_path)
        if "{" in normalized_path and "}" in normalized_path:
            route_hint = normalized_path
            if route_hint not in result.templated_paths:
                result.templated_paths.append(route_hint)
                result.warnings.append(
                    f"Il path templated {route_hint} verra importato letteralmente e non matchera /... dinamici."
                )

        for method in HTTP_METHOD_OPTIONS:
            operation = path_item.get(method.lower())
            if not isinstance(operation, dict):
                continue

            route_key = (method, normalized_path)
            route_label = _route_label(method, normalized_path)
            if route_key in known_routes or route_key in discovered_routes:
                result.skipped_duplicates.append(route_label)
                continue

            discovered_routes.add(route_key)
            result.apis_to_append.append(
                _build_mock_api(method, normalized_path, operation, len(result.apis_to_append) + 1)
            )

    return result
