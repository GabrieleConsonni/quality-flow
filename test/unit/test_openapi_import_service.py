import json

from app.mock_servers.services.openapi_import_service import import_openapi_json


def _raw_json(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def test_import_openapi_json_maps_summary_and_json_example():
    result = import_openapi_json(
        _raw_json(
            {
                "openapi": "3.0.3",
                "paths": {
                    "/orders": {
                        "get": {
                            "summary": "List orders",
                            "responses": {
                                "200": {
                                    "description": "OK",
                                    "content": {
                                        "application/json": {
                                            "example": {"items": [{"id": 1}]}
                                        }
                                    },
                                }
                            },
                        }
                    }
                },
            }
        ),
        existing_routes=set(),
    )

    assert result.errors == []
    assert result.imported_count == 1
    api_entry = result.apis_to_append[0]
    assert api_entry["description"] == "List orders"
    assert api_entry["method"] == "GET"
    assert api_entry["path"] == "/orders"
    assert api_entry["configuration_json"]["response_status"] == 200
    assert api_entry["configuration_json"]["response_body"] == {"items": [{"id": 1}]}
    assert api_entry["configuration_json"]["response_headers"] == {
        "Content-Type": "application/json"
    }
    assert api_entry["configuration_json"]["response_body_type"] == "json"
    assert api_entry["configuration_json"]["authMode"] == "inherit"
    assert api_entry["configuration_json"]["authorization"] == {}


def test_import_openapi_json_rejects_invalid_json():
    result = import_openapi_json(b"{not-json}", existing_routes=set())

    assert result.imported_count == 0
    assert result.errors
    assert "JSON non valido" in result.errors[0]


def test_import_openapi_json_rejects_non_openapi_3_spec():
    result = import_openapi_json(
        _raw_json(
            {
                "swagger": "2.0",
                "paths": {},
            }
        ),
        existing_routes=set(),
    )

    assert result.imported_count == 0
    assert result.errors == ["Sono supportati solo file OpenAPI 3.x in formato JSON."]


def test_import_openapi_json_uses_operation_id_and_method_path_fallbacks():
    result = import_openapi_json(
        _raw_json(
            {
                "openapi": "3.0.1",
                "paths": {
                    "/orders": {
                        "post": {
                            "operationId": "createOrder",
                            "responses": {
                                "201": {
                                    "description": "Created",
                                    "content": {
                                        "application/json": {
                                            "examples": {
                                                "default": {
                                                    "value": {"created": True}
                                                }
                                            }
                                        }
                                    },
                                }
                            },
                        }
                    },
                    "/health": {
                        "get": {
                            "responses": {
                                "default": {
                                    "description": "Default response",
                                }
                            },
                        }
                    },
                },
            }
        ),
        existing_routes=set(),
    )

    assert result.imported_count == 2
    post_api = next(api for api in result.apis_to_append if api["method"] == "POST")
    get_api = next(api for api in result.apis_to_append if api["method"] == "GET")

    assert post_api["description"] == "createOrder"
    assert post_api["configuration_json"]["response_status"] == 201
    assert post_api["configuration_json"]["response_body"] == {"created": True}

    assert get_api["description"] == "GET /health"
    assert get_api["configuration_json"]["response_status"] == 200
    assert get_api["configuration_json"]["response_body"] == {"status": "ok"}


def test_import_openapi_json_skips_existing_and_internal_duplicates_and_reports_templated_paths():
    result = import_openapi_json(
        _raw_json(
            {
                "openapi": "3.0.2",
                "paths": {
                    "/orders": {
                        "get": {"responses": {"200": {"description": "OK"}}},
                        "post": {"responses": {"200": {"description": "OK"}}},
                    },
                    "orders/": {
                        "post": {"responses": {"200": {"description": "OK"}}},
                    },
                    "/orders/{id}": {
                        "get": {"responses": {"200": {"description": "OK"}}},
                    },
                },
            }
        ),
        existing_routes={("GET", "/orders")},
    )

    assert result.imported_count == 2
    assert result.skipped_duplicates == ["GET /orders", "POST /orders"]
    assert result.templated_paths == ["/orders/{id}"]
    assert any("importato letteralmente" in warning for warning in result.warnings)

    imported_routes = {(api["method"], api["path"]) for api in result.apis_to_append}
    assert imported_routes == {("POST", "/orders"), ("GET", "/orders/{id}")}


def test_import_openapi_json_uses_string_body_type_for_string_examples():
    result = import_openapi_json(
        _raw_json(
            {
                "openapi": "3.0.3",
                "paths": {
                    "/plain-text": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "OK",
                                    "content": {
                                        "application/problem+json": {
                                            "example": "plain text body"
                                        }
                                    },
                                }
                            },
                        }
                    }
                },
            }
        ),
        existing_routes=set(),
    )

    assert result.imported_count == 1
    api_entry = result.apis_to_append[0]
    assert api_entry["configuration_json"]["response_body"] == "plain text body"
    assert api_entry["configuration_json"]["response_body_type"] == "string"
    assert api_entry["configuration_json"]["response_headers"] == {}
