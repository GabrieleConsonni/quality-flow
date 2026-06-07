from sqlalchemy.orm import Session

from _alembic.models.suite_test_entity import SuiteTestEntity
from data_sources.services.dataset_query_service import DatasetQueryService
from elaborations.models.dtos.configuration_test_dtos import DataFromDbConfigurationTestDto
from elaborations.services.suite_tests.test_executor import TestExecutor


class DataFromDbTestExecutor(TestExecutor):

    def execute(
        self,
        session: Session,
        suite_test: SuiteTestEntity,
        cfg: DataFromDbConfigurationTestDto,
    ) -> list[dict[str, str]]:
        test_code = str(suite_test.code or suite_test.id)
        data_source_id = str(cfg.dataset_id or "").strip()
        dataset = DatasetQueryService.get_dataset_or_raise_for_runtime(session, data_source_id)
        table_name = DatasetQueryService.qualified_table_name_from_dataset(dataset)

        self.log(test_code, f"Start reading table '{table_name}'")

        rows = DatasetQueryService.load_rows_for_runtime(dataset)

        total_rows = len(rows) if isinstance(rows, list) else 0

        results = self.execute_operations(
            session,
            suite_test.id,
            test_code,
            rows,
        )

        self.log(test_code,
                 f"Finished reading table '{table_name}'. Total rows processed: {total_rows}")

        return results
