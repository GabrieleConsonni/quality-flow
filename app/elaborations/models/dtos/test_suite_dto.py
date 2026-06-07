from __future__ import annotations

from copy import deepcopy

from pydantic import BaseModel, ConfigDict, Field, model_validator

from data_sources.services.dataset_query_service import DatasetQueryService
from elaborations.models.dtos.configuration_command_dto import ConfigurationOperationTypes
from elaborations.models.enums.hook_phase import HookPhase
from elaborations.models.enums.on_failure import OnFailure
from elaborations.models.enums.suite_item_kind import SuiteItemKind
from elaborations.models.enums.suite_item_role import SuiteItemRole
from elaborations.models.enums.template_kind import TemplateKind


def _normalize_token(value: object) -> str:
    return str(value or "").strip()


def _normalize_source_code(value: object) -> str:
    return _normalize_token(value)


def _normalize_dataset_parameter_bindings(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("parameterBindings must be an object.")
    normalized: dict[str, object] = {}
    for raw_name, raw_binding in value.items():
        parameter_name = _normalize_token(raw_name)
        if not parameter_name:
            raise ValueError("parameterBindings keys must be non-empty strings.")
        normalized[parameter_name] = deepcopy(raw_binding)
    return normalized or None


class RuntimeSourceDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceCode: str
    sourceType: str

    @model_validator(mode="after")
    def validate_common_fields(self):
        self.sourceCode = _normalize_source_code(self.sourceCode)
        self.sourceType = _normalize_token(self.sourceType)
        if not self.sourceCode:
            raise ValueError("sourceCode is required.")
        if self.sourceType not in {"dataset", "jsonArray"}:
            raise ValueError("sourceType must be one of: dataset, jsonArray.")
        return self


class JsonArraySourceDto(RuntimeSourceDto):
    sourceType: str = "jsonArray"
    jsonArrayId: str

    @model_validator(mode="after")
    def validate_json_array_source(self):
        self.jsonArrayId = _normalize_token(self.jsonArrayId)
        if not self.jsonArrayId:
            raise ValueError("jsonArrayId is required for jsonArray sources.")
        return self


class DatasetSourceDto(RuntimeSourceDto):
    sourceType: str = "dataset"
    datasetId: str
    perimeter: dict
    parameterBindings: dict | None = None
    sourceOrigin: dict | None = None

    @model_validator(mode="after")
    def validate_dataset_source(self):
        self.datasetId = _normalize_token(self.datasetId)
        if not self.datasetId:
            raise ValueError("datasetId is required for dataset sources.")
        self.perimeter = DatasetQueryService.normalize_perimeter(self.perimeter) or {}
        self.parameterBindings = _normalize_dataset_parameter_bindings(self.parameterBindings)
        self.sourceOrigin = deepcopy(self.sourceOrigin) if isinstance(self.sourceOrigin, dict) else None
        return self


SuiteSourceTypes = JsonArraySourceDto | DatasetSourceDto


class CreateSuiteItemCommandDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int
    description: str | None = ""
    cfg: ConfigurationOperationTypes | None = None


class CreateSuiteItemDto(BaseModel):
    kind: str = SuiteItemKind.TEST.value
    hook_phase: str | None = None
    description: str | None = ""
    on_failure: str | None = OnFailure.ABORT.value
    sources: list[SuiteSourceTypes] = Field(default_factory=list)
    commands: list[CreateSuiteItemCommandDto] = Field(default_factory=list)

    role: str | None = None
    template_kind: str = TemplateKind.CUSTOM.value
    template_config: dict | None = None
    data_driven: bool = False
    dataset_id: str | None = None

    @model_validator(mode="after")
    def validate_item(self):
        normalized_kind = _normalize_token(self.kind).lower() or SuiteItemKind.TEST.value
        if normalized_kind not in {item.value for item in SuiteItemKind}:
            raise ValueError(f"Unsupported suite item kind: {self.kind}")
        self.kind = normalized_kind

        normalized_hook_phase = _normalize_token(self.hook_phase).lower() or None
        self.description = str(self.description or "")
        self.on_failure = _normalize_token(self.on_failure).upper() or OnFailure.ABORT.value
        if self.on_failure not in {OnFailure.ABORT.value, OnFailure.CONTINUE.value}:
            self.on_failure = OnFailure.ABORT.value

        if self.kind == SuiteItemKind.HOOK.value:
            if normalized_hook_phase not in {phase.value for phase in HookPhase}:
                raise ValueError("hook_phase is required for hook suite items.")
            self.hook_phase = normalized_hook_phase
        else:
            self.hook_phase = None

        self.role = self._resolve_role(normalized_hook_phase)
        self.template_kind = self._normalize_template_kind()
        self._validate_data_driven()

        unique_codes: set[str] = set()
        normalized_sources: list[SuiteSourceTypes] = []
        for source in self.sources or []:
            if source.sourceCode in unique_codes:
                raise ValueError(f"Duplicate sourceCode '{source.sourceCode}' in suite item.")
            unique_codes.add(source.sourceCode)
            normalized_sources.append(source)
        self.sources = normalized_sources
        return self

    def _resolve_role(self, hook_phase: str | None) -> str:
        explicit_role = _normalize_token(self.role).lower() or None
        if explicit_role is not None:
            if explicit_role not in {r.value for r in SuiteItemRole}:
                raise ValueError(f"Unsupported suite item role: {self.role}")
            return explicit_role

        if self.kind == SuiteItemKind.HOOK.value:
            if hook_phase in (HookPhase.BEFORE_ALL.value, HookPhase.BEFORE_EACH.value):
                return SuiteItemRole.SETUP.value
            if hook_phase in (HookPhase.AFTER_EACH.value, HookPhase.AFTER_ALL.value):
                return SuiteItemRole.TEARDOWN.value
        return SuiteItemRole.TEST.value

    def _normalize_template_kind(self) -> str:
        normalized = _normalize_token(self.template_kind).lower() or TemplateKind.CUSTOM.value
        if normalized not in {t.value for t in TemplateKind}:
            raise ValueError(f"Unsupported template kind: {self.template_kind}")
        return normalized

    def _validate_data_driven(self) -> None:
        normalized_dataset_id = _normalize_token(self.dataset_id) or None
        self.dataset_id = normalized_dataset_id
        if self.data_driven and not normalized_dataset_id:
            raise ValueError("dataset_id is required when data_driven is true.")


class CreateTestSuiteDto(BaseModel):
    description: str
    tests: list[CreateSuiteItemDto] = Field(default_factory=list)
    hooks: list[CreateSuiteItemDto] = Field(default_factory=list)


class UpdateTestSuiteDto(CreateTestSuiteDto):
    id: str


class PreviewSuiteSourceDto(BaseModel):
    source: SuiteSourceTypes


class TemplatePreviewDto(BaseModel):
    """Input for POST /elaborations/templates/preview.

    `template_config` is template-specific (validated by the template
    generator itself). `data_driven` + `dataset_row` are reserved for Phase 4
    (data-driven preview row resolution) — accepted but currently ignored.
    """

    template_kind: str
    template_config: dict | None = None
    data_driven: bool = False
    dataset_row: dict | None = None

    @model_validator(mode="after")
    def validate_preview(self):
        normalized = _normalize_token(self.template_kind).lower()
        if not normalized:
            raise ValueError("template_kind is required.")
        self.template_kind = normalized
        return self


# Backward aliases during the refactor.
CreateSuiteItemOperationDto = CreateSuiteItemCommandDto
