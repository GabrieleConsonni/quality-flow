from typing import Any

from elaborations.services.operations.command_contract_registry import (
    OperationContract,
    get_operation_contract,
)
from elaborations.services.operations.command_scope import (
    SCOPE_MOCK_PRE_RESPONSE,
    SCOPE_TEST,
)
from elaborations.services.suite_runs.run_context import extract_context_root


def _collect_target_paths(cfg: Any) -> list[str]:
    targets: list[str] = []
    target = getattr(cfg, "target", None)
    if isinstance(target, str) and target.strip():
        targets.append(target)
    context = getattr(cfg, "context", None)
    name = getattr(cfg, "name", None)
    if isinstance(context, str) and context.strip() and isinstance(name, str) and name.strip():
        targets.append(f"$.{context}.constants.{name}")
    result_target = getattr(cfg, "result_target", None)
    if isinstance(result_target, str) and result_target.strip():
        targets.append(result_target)
    result_constant = getattr(cfg, "resultConstant", None)
    if result_constant is not None and getattr(result_constant, "name", None):
        targets.append(f"$.result.constants.{result_constant.name}")
    return targets


def _validate_scope_rules(contract: OperationContract, execution_scope: str | None):
    if not execution_scope:
        return
    if execution_scope not in contract.supported_scopes:
        raise ValueError(
            f"Operation '{contract.name}' is not allowed in scope '{execution_scope}'."
        )
    if execution_scope == SCOPE_MOCK_PRE_RESPONSE:
        if contract.side_effects:
            raise ValueError(
                f"Operation '{contract.name}' has side effects and cannot run in mock.preResponse."
            )
        if contract.async_allowed:
            raise ValueError(
                f"Operation '{contract.name}' is async-enabled and cannot run in mock.preResponse."
            )


def _validate_target_roots(targets: list[str], execution_scope: str | None):
    for target in targets:
        root = extract_context_root(target)
        if root is None:
            raise ValueError(
                f"Unsupported target path '{target}'. Use $.runEnvelope, $.global, $.local or $.result."
            )
        if execution_scope == SCOPE_TEST and root == "global":
            raise ValueError("Global context is immutable during test execution.")
        if execution_scope == SCOPE_TEST and root == "runEnvelope":
            raise ValueError("RunEnvelope context is immutable during test execution.")


def validate_operation_policy(cfg: Any, execution_scope: str | None) -> OperationContract:
    command_code = str(getattr(cfg, "commandCode", "") or "").strip()
    contract = get_operation_contract(command_code)
    if contract is None:
        raise ValueError(f"No command contract found for commandCode '{command_code}'.")
    _validate_scope_rules(contract, execution_scope)
    _validate_target_roots(_collect_target_paths(cfg), execution_scope)
    return contract

