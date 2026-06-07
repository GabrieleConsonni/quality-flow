from enum import Enum

class OperationType(str,Enum):
    DATA = "data"
    DATA_FROM_JSON_ARRAY = "data-from-json-array"
    DATA_FROM_DB = "data-from-db"
    DATA_FROM_QUEUE = "data-from-queue"
    SLEEP = "sleep"
    PUBLISH = "publish"
    SAVE_INTERNAL_DB = "save-internal-db"
    SAVE_EXTERNAL_DB = "save-external-db"
    ASSERT = "assert"
    RUN_SUITE = "run-suite"
    SET_VAR = "set-var"
    SET_RESPONSE_STATUS = "set-response-status"
    SET_RESPONSE_HEADER = "set-response-header"
    SET_RESPONSE_BODY = "set-response-body"
    BUILD_RESPONSE_FROM_TEMPLATE = "build-response-from-template"
