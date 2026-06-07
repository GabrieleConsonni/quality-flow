"""Base contracts of the template engine.

`TemplateProtocol` is the duck-typed interface every template implementation
must satisfy. `TemplateMeta` carries the static metadata returned by
`GET /elaborations/templates` so the FE can render the New Test dialog
without hard-coding the list of templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from elaborations.models.dtos.test_suite_dto import CreateSuiteItemCommandDto


class UnknownTemplateError(LookupError):
    """Raised when a `template_kind` is not registered in the engine."""


class InvalidTemplateConfigError(ValueError):
    """Raised when a `template_config` fails template-specific validation."""


@dataclass(frozen=True)
class TemplateMeta:
    """Static metadata for a template. Serialized as-is in
    `GET /elaborations/templates` responses."""

    kind: str
    name: str
    description: str
    config_schema_summary: dict = field(default_factory=dict)


@runtime_checkable
class TemplateProtocol(Protocol):
    """Contract every template implementation must satisfy.

    `generate_commands` is the only behaviour. It MUST be pure (no DB calls,
    no I/O); the resulting commands are persisted by the API layer.
    """

    meta: TemplateMeta

    def generate_commands(
        self, template_config: dict
    ) -> list[CreateSuiteItemCommandDto]:
        ...
