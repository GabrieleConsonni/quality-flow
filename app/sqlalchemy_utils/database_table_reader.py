from dataclasses import dataclass

import polars as pl
from sqlalchemy import text, Engine
from typing import Iterator, List, Dict
from sqlalchemy.engine import Engine, Result

@dataclass
class ReadTableConfig:
    table_name: str | None = None
    query: str | None = None
    chunk_size: int = 1000
    stream: bool = False
    order_by: List[str] | None = None


class DatabaseTableReader:

    @classmethod
    def test_connection(cls, engine) -> bool:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


    @classmethod
    def read_table_chunks(
            cls,
            engine: Engine,
            cfg: ReadTableConfig
    ) -> Iterator[List[Dict]]:
        if not cfg.query and not cfg.table_name:
            raise ValueError("Either query or table_name must be provided")

        sql = cfg.query
        if not sql and cfg.table_name:
            sql = f"SELECT * FROM {cfg.table_name}"
            sql += f" ORDER BY {', '.join(cfg.order_by)}" if cfg.order_by else ""

        with engine.connect() as connection:
            conn = connection.execution_options(stream_results=True) if cfg.stream else connection

            result: Result = conn.execute(text(sql))

            while True:
                rows = result.fetchmany(cfg.chunk_size)
                if not rows:
                    break
                df = pl.from_records(rows)
                chunk = df.to_dicts()
                yield chunk

    @classmethod
    def read_full_table(
            cls,
            engine: Engine,
            cfg: ReadTableConfig
    ) -> List[Dict]:
        if not cfg.query and not cfg.table_name:
            raise ValueError("Either query or table_name must be provided")

        sql = cfg.query
        if not sql and cfg.table_name:
            sql = f"SELECT * FROM {cfg.table_name}"
            sql += f" ORDER BY {', '.join(cfg.order_by)}" if cfg.order_by else ""

        with engine.connect() as connection:
            result: Result = connection.execute(text(sql))
            rows = result.fetchall()
            df = pl.from_records(rows)
            return df.to_dicts()
