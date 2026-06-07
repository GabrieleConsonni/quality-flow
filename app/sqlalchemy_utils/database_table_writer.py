from sqlalchemy import (
    MetaData, Table, Column, insert, inspect
)
from sqlalchemy.engine.base import Engine

from sqlalchemy_utils.column_type_extractor import extract_column_type


class DatabaseTableWriter:
    @classmethod
    def _split_schema_and_table_name(cls, table_name: str) -> tuple[str | None, str]:
        if "." in table_name:
            schema_name, table_name_only = table_name.split(".", 1)
            return schema_name.strip() or None, table_name_only.strip()
        return None, table_name

    @classmethod
    def ensure_table_exists(cls, engine: Engine, table_name: str, schema: dict)-> Table:
        schema_name, table_name_only = cls._split_schema_and_table_name(table_name)
        inspector = inspect(engine)

        if inspector.has_table(table_name_only, schema=schema_name):
            metadata = MetaData()
            return Table(
                table_name_only,
                metadata,
                schema=schema_name,
                autoload_with=engine,
            )

        columns = []

        for key, value in schema.items():
            col_type = extract_column_type(value)
            columns.append(Column(key, col_type))

        metadata = MetaData()
        table = Table(table_name_only, metadata, *columns, schema=schema_name)
        metadata.create_all(engine, tables=[table])

        return table


    @classmethod
    def insert_rows(cls, engine: Engine, table: Table, rows: list[dict]):
        if not rows:
            return

        with engine.begin() as conn:
            conn.execute(insert(table), rows)

