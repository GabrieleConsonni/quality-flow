from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Iterable

from elaborations.models.enums.suite_item_kind import SuiteItemKind


@dataclass
class RunContext:
    run_id: str
    run_envelope: dict[str, Any] = field(default_factory=dict)
    global_scope: dict[str, Any] = field(default_factory=dict)
    local_scope: dict[str, Any] = field(default_factory=dict)
    result_scope: dict[str, Any] = field(default_factory=dict)
    invocation_id: str | None = None
    current_item_kind: str = SuiteItemKind.HOOK.value
    current_hook_phase: str | None = None
    visible_sources: dict[str, Any] = field(default_factory=dict)
    last: dict[str, Any] = field(default_factory=lambda: {"item_id": "", "data": None})

    @property
    def event(self) -> dict[str, Any]:
        event = self.run_envelope.get("event")
        return event if isinstance(event, dict) else {}

    @property
    def global_vars(self) -> dict[str, Any]:
        constants = self.global_scope.get("constants")
        return constants if isinstance(constants, dict) else {}

    @property
    def local_vars(self) -> dict[str, Any]:
        constants = self.local_scope.get("constants")
        return constants if isinstance(constants, dict) else {}

    @property
    def artifacts(self) -> dict[str, Any]:
        artifacts = self.result_scope.get("artifacts")
        return artifacts if isinstance(artifacts, dict) else {}

    @property
    def vars(self) -> dict[str, Any]:
        return self.global_vars


def _build_run_context_payload(
    *,
    run_id: str,
    event: dict[str, Any] | None,
    initial_vars: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    run_envelope = {
        "run_id": str(run_id or "").strip(),
        "event": event if isinstance(event, dict) else {},
        "constants": initial_vars if isinstance(initial_vars, dict) else {},
    }
    global_scope = {
        "runEnvelope": run_envelope,
        "constants": {},
    }
    local_scope = {
        "global": global_scope,
        "constants": {},
    }
    result_scope = {
        "artifacts": {},
        "commands": {},
        "constants": {},
    }
    return run_envelope, global_scope, local_scope, result_scope


_RUN_CONTEXT: ContextVar[RunContext | None] = ContextVar("run_context", default=None)


def create_run_context(
    *,
    run_id: str,
    event: dict[str, Any] | None = None,
    initial_vars: dict[str, Any] | None = None,
    invocation_id: str | None = None,
) -> RunContext:
    run_envelope, global_scope, local_scope, result_scope = _build_run_context_payload(
        run_id=run_id,
        event=event,
        initial_vars=initial_vars,
    )
    return RunContext(
        run_id=str(run_id or "").strip(),
        run_envelope=run_envelope,
        global_scope=global_scope,
        local_scope=local_scope,
        result_scope=result_scope,
        invocation_id=str(invocation_id or "").strip() or None,
    )


def get_run_context() -> RunContext | None:
    return _RUN_CONTEXT.get()


@contextmanager
def bind_run_context(run_context: RunContext):
    token: Token = _RUN_CONTEXT.set(run_context)
    try:
        yield run_context
    finally:
        _RUN_CONTEXT.reset(token)


@contextmanager
def bind_suite_item_context(
    *,
    item_kind: str,
    hook_phase: str | None = None,
    local_vars: dict[str, Any] | None = None,
    visible_sources: dict[str, Any] | None = None,
):
    context = get_run_context()
    if context is None:
        yield None
        return

    previous_kind = context.current_item_kind
    previous_hook_phase = context.current_hook_phase
    previous_local_vars = context.local_scope.get("constants")
    previous_sources = context.visible_sources
    try:
        context.current_item_kind = str(item_kind or previous_kind).strip().lower()
        context.current_hook_phase = str(hook_phase or "").strip().lower() or None
        if local_vars is not None:
            context.local_scope["constants"] = local_vars
        if visible_sources is not None:
            context.visible_sources = visible_sources
        yield context
    finally:
        context.current_item_kind = previous_kind
        context.current_hook_phase = previous_hook_phase
        context.local_scope["constants"] = previous_local_vars if isinstance(previous_local_vars, dict) else {}
        context.visible_sources = previous_sources if isinstance(previous_sources, dict) else {}


def reset_local_context():
    context = get_run_context()
    if context is None:
        return
    context.local_scope["constants"] = {}
    context.last = {"item_id": "", "data": None}


def set_context_last(item_id: str, data: Any):
    context = get_run_context()
    if context is None:
        return
    context.last = {
        "item_id": str(item_id or "").strip(),
        "data": data,
    }


def set_context_var(key: str, value: Any, scope: str = "local"):
    context = get_run_context()
    if context is None:
        return
    normalized_key = str(key or "").strip()
    if not normalized_key:
        raise ValueError("Context variable key is required.")
    normalized_scope = str(scope or "local").strip()
    if normalized_scope == "auto":
        normalized_scope = (
            "local"
            if context.current_item_kind == SuiteItemKind.TEST.value
            else "global"
        )
    write_context_path(f"$.{normalized_scope}.constants.{normalized_key}", value)


def append_assert_artifact(artifact: dict[str, Any]):
    context = get_run_context()
    if context is None:
        return
    artifacts = context.result_scope.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}
        context.result_scope["artifacts"] = artifacts
    assert_items = artifacts.get("asserts")
    if not isinstance(assert_items, list):
        assert_items = []
        artifacts["asserts"] = assert_items
    assert_items.append(artifact)


def _normalize_target_path(path: str) -> str:
    normalized = str(path or "").strip()
    if not normalized:
        raise ValueError("Target path is required.")
    if normalized.startswith("$."):
        return normalized[2:]
    if normalized.startswith("$"):
        normalized = normalized[1:]
        if normalized.startswith("."):
            normalized = normalized[1:]
    return normalized


def _segment_tokens(segment: str) -> list[str]:
    source = str(segment or "").strip()
    if not source:
        return []
    result: list[str] = []
    buffer: list[str] = []
    index_mode = False
    for char in source:
        if char == "[":
            if buffer:
                result.append("".join(buffer))
                buffer = []
            index_mode = True
            continue
        if char == "]":
            token = "".join(buffer).strip()
            if token:
                result.append(token)
            buffer = []
            index_mode = False
            continue
        buffer.append(char)
    if buffer:
        result.append("".join(buffer) if not index_mode else "".join(buffer).strip())
    return [token for token in result if token]


def _path_tokens(path: str) -> list[str]:
    normalized = _normalize_target_path(path)
    parts = [part for part in normalized.split(".") if part]
    tokens: list[str] = []
    for part in parts:
        tokens.extend(_segment_tokens(part))
    return tokens


def extract_context_root(path: str) -> str | None:
    tokens = _path_tokens(path)
    if not tokens:
        return None
    root = str(tokens[0] or "").strip()
    if root == "vars":
        return "global"
    if root == "response":
        return "response"
    if root in {"runEnvelope", "global", "local", "result"}:
        return root
    return None


def _target_from_root(context: RunContext, root: str):
    if root == "runEnvelope":
        return context.run_envelope
    if root == "global":
        return context.global_scope
    if root == "local":
        return context.local_scope
    if root == "result":
        return context.result_scope
    if root == "response":
        commands = context.result_scope.get("commands")
        if not isinstance(commands, dict):
            commands = {}
            context.result_scope["commands"] = commands
        return commands
    raise ValueError(f"Unsupported context root '{root}'.")


def _to_index(token: str) -> int | None:
    raw = str(token or "").strip()
    if raw.isdigit():
        return int(raw)
    return None


def _ensure_list_size(items: list[Any], idx: int):
    while len(items) <= idx:
        items.append({})


def _assign_nested_value(target: Any, tokens: Iterable[str], value: Any):
    path_tokens = list(tokens)
    if not path_tokens:
        raise ValueError("Target path must include at least one segment.")

    current = target
    for idx, token in enumerate(path_tokens):
        is_last = idx == len(path_tokens) - 1
        list_index = _to_index(token)

        if list_index is not None:
            if not isinstance(current, list):
                raise ValueError("Target path expects a list segment.")
            _ensure_list_size(current, list_index)
            if is_last:
                current[list_index] = value
                return
            next_token = path_tokens[idx + 1]
            next_is_index = _to_index(next_token) is not None
            if current[list_index] is None:
                current[list_index] = [] if next_is_index else {}
            current = current[list_index]
            continue

        if not isinstance(current, dict):
            raise ValueError("Target path expects an object segment.")
        if is_last:
            current[token] = value
            return
        next_token = path_tokens[idx + 1]
        next_is_index = _to_index(next_token) is not None
        next_value = current.get(token)
        if next_value is None:
            current[token] = [] if next_is_index else {}
            next_value = current[token]
        current = next_value


def _remove_nested_value(target: Any, tokens: Iterable[str]):
    path_tokens = list(tokens)
    if not path_tokens:
        return
    current = target
    for idx, token in enumerate(path_tokens):
        is_last = idx == len(path_tokens) - 1
        list_index = _to_index(token)
        if list_index is not None:
            if not isinstance(current, list) or list_index >= len(current):
                return
            if is_last:
                current.pop(list_index)
                return
            current = current[list_index]
            continue
        if not isinstance(current, dict) or token not in current:
            return
        if is_last:
            current.pop(token, None)
            return
        current = current[token]


def write_context_path(path: str, value: Any):
    context = get_run_context()
    if context is None:
        return

    root = extract_context_root(path)
    if root is None:
        raise ValueError("Unsupported target path. Use $.runEnvelope, $.global, $.local or $.result.")
    if root == "global" and context.current_item_kind == SuiteItemKind.TEST.value:
        raise ValueError("Global context is immutable during test execution.")
    if root == "runEnvelope" and context.current_item_kind == SuiteItemKind.TEST.value:
        raise ValueError("RunEnvelope context is immutable during test execution.")

    tokens = _path_tokens(path)
    if tokens and tokens[0] == "vars":
        tokens[0] = "global"
    target_tokens = tokens[1:]
    if root in {"runEnvelope", "global", "local"} and target_tokens:
        if target_tokens[0] not in {"constants", "event", "run_id", "runEnvelope", "global"}:
            target_tokens = ["constants", *target_tokens]
    target = _target_from_root(context, root)
    if not target_tokens:
        if not isinstance(value, dict):
            raise ValueError("Root assignment requires a JSON object value.")
        target.clear()
        target.update(value)
        return
    _assign_nested_value(target, target_tokens, value)


def remove_context_path(path: str):
    context = get_run_context()
    if context is None:
        return
    root = extract_context_root(path)
    if root is None:
        return
    if root == "global" and context.current_item_kind == SuiteItemKind.TEST.value:
        raise ValueError("Global context is immutable during test execution.")
    if root == "runEnvelope" and context.current_item_kind == SuiteItemKind.TEST.value:
        raise ValueError("RunEnvelope context is immutable during test execution.")
    tokens = _path_tokens(path)
    if tokens and tokens[0] == "vars":
        tokens[0] = "global"
    target_tokens = tokens[1:]
    if root in {"runEnvelope", "global", "local"} and target_tokens:
        if target_tokens[0] not in {"constants", "event", "run_id", "runEnvelope", "global"}:
            target_tokens = ["constants", *target_tokens]
    target = _target_from_root(context, root)
    _remove_nested_value(target, target_tokens)


def resolve_constant_value(name: str) -> Any:
    context = get_run_context()
    if context is None:
        return None
    normalized_name = str(name or "").strip()
    if not normalized_name:
        return None
    for container in (
        context.local_vars,
        context.global_vars,
        context.run_envelope.get("constants") if isinstance(context.run_envelope.get("constants"), dict) else {},
        context.result_scope.get("constants") if isinstance(context.result_scope.get("constants"), dict) else {},
    ):
        if normalized_name in container:
            return container[normalized_name]
    return None


def build_run_context_scope(run_context: RunContext | None = None) -> dict[str, Any]:
    context = run_context or get_run_context()
    if context is None:
        return {
            "runEnvelope": {"run_id": "", "event": {}, "constants": {}},
            "global": {"runEnvelope": {"run_id": "", "event": {}, "constants": {}}, "constants": {}},
            "local": {"global": {"runEnvelope": {"run_id": "", "event": {}, "constants": {}}, "constants": {}}, "constants": {}},
            "result": {"artifacts": {}, "commands": {}, "constants": {}},
            "response": {},
        }
    return {
        "runEnvelope": context.run_envelope,
        "global": context.global_scope,
        "local": context.local_scope,
        "result": context.result_scope,
        "vars": context.global_vars,
        "response": context.result_scope.get("commands") if isinstance(context.result_scope.get("commands"), dict) else {},
    }


def serialize_run_context(run_context: RunContext) -> dict[str, Any]:
    return {
        "run_id": str(run_context.run_id or "").strip(),
        "runEnvelope": run_context.run_envelope,
        "global": run_context.global_scope,
        "local": run_context.local_scope,
        "result": run_context.result_scope,
        "invocation_id": str(run_context.invocation_id or "").strip() or None,
        "visible_sources": run_context.visible_sources,
        "last": run_context.last,
    }


def deserialize_run_context(payload: dict[str, Any] | None) -> RunContext:
    source = payload if isinstance(payload, dict) else {}
    run_envelope = source.get("runEnvelope") if isinstance(source.get("runEnvelope"), dict) else {}
    initial_vars = run_envelope.get("constants") if isinstance(run_envelope.get("constants"), dict) else {}
    context = create_run_context(
        run_id=str(source.get("run_id") or run_envelope.get("run_id") or "").strip(),
        event=run_envelope.get("event") if isinstance(run_envelope.get("event"), dict) else {},
        initial_vars=initial_vars,
        invocation_id=str(source.get("invocation_id") or "").strip() or None,
    )
    global_payload = source.get("global") if isinstance(source.get("global"), dict) else {}
    local_payload = source.get("local") if isinstance(source.get("local"), dict) else {}
    result_payload = source.get("result") if isinstance(source.get("result"), dict) else {}
    context.global_scope["constants"] = (
        global_payload.get("constants") if isinstance(global_payload.get("constants"), dict) else {}
    )
    context.local_scope["constants"] = (
        local_payload.get("constants") if isinstance(local_payload.get("constants"), dict) else {}
    )
    context.result_scope = result_payload or {"artifacts": {}, "commands": {}, "constants": {}}
    context.visible_sources = source.get("visible_sources") if isinstance(source.get("visible_sources"), dict) else {}
    context.last = source.get("last") if isinstance(source.get("last"), dict) else {"item_id": "", "data": None}
    return context
