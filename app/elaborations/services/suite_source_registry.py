from __future__ import annotations

from typing import Iterable

from _alembic.models.suite_item_entity import SuiteItemEntity
from elaborations.models.dtos.configuration_command_dto import convert_to_config_command_type
from elaborations.models.dtos.test_suite_dto import CreateSuiteItemDto, CreateTestSuiteDto
from elaborations.models.enums.hook_phase import HookPhase
from elaborations.models.enums.suite_item_kind import SuiteItemKind


_SOURCE_TYPE_COMPATIBILITY: dict[str, set[str]] = {
    "sendMessageQueue": {"dataset", "jsonArray"},
    "saveTable": {"dataset", "jsonArray"},
    "exportDataset": {"dataset", "jsonArray"},
    "jsonArrayEquals": {"jsonArray"},
    "jsonArrayEmpty": {"jsonArray"},
    "jsonArrayNotEmpty": {"jsonArray"},
    "jsonArrayContains": {"jsonArray"},
}


def _section_type_for_item(item: CreateSuiteItemDto | SuiteItemEntity) -> str:
    kind = str(getattr(item, "kind", "") or "").strip().lower()
    if kind != SuiteItemKind.HOOK.value:
        return "test"
    hook_phase = str(getattr(item, "hook_phase", "") or "").strip().lower()
    mapping = {
        HookPhase.BEFORE_ALL.value: "beforeAll",
        HookPhase.BEFORE_EACH.value: "beforeEach",
        HookPhase.AFTER_EACH.value: "afterEach",
        HookPhase.AFTER_ALL.value: "afterAll",
    }
    return mapping.get(hook_phase, "test")


def _source_dicts(item: CreateSuiteItemDto | SuiteItemEntity | None) -> list[dict]:
    if item is None:
        return []
    if isinstance(item, SuiteItemEntity):
        sources = item.sources_json if isinstance(item.sources_json, list) else []
        return [source for source in sources if isinstance(source, dict)]
    sources = item.sources if isinstance(getattr(item, "sources", None), list) else []
    result: list[dict] = []
    for source in sources:
        if hasattr(source, "model_dump"):
            result.append(source.model_dump())
        elif isinstance(source, dict):
            result.append(dict(source))
    return result


def _add_sources(target: dict[str, dict], sources: Iterable[dict], *, owner: str) -> None:
    for source in sources:
        source_code = str(source.get("sourceCode") or "").strip()
        if not source_code:
            continue
        if source_code in target:
            raise ValueError(f"Source '{source_code}' is visible from multiple sections ({owner}).")
        target[source_code] = source


def build_visible_sources_for_suite_item(
    *,
    before_all: CreateSuiteItemDto | SuiteItemEntity | None,
    before_each: CreateSuiteItemDto | SuiteItemEntity | None,
    current_item: CreateSuiteItemDto | SuiteItemEntity,
) -> dict[str, dict]:
    section_type = _section_type_for_item(current_item)
    visible: dict[str, dict] = {}
    if section_type in {"beforeEach", "test", "afterAll"}:
        _add_sources(visible, _source_dicts(before_all), owner="beforeAll")
    if section_type in {"test", "afterEach"}:
        _add_sources(visible, _source_dicts(before_each), owner="beforeEach")
    _add_sources(visible, _source_dicts(current_item), owner=section_type)
    return visible


def validate_suite_sources_graph(dto: CreateTestSuiteDto) -> None:
    hooks_by_phase = {
        str(item.hook_phase or "").strip(): item
        for item in dto.hooks or []
    }
    before_all = hooks_by_phase.get(HookPhase.BEFORE_ALL.value)
    before_each = hooks_by_phase.get(HookPhase.BEFORE_EACH.value)

    all_items: list[CreateSuiteItemDto] = [item for item in dto.hooks or []] + [item for item in dto.tests or []]
    for item in all_items:
        visible_sources = build_visible_sources_for_suite_item(
            before_all=before_all,
            before_each=before_each,
            current_item=item,
        )
        commands = item.commands if isinstance(item.commands, list) else []
        for command in commands:
            cfg = convert_to_config_command_type(command.cfg.model_dump() if hasattr(command.cfg, "model_dump") else {})
            input_ref = getattr(cfg, "inputRef", None)
            if input_ref is not None and str(getattr(input_ref, "kind", "")) == "source":
                source = visible_sources.get(str(input_ref.sourceCode or "").strip())
                if source is None:
                    raise ValueError(
                        f"Source '{input_ref.sourceCode}' is not visible for command '{cfg.commandCode}'."
                    )
                compatible = _SOURCE_TYPE_COMPATIBILITY.get(str(cfg.commandCode or "").strip())
                source_type = str(source.get("sourceType") or "").strip()
                if compatible and source_type not in compatible:
                    raise ValueError(
                        f"Source '{input_ref.sourceCode}' has incompatible type '{source_type}' for command '{cfg.commandCode}'."
                    )
            actual_ref = getattr(cfg, "actualRef", None)
            if actual_ref is not None and str(getattr(actual_ref, "kind", "")) == "source":
                source = visible_sources.get(str(actual_ref.sourceCode or "").strip())
                if source is None:
                    raise ValueError(
                        f"Source '{actual_ref.sourceCode}' is not visible for command '{cfg.commandCode}'."
                    )
            expected_ref = getattr(cfg, "expectedRef", None)
            if expected_ref is not None and str(getattr(expected_ref, "kind", "")) == "source":
                source = visible_sources.get(str(expected_ref.sourceCode or "").strip())
                if source is None:
                    raise ValueError(
                        f"Source '{expected_ref.sourceCode}' is not visible for command '{cfg.commandCode}'."
                    )
                compatible = _SOURCE_TYPE_COMPATIBILITY.get(str(cfg.commandCode or "").strip())
                source_type = str(source.get("sourceType") or "").strip()
                if compatible and source_type not in compatible:
                    raise ValueError(
                        f"Source '{expected_ref.sourceCode}' has incompatible type '{source_type}' for command '{cfg.commandCode}'."
                    )
