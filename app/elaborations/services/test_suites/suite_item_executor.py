from sqlalchemy.orm import Session

from _alembic.models.suite_item_entity import SuiteItemEntity
from elaborations.models.enums.hook_phase import HookPhase
from elaborations.models.enums.suite_item_kind import SuiteItemKind
from elaborations.services.alembic.suite_item_command_service import (
    SuiteItemOperationService,
)
from elaborations.services.operations.command_executor_composite import execute_operations
from elaborations.services.operations.command_scope import (
    SCOPE_HOOK_AFTER_ALL,
    SCOPE_HOOK_AFTER_EACH,
    SCOPE_HOOK_BEFORE_ALL,
    SCOPE_HOOK_BEFORE_EACH,
    SCOPE_TEST,
)
from elaborations.services.suite_runs.execution_runtime_context import bind_execution_context
from elaborations.services.suite_runs.run_context import set_context_last


def _resolve_suite_item_scope(suite_item: SuiteItemEntity) -> str | None:
    kind = str(suite_item.kind or "").strip().lower()
    if kind == SuiteItemKind.TEST.value:
        return SCOPE_TEST
    hook_phase = str(suite_item.hook_phase or "").strip().lower()
    if hook_phase == HookPhase.BEFORE_ALL.value:
        return SCOPE_HOOK_BEFORE_ALL
    if hook_phase == HookPhase.BEFORE_EACH.value:
        return SCOPE_HOOK_BEFORE_EACH
    if hook_phase == HookPhase.AFTER_EACH.value:
        return SCOPE_HOOK_AFTER_EACH
    if hook_phase == HookPhase.AFTER_ALL.value:
        return SCOPE_HOOK_AFTER_ALL
    return None


def execute_suite_item(session: Session, suite_item: SuiteItemEntity) -> list[dict[str, object]]:
    operations = SuiteItemOperationService().get_all_by_suite_item_id(session, suite_item.id)
    execution_scope = _resolve_suite_item_scope(suite_item)
    with bind_execution_context(suite_item_id=suite_item.id):
        execution_result = execute_operations(
            session,
            operations,
            [],
            execution_scope=execution_scope,
        )
    set_context_last(str(suite_item.id or ""), execution_result.data)
    return execution_result.result

