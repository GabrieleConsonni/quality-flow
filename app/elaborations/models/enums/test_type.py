from enum import Enum


class TestType(str,Enum):
    __test__ = False

    SLEEP = "sleep"
    DATA_FROM_JSON_ARRAY = "data-from-json-array"
    DATA = "data"
    DATA_FROM_DB = "data-from-db"
    DATA_FROM_QUEUE = "data-from-queue"
