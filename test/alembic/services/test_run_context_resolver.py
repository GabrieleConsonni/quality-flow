import pytest

from app.elaborations.services.suite_runs.run_context_resolver import resolve_dynamic_value


def test_resolve_dynamic_value_supports_ref_paths():
    scope = {
        "event": {"payload": {"items": [{"sku": "SKU-001"}]}},
        "vars": {"tenant": "it"},
        "last": {"data": {"id": 10}},
        "artifacts": {},
    }
    value = {
        "sku": {"$ref": "$.event.payload.items[0].sku"},
        "tenant": {"$ref": "$.vars.tenant"},
        "last_id": {"$ref": "$.last.data.id"},
    }

    assert resolve_dynamic_value(value, scope) == {
        "sku": "SKU-001",
        "tenant": "it",
        "last_id": 10,
    }


def test_resolve_dynamic_value_uses_default_when_missing():
    scope = {
        "event": {},
        "vars": {},
        "last": {},
        "artifacts": {},
    }
    value = {"$ref": "$.vars.missing", "$default": "fallback"}

    assert resolve_dynamic_value(value, scope) == "fallback"


def test_resolve_dynamic_value_raises_when_required_and_missing():
    scope = {
        "event": {},
        "vars": {},
        "last": {},
        "artifacts": {},
    }
    value = {"$ref": "$.vars.missing", "$required": True}

    with pytest.raises(ValueError, match="Required reference not found"):
        resolve_dynamic_value(value, scope)


def test_resolve_dynamic_value_supports_string_ref_value():
    scope = {
        "event": {
            "meta": {"headers": {"authorization": "Bearer 123"}},
        },
        "vars": {},
        "last": {},
        "artifacts": {},
    }
    value = {
        "token": "$.event.meta.headers.authorization",
    }

    assert resolve_dynamic_value(value, scope) == {
        "token": "Bearer 123",
    }


def test_resolve_dynamic_value_keeps_unresolved_string_ref_literal():
    scope = {
        "event": {},
        "vars": {},
        "last": {},
        "artifacts": {},
    }
    value = {
        "token": "$.event.meta.headers.autorization",
    }

    assert resolve_dynamic_value(value, scope) == {
        "token": "$.event.meta.headers.autorization",
    }


def test_resolve_dynamic_value_keeps_non_runtime_ref_objects_literal():
    scope = {
        "event": {},
        "vars": {},
        "last": {},
        "artifacts": {},
    }
    value = {
        "schema": {
            "$ref": "#/components/schemas/HealthResponse",
        },
    }

    assert resolve_dynamic_value(value, scope) == {
        "schema": {
            "$ref": "#/components/schemas/HealthResponse",
        },
    }
