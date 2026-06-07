from contextlib import contextmanager
from contextvars import ContextVar, Token


_EXECUTION_ID: ContextVar[str | None] = ContextVar("execution_id", default=None)
_SUITE_ID: ContextVar[str | None] = ContextVar("suite_id", default=None)
_SUITE_TEST_ID: ContextVar[str | None] = ContextVar("suite_test_id", default=None)
_SUITE_EXECUTION_ID: ContextVar[str | None] = ContextVar("suite_execution_id", default=None)
_SUITE_TEST_EXECUTION_ID: ContextVar[str | None] = ContextVar("suite_test_execution_id", default=None)
_TEST_SUITE_ID: ContextVar[str | None] = ContextVar("test_suite_id", default=None)
_SUITE_ITEM_ID: ContextVar[str | None] = ContextVar("suite_item_id", default=None)
_TEST_SUITE_EXECUTION_ID: ContextVar[str | None] = ContextVar("test_suite_execution_id", default=None)
_SUITE_ITEM_EXECUTION_ID: ContextVar[str | None] = ContextVar("suite_item_execution_id", default=None)


def get_execution_id() -> str | None:
    return _EXECUTION_ID.get()


def get_suite_id() -> str | None:
    return _SUITE_ID.get()


def get_suite_test_id() -> str | None:
    return _SUITE_TEST_ID.get()


def get_suite_execution_id() -> str | None:
    return _SUITE_EXECUTION_ID.get()


def get_suite_test_execution_id() -> str | None:
    return _SUITE_TEST_EXECUTION_ID.get()


def get_test_suite_id() -> str | None:
    return _TEST_SUITE_ID.get()


def get_suite_item_id() -> str | None:
    return _SUITE_ITEM_ID.get()


def get_test_suite_execution_id() -> str | None:
    return _TEST_SUITE_EXECUTION_ID.get()


def get_suite_item_execution_id() -> str | None:
    return _SUITE_ITEM_EXECUTION_ID.get()


@contextmanager
def bind_execution_context(
    *,
    execution_id: str | None = None,
    suite_id: str | None = None,
    suite_test_id: str | None = None,
    suite_execution_id: str | None = None,
    suite_test_execution_id: str | None = None,
    test_suite_id: str | None = None,
    suite_item_id: str | None = None,
    test_suite_execution_id: str | None = None,
    suite_item_execution_id: str | None = None,
):
    tokens: list[tuple[ContextVar, Token]] = []
    try:
        if execution_id is not None:
            tokens.append((_EXECUTION_ID, _EXECUTION_ID.set(execution_id)))
        if suite_id is not None:
            tokens.append((_SUITE_ID, _SUITE_ID.set(suite_id)))
        if suite_test_id is not None:
            tokens.append((_SUITE_TEST_ID, _SUITE_TEST_ID.set(suite_test_id)))
        if suite_execution_id is not None:
            tokens.append((_SUITE_EXECUTION_ID, _SUITE_EXECUTION_ID.set(suite_execution_id)))
        if suite_test_execution_id is not None:
            tokens.append(
                (_SUITE_TEST_EXECUTION_ID, _SUITE_TEST_EXECUTION_ID.set(suite_test_execution_id))
            )
        if test_suite_id is not None:
            tokens.append((_TEST_SUITE_ID, _TEST_SUITE_ID.set(test_suite_id)))
        if suite_item_id is not None:
            tokens.append((_SUITE_ITEM_ID, _SUITE_ITEM_ID.set(suite_item_id)))
        if test_suite_execution_id is not None:
            tokens.append((_TEST_SUITE_EXECUTION_ID, _TEST_SUITE_EXECUTION_ID.set(test_suite_execution_id)))
        if suite_item_execution_id is not None:
            tokens.append((_SUITE_ITEM_EXECUTION_ID, _SUITE_ITEM_EXECUTION_ID.set(suite_item_execution_id)))
        yield
    finally:
        for context_var, token in reversed(tokens):
            context_var.reset(token)

