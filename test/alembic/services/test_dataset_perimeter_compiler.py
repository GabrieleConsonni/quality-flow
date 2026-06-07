from sqlalchemy import Column, Integer, MetaData, String, Table

import pytest

from app.data_sources.services.dataset_parameter_resolver import DatasetParameterResolver
from app.data_sources.services.dataset_perimeter_compiler import DatasetPerimeterCompiler


def _build_orders_table() -> Table:
    metadata = MetaData()
    return Table(
        "orders",
        metadata,
        Column("id", Integer),
        Column("status", String),
        Column("note", String),
    )


def test_dataset_perimeter_compiler_rejects_duplicate_selected_columns():
    table = _build_orders_table()

    with pytest.raises(ValueError, match="Duplicate selected column 'id'"):
        DatasetPerimeterCompiler.compile(
            table,
            {"selected_columns": ["id", "id"]},
        )


def test_dataset_perimeter_compiler_rejects_unknown_fields():
    table = _build_orders_table()

    with pytest.raises(ValueError, match="Filter field 'missing' does not exist."):
        DatasetPerimeterCompiler.compile(
            table,
            {
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {"field": "missing", "operator": "eq", "value": 1},
                    ],
                }
            },
        )


def test_dataset_perimeter_compiler_binds_values_instead_of_inlining_them():
    table = _build_orders_table()
    malicious_value = "READY' OR 1=1 --"

    compilation = DatasetPerimeterCompiler.compile(
        table,
        {
            "selected_columns": ["id", "status"],
            "filter": {
                "logic": "AND",
                "conditions": [
                    {"field": "status", "operator": "eq", "value": malicious_value},
                ],
            },
            "sort": [{"field": "id", "direction": "desc"}],
        },
        limit=100,
    )
    compiled_stmt = compilation.stmt.compile()
    compiled_sql = str(compiled_stmt)

    assert malicious_value not in compiled_sql
    assert malicious_value in compiled_stmt.params.values()
    assert compilation.columns == ["id", "status"]


def test_dataset_perimeter_compiler_supports_parameter_references():
    table = _build_orders_table()

    compilation = DatasetPerimeterCompiler.compile(
        table,
        {
            "parameters": [
                {
                    "name": "statusParam",
                    "type": "string",
                }
            ],
            "filter": {
                "logic": "AND",
                "conditions": [
                    {
                        "field": "status",
                        "operator": "eq",
                        "value": {"kind": "parameter", "name": "statusParam"},
                    },
                ],
            },
        },
        resolved_parameters={"statusParam": "READY"},
    )

    compiled_stmt = compilation.stmt.compile()
    assert compiled_stmt.params
    assert "READY" in compiled_stmt.params.values()


def test_dataset_perimeter_compiler_rejects_unknown_parameter_references():
    table = _build_orders_table()

    with pytest.raises(ValueError, match="unknown dataset parameter 'missingParam'"):
        DatasetPerimeterCompiler.compile(
            table,
            {
                "parameters": [
                    {
                        "name": "statusParam",
                        "type": "string",
                    }
                ],
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {
                            "field": "status",
                            "operator": "eq",
                            "value": {"kind": "parameter", "name": "missingParam"},
                        },
                    ],
                },
            },
            resolved_parameters={"statusParam": "READY"},
        )


def test_dataset_perimeter_compiler_normalizes_default_binding():
    normalized = DatasetPerimeterCompiler.normalize(
        {
            "parameters": [
                {
                    "name": "snapshotAt",
                    "type": "datetime",
                    "default_binding": {
                        "kind": "built_in",
                        "resolver": "$now",
                    },
                }
            ]
        }
    )

    assert normalized == {
        "parameters": [
            {
                "name": "snapshotAt",
                "type": "datetime",
                "description": None,
                "default_binding": {
                    "kind": "built_in",
                    "resolver": "$now",
                },
            }
        ]
    }


def test_dataset_perimeter_compiler_rejects_parameter_with_both_default_value_and_default_binding():
    with pytest.raises(ValueError, match="cannot declare both default_value and default_binding"):
        DatasetPerimeterCompiler.normalize(
            {
                "parameters": [
                    {
                        "name": "snapshotAt",
                        "type": "datetime",
                        "default_value": "2026-03-21T09:00:00",
                        "default_binding": {
                            "kind": "built_in",
                            "resolver": "$now",
                        },
                    }
                ]
            }
        )


def test_dataset_perimeter_compiler_rejects_invalid_default_binding_resolver():
    with pytest.raises(ValueError, match="resolver must be one of: \\$now, \\$today"):
        DatasetPerimeterCompiler.normalize(
            {
                "parameters": [
                    {
                        "name": "snapshotAt",
                        "type": "datetime",
                        "default_binding": {
                            "kind": "built_in",
                            "resolver": "$utc_now",
                        },
                    }
                ]
            }
        )


def test_dataset_parameter_resolver_supports_builtin_defaults():
    resolved = DatasetParameterResolver.resolve(
        {
            "parameters": [
                {
                    "name": "snapshotAt",
                    "type": "datetime",
                    "default_binding": {
                        "kind": "built_in",
                        "resolver": "$now",
                    },
                },
                {
                    "name": "currentDay",
                    "type": "date",
                    "default_binding": {
                        "kind": "built_in",
                        "resolver": "$today",
                    },
                },
            ]
        }
    )

    assert resolved["snapshotAt"].__class__.__name__ == "datetime"
    assert resolved["currentDay"].__class__.__name__ == "date"
