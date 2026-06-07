DATABASE_TYPE_OPTIONS = {
    "Postgres": "postgres",
    "Oracle": "oracle",
    "MSSQL": "sqlserver",
}

DEFAULT_PORT_BY_TYPE = {
    "postgres": 5432,
    "oracle": 1521,
    "sqlserver": 1433,
}


def pick_database_type_label(database_type: str | None) -> str:
    normalized = str(database_type or "").strip().lower()
    for label, value in DATABASE_TYPE_OPTIONS.items():
        if value == normalized:
            return label
    return "Postgres"

