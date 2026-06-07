from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from elaborations.models.enums.schedule_frequency_unit import ScheduleFrequencyUnit


class _BaseTestSuiteScheduleDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_suite_id: str
    description: str | None = ""
    active: bool = True
    frequency_unit: ScheduleFrequencyUnit
    frequency_value: int
    start_at: datetime | None = None
    end_at: datetime | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        self.test_suite_id = str(self.test_suite_id or "").strip()
        if not self.test_suite_id:
            raise ValueError("test_suite_id is required.")

        self.description = str(self.description or "")
        if int(self.frequency_value or 0) <= 0:
            raise ValueError("frequency_value must be greater than zero.")

        if self.start_at and self.end_at and self.start_at >= self.end_at:
            raise ValueError("start_at must be earlier than end_at.")

        return self


class CreateTestSuiteScheduleDto(_BaseTestSuiteScheduleDto):
    pass


class UpdateTestSuiteScheduleDto(_BaseTestSuiteScheduleDto):
    id: str

    @model_validator(mode="after")
    def validate_id(self):
        self.id = str(self.id or "").strip()
        if not self.id:
            raise ValueError("id is required.")
        return self
