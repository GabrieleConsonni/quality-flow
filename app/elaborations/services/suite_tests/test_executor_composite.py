from sqlalchemy.orm import Session

from _alembic.models.suite_test_entity import SuiteTestEntity
from elaborations.models.dtos.configuration_test_dtos import (
    ConfigurationTestDto,
    ConfigurationTestDtoTypes,
    DataConfigurationTestDTO,
    DataFromDbConfigurationTestDto,
    DataFromJsonArrayConfigurationTestDto,
    DataFromQueueConfigurationTestDto,
    SleepConfigurationTestDto,
    convert_to_config_test_type,
)
from elaborations.services.suite_tests.data_from_db_test_executor import DataFromDbTestExecutor
from elaborations.services.suite_tests.data_from_json_array_test_executor import DataFromJsonArrayTestExecutor
from elaborations.services.suite_tests.data_from_queue_test_executor import DataFromQueueTestExecutor
from elaborations.services.suite_tests.data_test_executor import DataTestExecutor
from elaborations.services.suite_tests.sleep_test_executor import SleepTestExecutor
from elaborations.services.suite_tests.test_executor import TestExecutor

_EXECUTOR_MAPPING: dict[type[ConfigurationTestDto], type[TestExecutor]] = {
    SleepConfigurationTestDto: SleepTestExecutor,
    DataConfigurationTestDTO: DataTestExecutor,
    DataFromJsonArrayConfigurationTestDto: DataFromJsonArrayTestExecutor,
    DataFromDbConfigurationTestDto: DataFromDbTestExecutor,
    DataFromQueueConfigurationTestDto: DataFromQueueTestExecutor,
}


def execute_test(session: Session, suite_test: SuiteTestEntity) -> list[dict[str, str]]:
    suite_cfg = (
        suite_test.configuration_json
        if isinstance(suite_test.configuration_json, dict)
        else {}
    )
    cfg: ConfigurationTestDtoTypes = convert_to_config_test_type(suite_cfg)

    clazz = _EXECUTOR_MAPPING.get(type(cfg))
    if clazz is None:
        supported_types = list(_EXECUTOR_MAPPING.keys())
        raise ValueError(
            f"Unsupported test type: {cfg}. "
            f"Supported types: {supported_types}"
        )
    test_executor = clazz()
    return test_executor.execute(session, suite_test, cfg)
