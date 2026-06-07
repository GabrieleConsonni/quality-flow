from pydantic import BaseModel

from elaborations.models.enums.test_type import TestType


class ConfigurationTestDto(BaseModel):
    testType: str

class SleepConfigurationTestDto(ConfigurationTestDto):
    testType: str = TestType.SLEEP.value
    duration: int

class DataFromJsonArrayConfigurationTestDto(ConfigurationTestDto):
    testType: str = TestType.DATA_FROM_JSON_ARRAY.value
    json_array_id: str

class DataConfigurationTestDTO(ConfigurationTestDto):
    testType: str = TestType.DATA.value
    data: list[dict]

class DataFromDbConfigurationTestDto(ConfigurationTestDto):
    testType: str = TestType.DATA_FROM_DB.value
    dataset_id: str | None = None

class DataFromQueueConfigurationTestDto(ConfigurationTestDto):
    testType: str = TestType.DATA_FROM_QUEUE.value
    queue_id: str
    retry: int = 3
    wait_time_seconds: int = 20
    max_messages: int = 1000


ConfigurationTestDtoTypes = SleepConfigurationTestDto | DataConfigurationTestDTO |DataFromJsonArrayConfigurationTestDto | DataFromQueueConfigurationTestDto |DataFromDbConfigurationTestDto


def convert_to_config_test_type(data: dict):
    test_type = data.get("testType")
    if test_type == TestType.SLEEP.value:
        return SleepConfigurationTestDto(
            duration=data.get("duration")
        )
    elif test_type == TestType.DATA.value:
        return DataConfigurationTestDTO(
            data=data.get("data")
        )
    elif test_type == TestType.DATA_FROM_JSON_ARRAY.value:
        return DataFromJsonArrayConfigurationTestDto(
            json_array_id=data.get("json_array_id")
        )
    elif test_type == TestType.DATA_FROM_DB.value:
        return DataFromDbConfigurationTestDto(
            dataset_id=data.get("dataset_id") or data.get("data_source_id")
        )
    elif test_type == TestType.DATA_FROM_QUEUE.value:
        return DataFromQueueConfigurationTestDto(
            queue_id=data.get("queue_id"),
            retry=data.get("retry", 3),
            wait_time_seconds=data.get("wait_time_seconds", 20),
            max_messages=data.get("max_messages", 1000)
        )
    else:
        raise ValueError(f"Unsupported test type: {test_type}")
