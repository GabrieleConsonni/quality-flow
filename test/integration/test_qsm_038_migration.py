import os
from datetime import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from docker.errors import DockerException
from sqlalchemy import MetaData, Table, create_engine, select, text
from testcontainers.core.exceptions import ContainerStartException
from testcontainers.postgres import PostgresContainer


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _start_container_or_skip(container, name: str):
    try:
        return container.start()
    except (DockerException, ContainerStartException) as exc:
        pytest.skip(f"Cannot start {name} test container: {exc}")


def _build_alembic_config() -> Config:
    return Config(str(PROJECT_ROOT / "alembic.ini"))


def test_qsm_038_migrates_database_table_payloads_to_datasets():
    container = PostgresContainer("postgres:16-alpine")
    started_container = _start_container_or_skip(container, "postgres")
    previous_database_url = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = started_container.get_connection_url()
        alembic_cfg = _build_alembic_config()
        command.upgrade(alembic_cfg, "b2c3d4e5f6a")

        engine = create_engine(os.environ["DATABASE_URL"])
        try:
            metadata = MetaData()
            json_payloads = Table(
                "json_payloads",
                metadata,
                schema="quality_flow_service",
                autoload_with=engine,
            )
            with engine.begin() as conn:
                conn.execute(
                    json_payloads.insert().values(
                        id="dataset-legacy-1",
                        description="legacy dataset",
                        json_type="database-table",
                        payload={
                            "connection_id": "conn-1",
                            "schema": "public",
                            "object_name": "orders",
                            "object_type": "table",
                        },
                        created_date=datetime.utcnow(),
                        modified_date=datetime.utcnow(),
                    )
                )
        finally:
            engine.dispose()

        command.upgrade(alembic_cfg, "head")

        engine = create_engine(os.environ["DATABASE_URL"])
        try:
            metadata = MetaData()
            datasets = Table(
                "datasets",
                metadata,
                schema="quality_flow_service",
                autoload_with=engine,
            )
            json_payloads = Table(
                "json_payloads",
                metadata,
                schema="quality_flow_service",
                autoload_with=engine,
            )
            with engine.connect() as conn:
                dataset_row = conn.execute(
                    select(datasets).where(datasets.c.id == "dataset-legacy-1")
                ).mappings().one()
                old_row = conn.execute(
                    select(json_payloads.c.id).where(json_payloads.c.id == "dataset-legacy-1")
                ).all()
        finally:
            engine.dispose()

        assert dataset_row["description"] == "legacy dataset"
        assert dataset_row["configuration_json"]["object_name"] == "orders"
        assert dataset_row["perimeter"] is None
        assert old_row == []
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        started_container.stop()


def test_qsm_038_fix_migration_creates_datasets_for_already_migrated_db():
    container = PostgresContainer("postgres:16-alpine")
    started_container = _start_container_or_skip(container, "postgres")
    previous_database_url = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = started_container.get_connection_url()
        alembic_cfg = _build_alembic_config()
        command.upgrade(alembic_cfg, "d5f6a7b8c9d0")

        engine = create_engine(os.environ["DATABASE_URL"])
        try:
            metadata = MetaData()
            datasets = Table(
                "datasets",
                metadata,
                schema="quality_flow_service",
                autoload_with=engine,
            )
            json_payloads = Table(
                "json_payloads",
                metadata,
                schema="quality_flow_service",
                autoload_with=engine,
            )
            with engine.begin() as conn:
                conn.execute(text('DROP TABLE IF EXISTS "quality_flow_service"."datasets"'))
                conn.execute(
                    json_payloads.insert().values(
                        id="dataset-legacy-2",
                        description="legacy dataset after old head",
                        json_type="database-table",
                        payload={
                            "connection_id": "conn-2",
                            "schema": "public",
                            "object_name": "customers",
                            "object_type": "table",
                        },
                        created_date=datetime.utcnow(),
                        modified_date=datetime.utcnow(),
                    )
                )
        finally:
            engine.dispose()

        command.upgrade(alembic_cfg, "head")

        engine = create_engine(os.environ["DATABASE_URL"])
        try:
            metadata = MetaData()
            datasets = Table(
                "datasets",
                metadata,
                schema="quality_flow_service",
                autoload_with=engine,
            )
            with engine.connect() as conn:
                dataset_row = conn.execute(
                    select(datasets).where(datasets.c.id == "dataset-legacy-2")
                ).mappings().one()
        finally:
            engine.dispose()

        assert dataset_row["description"] == "legacy dataset after old head"
        assert dataset_row["configuration_json"]["object_name"] == "customers"
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        started_container.stop()
