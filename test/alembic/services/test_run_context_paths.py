import pytest

from app.elaborations.services.suite_runs.run_context import (
    bind_run_context,
    bind_suite_item_context,
    create_run_context,
    extract_context_root,
    write_context_path,
)


def test_extract_context_root_supports_vars_alias():
    assert extract_context_root("$.vars.tenant") == "global"
    assert extract_context_root("$.local.result") == "local"
    assert extract_context_root("$.response.body") == "response"


def test_write_context_path_updates_nested_local_path():
    run_context = create_run_context(run_id="run-1")
    with bind_run_context(run_context):
        write_context_path("$.local.actual.rows", [{"id": 1}])

    assert run_context.local_vars["actual"]["rows"] == [{"id": 1}]


def test_write_context_path_blocks_global_in_test_scope():
    run_context = create_run_context(run_id="run-2")
    with bind_run_context(run_context):
        with bind_suite_item_context(item_kind="test", hook_phase=None, local_vars={}):
            with pytest.raises(
                ValueError,
                match="Global context is immutable during test execution.",
            ):
                write_context_path("$.global.forbidden", "x")
