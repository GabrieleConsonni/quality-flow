from elaborations.services.test_suites.test_suite_executor_thread import TestSuiteExecutorThread


def execute_test_suite_by_id(
    test_suite_id: str,
    *,
    run_event: dict | None = None,
    vars_init: dict | None = None,
    invocation_id: str | None = None,
    tenant_id: str = None,
):
    executor_thread = TestSuiteExecutorThread(
        test_suite_id,
        run_event=run_event,
        vars_init=vars_init,
        invocation_id=invocation_id,
        tenant_id=tenant_id,
    )
    executor_thread.start()
    return executor_thread.execution_id


def execute_test_by_id(
    test_suite_id: str,
    suite_item_id: str,
    tenant_id: str = None,
):
    executor_thread = TestSuiteExecutorThread(
        test_suite_id=test_suite_id,
        target_suite_item_id=suite_item_id,
        tenant_id=tenant_id,
    )
    executor_thread.start()
    return executor_thread.execution_id
