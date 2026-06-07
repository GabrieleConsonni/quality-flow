"""Unit tests for the qsm_047 fields on CreateSuiteItemDto:
role, template_kind, template_config, data_driven, dataset_id."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.elaborations.models.dtos.test_suite_dto import CreateSuiteItemDto
from app.elaborations.models.enums.suite_item_role import SuiteItemRole
from app.elaborations.models.enums.template_kind import TemplateKind


def test_test_kind_defaults_to_test_role_and_custom_template():
    dto = CreateSuiteItemDto(kind="test", description="t1", commands=[])
    assert dto.role == SuiteItemRole.TEST.value
    assert dto.template_kind == TemplateKind.CUSTOM.value
    assert dto.template_config is None
    assert dto.data_driven is False
    assert dto.dataset_id is None


def test_hook_before_phases_derive_setup_role():
    for phase in ("before-all", "before-each"):
        dto = CreateSuiteItemDto(
            kind="hook",
            hook_phase=phase,
            description=f"hook {phase}",
            commands=[],
        )
        assert dto.role == SuiteItemRole.SETUP.value, phase


def test_hook_after_phases_derive_teardown_role():
    for phase in ("after-each", "after-all"):
        dto = CreateSuiteItemDto(
            kind="hook",
            hook_phase=phase,
            description=f"hook {phase}",
            commands=[],
        )
        assert dto.role == SuiteItemRole.TEARDOWN.value, phase


def test_explicit_role_overrides_kind_inference():
    dto = CreateSuiteItemDto(
        kind="test",
        description="explicit",
        role="setup",
        commands=[],
    )
    assert dto.role == SuiteItemRole.SETUP.value


def test_unknown_role_is_rejected():
    with pytest.raises(ValidationError):
        CreateSuiteItemDto(kind="test", description="bad", role="nope", commands=[])


def test_unknown_template_kind_is_rejected():
    with pytest.raises(ValidationError):
        CreateSuiteItemDto(
            kind="test", description="bad", template_kind="not_a_template", commands=[]
        )


def test_data_driven_without_dataset_id_is_rejected():
    with pytest.raises(ValidationError) as excinfo:
        CreateSuiteItemDto(
            kind="test",
            description="dd",
            data_driven=True,
            dataset_id=None,
            commands=[],
        )
    assert "dataset_id is required" in str(excinfo.value)


def test_data_driven_with_dataset_id_is_accepted():
    dto = CreateSuiteItemDto(
        kind="test",
        description="dd",
        data_driven=True,
        dataset_id="json-array-uuid",
        commands=[],
    )
    assert dto.data_driven is True
    assert dto.dataset_id == "json-array-uuid"


def test_template_config_is_passed_through_when_dict():
    cfg = {"queue_id": "q-1", "wait_ms": 500}
    dto = CreateSuiteItemDto(
        kind="test",
        description="tc",
        template_kind="send_verify",
        template_config=cfg,
        commands=[],
    )
    assert dto.template_kind == TemplateKind.SEND_VERIFY.value
    assert dto.template_config == cfg
