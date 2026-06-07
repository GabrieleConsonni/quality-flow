"""Test Suites template engine (Phase 2 of the quality-flow refactor).

Public surface:
    from templating import template_registry
    template_registry.list_templates()  -> list[TemplateMeta]
    template_registry.get(template_kind) -> TemplateProtocol
    template_registry.generate_commands(template_kind, template_config) -> list[CreateSuiteItemCommandDto]
    template_registry.is_supported(template_kind) -> bool

The engine is intentionally side-effect free: it only converts a
`template_config` dict into a list of `CreateSuiteItemCommandDto` snapshots.
The actual persistence is owned by the test_suites_api layer.
"""

from templating.template_registry import (
    TemplateMeta,
    TemplateProtocol,
    UnknownTemplateError,
    InvalidTemplateConfigError,
    template_registry,
)

__all__ = [
    "TemplateMeta",
    "TemplateProtocol",
    "UnknownTemplateError",
    "InvalidTemplateConfigError",
    "template_registry",
]
