from sqlalchemy.orm import Session

from _alembic.models.json_payload_entity import JsonPayloadEntity
from _alembic.models.suite_test_entity import SuiteTestEntity
from elaborations.models.dtos.configuration_test_dtos import DataFromJsonArrayConfigurationTestDto
from elaborations.services.suite_tests.test_executor import TestExecutor
from json_utils.services.alembic.json_files_service import JsonFilesService


class DataFromJsonArrayTestExecutor(TestExecutor):
    def execute(
        self,
        session: Session,
        suite_test: SuiteTestEntity,
        cfg: DataFromJsonArrayConfigurationTestDto,
    ) -> list[dict[str, str]]:
        test_code = str(suite_test.code or suite_test.id)
        json_array = self.load_json_array(session, cfg.json_array_id)

        self.log(
            test_code,
            f"Try to elaborate {len(json_array)} objects from JSON array",
        )

        return self.execute_operations(
            session,
            suite_test.id,
            test_code,
            json_array,
        )

    def load_json_array(self,session:Session, json_array_id:str):
        json_payload_entity: JsonPayloadEntity = JsonFilesService().get_by_id(session, json_array_id)

        if not json_payload_entity:
            raise ValueError(f"Json array '{json_array_id}' not found")

        if isinstance(json_payload_entity.payload, list):
            return json_payload_entity.payload
        else:
            return [json_payload_entity.payload]
