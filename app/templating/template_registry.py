"""Template registry singleton.

Keeps the catalogue of `TemplateProtocol` implementations and exposes the two
operations the API layer uses:

    template_registry.list_templates()                 -> list[TemplateMeta]
    template_registry.generate_commands(kind, config)  -> list[CreateSuiteItemCommandDto]

The `custom` template_kind is intentionally NOT registered here: by contract
its commands come from the user (no generation), so the API layer must
short-circuit before calling the registry when `template_kind == 'custom'`.
"""

from __future__ import annotations

from typing import Dict

from elaborations.models.dtos.test_suite_dto import CreateSuiteItemCommandDto
from elaborations.models.enums.template_kind import TemplateKind
from templating.base import (
    InvalidTemplateConfigError,
    TemplateMeta,
    TemplateProtocol,
    UnknownTemplateError,
)


class _TemplateRegistry:
    def __init__(self) -> None:
        self._templates: Dict[str, TemplateProtocol] = {}

    def register(self, template: TemplateProtocol) -> None:
        kind = template.meta.kind
        if kind in self._templates:
            raise RuntimeError(f"Template kind '{kind}' already registered.")
        if kind == TemplateKind.CUSTOM.value:
            raise RuntimeError(
                "The 'custom' template_kind must not be registered: "
                "its commands come from the user, not the engine."
            )
        if kind not in {t.value for t in TemplateKind}:
            raise RuntimeError(
                f"Template kind '{kind}' is not declared in TemplateKind enum."
            )
        self._templates[kind] = template

    def is_supported(self, template_kind: str) -> bool:
        return template_kind in self._templates

    def get(self, template_kind: str) -> TemplateProtocol:
        try:
            return self._templates[template_kind]
        except KeyError as exc:
            raise UnknownTemplateError(
                f"No template engine registered for kind '{template_kind}'."
            ) from exc

    def list_templates(self) -> list[TemplateMeta]:
        return [self._templates[kind].meta for kind in sorted(self._templates)]

    def generate_commands(
        self, template_kind: str, template_config: dict | None
    ) -> list[CreateSuiteItemCommandDto]:
        template = self.get(template_kind)
        config = template_config if isinstance(template_config, dict) else {}
        return template.generate_commands(config)


template_registry = _TemplateRegistry()


def _bootstrap_default_templates() -> None:
    """Import the built-in template modules so their module-level
    `template_registry.register(...)` side effects run.

    Kept as a module-level call so any caller that imports the registry
    (or the API layer) immediately sees the templates without an explicit
    bootstrap step.
    """
    # Late imports break the import cycle: each template module imports the
    # registry to register itself.
    from templating.templates import mock_assert as _mock_assert  # noqa: F401
    from templating.templates import send_verify as _send_verify  # noqa: F401


_bootstrap_default_templates()


__all__ = [
    "InvalidTemplateConfigError",
    "TemplateMeta",
    "TemplateProtocol",
    "UnknownTemplateError",
    "template_registry",
]
