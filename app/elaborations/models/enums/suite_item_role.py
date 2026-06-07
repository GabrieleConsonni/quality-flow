from enum import Enum


class SuiteItemRole(str, Enum):
    """Refactor-era role of a suite_item.

    Replaces the legacy combination of `SuiteItemKind` + `HookPhase` for new
    code paths. The collapse-4-to-2 migration (qsm_046) maps:
        kind='hook' + hook_phase IN (before-all, before-each) -> SETUP
        kind='hook' + hook_phase IN (after-each,  after-all)  -> TEARDOWN
        kind='test'                                           -> TEST
    """

    TEST = "test"
    SETUP = "setup"
    TEARDOWN = "teardown"
