"""Unit tests for the template_registry singleton."""

from __future__ import annotations

import pytest

from app.elaborations.models.enums.template_kind import TemplateKind
from app.templating import (
    InvalidTemplateConfigError,
    UnknownTemplateError,
    template_registry,
)


def test_registry_lists_send_verify_and_mock_assert():
    kinds = {meta.kind for meta in template_registry.list_templates()}
    assert kinds == {TemplateKind.SEND_VERIFY.value, TemplateKind.MOCK_ASSERT.value}


def test_registry_does_not_register_custom():
    assert not template_registry.is_supported(TemplateKind.CUSTOM.value)


def test_get_returns_send_verify_template():
    template = template_registry.get(TemplateKind.SEND_VERIFY.value)
    assert template.meta.kind == TemplateKind.SEND_VERIFY.value
    assert template.meta.name == "Send & Verify"


def test_get_unknown_kind_raises():
    with pytest.raises(UnknownTemplateError):
        template_registry.get("unknown_template_kind")


def test_generate_commands_unknown_kind_raises():
    with pytest.raises(UnknownTemplateError):
        template_registry.generate_commands("unknown_template_kind", {})


def test_generate_commands_invalid_config_raises():
    # send_verify requires `queue_id` + `payload`.
    with pytest.raises(InvalidTemplateConfigError):
        template_registry.generate_commands(TemplateKind.SEND_VERIFY.value, {})
