from elaborations.models.enums.hook_phase import HookPhase
from elaborations.models.enums.suite_item_kind import SuiteItemKind
from elaborations.services.suite_runs.run_context import get_run_context


SCOPE_TEST = "test"
SCOPE_HOOK_BEFORE_ALL = "hook.beforeAll"
SCOPE_HOOK_BEFORE_EACH = "hook.beforeEach"
SCOPE_HOOK_AFTER_EACH = "hook.afterEach"
SCOPE_HOOK_AFTER_ALL = "hook.afterAll"
SCOPE_MOCK_PRE_RESPONSE = "mock.preResponse"
SCOPE_MOCK_RESPONSE = "mock.response"
SCOPE_MOCK_POST_RESPONSE = "mock.postResponse"

_HOOK_PHASE_TO_SCOPE: dict[str, str] = {
    HookPhase.BEFORE_ALL.value: SCOPE_HOOK_BEFORE_ALL,
    HookPhase.BEFORE_EACH.value: SCOPE_HOOK_BEFORE_EACH,
    HookPhase.AFTER_EACH.value: SCOPE_HOOK_AFTER_EACH,
    HookPhase.AFTER_ALL.value: SCOPE_HOOK_AFTER_ALL,
}


def normalize_scope(scope: str | None) -> str | None:
    normalized = str(scope or "").strip()
    if not normalized:
        return None
    return normalized


def resolve_execution_scope(explicit_scope: str | None = None) -> str | None:
    normalized_explicit_scope = normalize_scope(explicit_scope)
    if normalized_explicit_scope:
        return normalized_explicit_scope

    run_context = get_run_context()
    if run_context is None:
        return None

    item_kind = str(run_context.current_item_kind or "").strip().lower()
    if item_kind == SuiteItemKind.TEST.value:
        return SCOPE_TEST
    if item_kind == SuiteItemKind.HOOK.value:
        hook_phase = str(run_context.current_hook_phase or "").strip().lower()
        return _HOOK_PHASE_TO_SCOPE.get(hook_phase)
    return None
