from elaborations.services.suite_runs.suite_executor_thread import SuiteExecutorThread


def execute_suite_by_id(
    suite_id: str,
    *,
    run_event: dict | None = None,
    vars_init: dict | None = None,
    invocation_id: str | None = None,
):
    executor_thread = SuiteExecutorThread(
        suite_id,
        run_event=run_event,
        vars_init=vars_init,
        invocation_id=invocation_id,
    )
    executor_thread.start()
    return executor_thread.execution_id


def execute_suite_test_by_id(
    suite_id: str,
    suite_test_id: str,
    include_previous: bool = False,
):
    executor_thread = SuiteExecutorThread(
        suite_id=suite_id,
        target_suite_test_id=suite_test_id,
        include_previous=include_previous,
    )
    executor_thread.start()
    return executor_thread.execution_id
