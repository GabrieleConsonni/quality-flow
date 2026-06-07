from enum import Enum


class HookPhase(str, Enum):
    BEFORE_ALL = "before-all"
    BEFORE_EACH = "before-each"
    AFTER_EACH = "after-each"
    AFTER_ALL = "after-all"
