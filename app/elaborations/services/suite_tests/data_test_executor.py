from sqlalchemy.orm import Session

from _alembic.models.suite_test_entity import SuiteTestEntity
from elaborations.models.dtos.configuration_test_dtos import DataConfigurationTestDTO
from elaborations.services.suite_tests.test_executor import TestExecutor


class DataTestExecutor(TestExecutor):
    def execute(
        self,
        session: Session,
        suite_test: SuiteTestEntity,
        cfg: DataConfigurationTestDTO,
    ) -> list[dict[str, str]]:
        test_code = str(suite_test.code or suite_test.id)
        self.log(test_code, f"Try to export {len(cfg.data)} objects")
        return self.execute_operations(
            session,
            suite_test.id,
            test_code,
            cfg.data,
        )
