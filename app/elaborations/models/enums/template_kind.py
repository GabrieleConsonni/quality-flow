from enum import Enum


class TemplateKind(str, Enum):
    """Test template flavour stored on `suite_items.template_kind`.

    `CUSTOM` is the default for both legacy items (after the qsm_046 backfill)
    and newly created items that don't pick a template explicitly. The other
    values are reserved for the template-engine work in Phase 2 of the Test
    Suites refactor (`send_verify`, `mock_assert`).
    """

    CUSTOM = "custom"
    SEND_VERIFY = "send_verify"
    MOCK_ASSERT = "mock_assert"
