import datetime
from abc import abstractmethod, ABC

from sqlalchemy import (Integer, Float, String, Boolean,
                        Date, DateTime, JSON
                        )


class ColumnTypeExtractor(ABC):
    @abstractmethod
    def can_extract(self,column):
        pass
    @abstractmethod
    def get_column_type(self):
        pass


class DatetimeColumnTypeExtractor(ColumnTypeExtractor):
    def can_extract(self, value):
        return isinstance(value, datetime.datetime)
    def get_column_type(self):
            return DateTime()

class DateColumnTypeExtractor(ColumnTypeExtractor):
    def can_extract(self, value):
        return isinstance(value, datetime.date)
    def get_column_type(self):
            return Date()

class BooleanColumnTypeExtractor(ColumnTypeExtractor):
    def can_extract(self, value):
        return isinstance(value, bool)
    def get_column_type(self):
            return Boolean()

class IntegerColumnTypeExtractor(ColumnTypeExtractor):
    def can_extract(self, value):
        return isinstance(value, int)
    def get_column_type(self):
            return Integer()

class FloatColumnTypeExtractor(ColumnTypeExtractor):
    def can_extract(self, value):
        return isinstance(value, float)
    def get_column_type(self):
            return Float()

class JsonColumnTypeExtractor(ColumnTypeExtractor):
    def can_extract(self, value):
        return isinstance(value, (list, dict))
    def get_column_type(self):
            return JSON

class StringColumnTypeExtractor(ColumnTypeExtractor):
    def can_extract(self, value):
        return isinstance(value, str)
    def get_column_type(self):
            return String(1024)

class FallbackColumnTypeExtractor(ColumnTypeExtractor):
    def can_extract(self, value):
        return True
    def get_column_type(self):
            return String(1024)  # fallback

COLUMN_TYPE_EXTRACTORS: list[ColumnTypeExtractor] = [
    DatetimeColumnTypeExtractor(),
    DateColumnTypeExtractor(),
    BooleanColumnTypeExtractor(),
    IntegerColumnTypeExtractor(),
    FloatColumnTypeExtractor(),
    JsonColumnTypeExtractor(),
    StringColumnTypeExtractor(),
    FallbackColumnTypeExtractor()
]

def extract_column_type(value):
    for extractor in COLUMN_TYPE_EXTRACTORS:
        if extractor.can_extract(value):
            return extractor.get_column_type()
    return String(1024)  # fallback
