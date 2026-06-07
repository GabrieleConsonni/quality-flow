import time

from sqlalchemy.orm import Session

from _alembic.models.suite_test_entity import SuiteTestEntity
from elaborations.models.dtos.configuration_test_dtos import SleepConfigurationTestDto
from elaborations.services.suite_runs.run_context import set_context_last
from elaborations.services.suite_tests.test_executor import TestExecutor


class SleepTestExecutor(TestExecutor):
    def execute(
        self,
        session: Session,
        suite_test: SuiteTestEntity,
        cfg: SleepConfigurationTestDto,
    ) -> list[dict[str, str]]:
        time.sleep(cfg.duration)
        test_code = str(suite_test.code or suite_test.id)
        self.log(test_code, f"Slept for {cfg.duration} seconds")
        output = [{"status": "slept", "duration": str(cfg.duration)}]
        set_context_last(item_id=test_code, data=output)
        return output
