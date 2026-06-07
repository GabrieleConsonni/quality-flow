from sqlalchemy import text

class DatabaseTableManager:
    @classmethod
    def create_table(cls,
                     engine,
                     table_name: str,
                     columns: dict[str, str],
                     primary_key: str | None = None):
        with engine.connect() as connection:
            columns_str = ', '.join([f"{col} {dtype}" for col, dtype in columns.items()])
            pk_str = f", PRIMARY KEY ({primary_key})" if primary_key else ""
            create_table = text(f"CREATE TABLE {table_name} ({columns_str}{pk_str})")
            connection.execute(create_table)
            connection.commit()

    @classmethod
    def drop_table(cls,
                   engine,
                   table_name: str):

        with engine.connect() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            connection.commit()