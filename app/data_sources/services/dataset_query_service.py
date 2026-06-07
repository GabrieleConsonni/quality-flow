from sqlalchemy import MetaData, Table, inspect
from sqlalchemy.orm import Session

from _alembic.models.dataset_entity import DatasetEntity
from data_sources.models.database_connection_config_types import convert_database_connection_config
from data_sources.services.alembic.dataset_service import DatasetService
from data_sources.services.dataset_parameter_resolver import DatasetParameterResolver
from data_sources.services.alembic.database_connection_service import load_database_connection
from data_sources.services.dataset_perimeter_compiler import DatasetPerimeterCompiler
from exceptions.app_exception import QualityFlowAppException
from json_utils.services.alembic.json_files_service import JsonFilesService
from sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import (
    create_sqlalchemy_engine,
)


class DatasetQueryService:
    @staticmethod
    def safe_limit(limit: int) -> int:
        if limit <= 0:
            return 1
        if limit > 500:
            return 500
        return limit

    @staticmethod
    def normalize_object_type(value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"table", "base table"}:
            return "table"
        if normalized == "view":
            return "view"
        raise QualityFlowAppException(f"Unsupported object type: {value}")

    @classmethod
    def validate_dataset_configuration(cls, payload: dict):
        if not isinstance(payload, dict):
            raise QualityFlowAppException("Payload non valido: deve essere un oggetto JSON.")

        connection_id = str(payload.get("connection_id") or "").strip()
        object_name = str(payload.get("object_name") or "").strip()
        object_type = cls.normalize_object_type(str(payload.get("object_type") or "table"))

        if not connection_id:
            raise QualityFlowAppException("Payload non valido: connection_id obbligatorio.")
        if not object_name:
            raise QualityFlowAppException("Payload non valido: object_name obbligatorio.")

        payload["connection_id"] = connection_id
        payload["object_name"] = object_name
        payload["object_type"] = object_type
        if payload.get("schema") is not None:
            payload["schema"] = str(payload.get("schema") or "").strip() or None

    @classmethod
    def normalize_perimeter(cls, perimeter: dict | None) -> dict | None:
        try:
            return DatasetPerimeterCompiler.normalize(perimeter)
        except ValueError as exc:
            raise QualityFlowAppException(str(exc)) from exc

    @staticmethod
    def serialize_dataset(entity: DatasetEntity) -> dict:
        return {
            "id": entity.id,
            "description": entity.description,
            "payload": (
                entity.configuration_json
                if isinstance(entity.configuration_json, dict)
                else {}
            ),
            "perimeter": entity.perimeter if isinstance(entity.perimeter, dict) else None,
        }

    @classmethod
    def get_dataset_or_raise(cls, session: Session, dataset_id: str) -> DatasetEntity:
        dataset = DatasetService().get_by_id(session, str(dataset_id or "").strip())
        if not dataset:
            raise QualityFlowAppException(f"No database datasource found with id [ {dataset_id} ]")
        return dataset

    @classmethod
    def get_dataset_or_raise_for_runtime(cls, session: Session, dataset_id: str) -> DatasetEntity:
        dataset = DatasetService().get_by_id(session, str(dataset_id or "").strip())
        if not dataset:
            raise ValueError(f"Database datasource '{dataset_id}' not found")
        return dataset

    @classmethod
    def load_rows_for_runtime(
        cls,
        dataset: DatasetEntity,
        limit: int | None = None,
        parameter_values: dict | None = None,
        session: Session | None = None,
    ) -> list[dict]:
        preview = cls.execute_dataset_query(
            dataset.configuration_json if isinstance(dataset.configuration_json, dict) else {},
            dataset.perimeter if isinstance(dataset.perimeter, dict) else None,
            limit=limit,
            parameter_values=parameter_values,
            dataset_id=str(dataset.id or "").strip() or None,
            session=session,
        )
        return preview["rows"]

    @classmethod
    def qualified_table_name_from_dataset(cls, dataset: DatasetEntity) -> str:
        payload = dataset.configuration_json if isinstance(dataset.configuration_json, dict) else {}
        object_name = str(payload.get("object_name") or "").strip()
        schema = str(payload.get("schema") or "").strip()
        return object_name if not schema or "." in object_name else f"{schema}.{object_name}"

    @staticmethod
    def load_database_connection_for_query(
        config: dict,
        *,
        session: Session | None = None,
    ):
        connection_id = str(config.get("connection_id") or "").strip()
        if session is not None:
            json_payload_entity = JsonFilesService().get_by_id(session, connection_id)
            if json_payload_entity and isinstance(json_payload_entity.payload, dict):
                return convert_database_connection_config(json_payload_entity.payload)
        return load_database_connection(connection_id)

    @classmethod
    def execute_dataset_query(
        cls,
        payload: dict,
        perimeter: dict | None,
        *,
        limit: int | None = None,
        parameter_values: dict | None = None,
        dataset_id: str | None = None,
        session: Session | None = None,
    ) -> dict:
        config = dict(payload or {})
        cls.validate_dataset_configuration(config)
        try:
            normalized_perimeter = cls.normalize_perimeter(perimeter)
            resolved_parameters = DatasetParameterResolver.resolve(
                normalized_perimeter,
                parameter_values,
                dataset_id=dataset_id,
            )

            connection = cls.load_database_connection_for_query(config, session=session)
            if not connection:
                raise QualityFlowAppException(
                    f"No database connection found with id [ {config['connection_id']} ]"
                )

            schema = config.get("schema") or connection.db_schema or None
            object_name = config["object_name"]
            object_type = cls.normalize_object_type(config.get("object_type", "table"))

            engine = create_sqlalchemy_engine(connection)
            inspector = inspect(engine)
            allowed_names = (
                inspector.get_table_names(schema=schema)
                if object_type == "table"
                else inspector.get_view_names(schema=schema)
            )
            if object_name not in allowed_names:
                raise QualityFlowAppException(
                    f"Object [ {object_name} ] not found for type [ {object_type} ]"
                )

            metadata = MetaData()
            table = Table(
                object_name,
                metadata,
                schema=schema,
                autoload_with=engine,
            )
            compilation = DatasetPerimeterCompiler.compile(
                table,
                normalized_perimeter,
                limit=cls.safe_limit(limit) if limit is not None else None,
                resolved_parameters=resolved_parameters,
            )

            with engine.connect() as db_connection:
                result = db_connection.execute(compilation.stmt)
                rows = [dict(row._mapping) for row in result]

            return {
                "schema": schema,
                "object_name": object_name,
                "object_type": object_type,
                "columns": compilation.columns,
                "rows": rows,
                "count": len(rows),
                "perimeter": compilation.normalized_perimeter,
                "resolved_parameters": resolved_parameters,
            }
        except QualityFlowAppException:
            raise
        except ValueError as exc:
            raise QualityFlowAppException(str(exc)) from exc
        finally:
            if "engine" in locals():
                engine.dispose()
