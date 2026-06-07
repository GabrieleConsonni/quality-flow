from enum import Enum


class SuiteItemKind(str, Enum):
    TEST = "test"
    HOOK = "hook"
