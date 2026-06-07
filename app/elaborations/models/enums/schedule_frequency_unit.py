from enum import Enum


class ScheduleFrequencyUnit(str, Enum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
