import asyncio
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app._alembic.services.session_context_manager import managed_session
from app.elaborations.api.test_suites_api import (
    find_test_suite_api,
    insert_test_suite_api,
)
from app.elaborations.models.dtos.configuration_command_dto import (
    AssertConfigurationCommandDto,
    DataConfigurationOperationDto,
    SetVarConfigurationOperationDto,
)
from app.elaborations.models.dtos.test_suite_dto import (
    CreateSuiteItemCommandDto,
    CreateSuiteItemDto,
    CreateTestSuiteDto,
)
from app.elaborations.services.alembic.suite_item_execution_service import (
    SuiteItemExecutionService,
)
from app.elaborations.services.alembic.test_suite_execution_service import (
    TestSuiteExecutionService,
)
from app.elaborations.services.test_suites.test_suite_executor_thread import (
    TestSuiteExecutionInput,
    _execute,
)


def _cfg_payload(cfg) -> dict:
    return cfg.model_dump() if hasattr(cfg, "model_dump") else cfg


def test_test_suite_api_and_runtime_happy_path(alembic_container):
    del alembic_container
    dto = CreateTestSuiteDto(
        description="orders suite",
        hooks=[
            CreateSuiteItemDto(
                kind="hook",
                hook_phase="before-all",
                description="before all",
                commands=[
                    CreateSuiteItemCommandDto(
                        order=1,
                        description="set tenant",
                        cfg=_cfg_payload(SetVarConfigurationOperationDto(
                            definitionId="def-tenant",
                            key="tenant",
                            value="ACME",
                            scope="global",
                        )),
                    )
                ],
            ),
            CreateSuiteItemDto(
                kind="hook",
                hook_phase="before-each",
                description="before each",
                commands=[
                    CreateSuiteItemCommandDto(
                        order=1,
                        description="set local",
                        cfg=_cfg_payload(SetVarConfigurationOperationDto(
                            definitionId="def-local-customer",
                            key="local_customer",
                            value="C-001",
                            scope="local",
                        )),
                    )
                ],
            ),
        ],
        tests=[
            CreateSuiteItemDto(
                description="verifies global and local values",
                commands=[
                    CreateSuiteItemCommandDto(
                        order=1,
                        description="load inline data",
                        cfg=_cfg_payload(DataConfigurationOperationDto(
                            definitionId="def-actual-rows",
                            data=[{"id": 1, "customer": "C-001"}],
                            target="$.local.actualRows",
                        )),
                    ),
                    CreateSuiteItemCommandDto(
                        order=2,
                        description="assert tenant",
                        cfg=_cfg_payload(AssertConfigurationCommandDto(
                            commandCode="jsonEquals",
                            commandType="assert",
                            actualConstantRef={"definitionId": "def-tenant"},
                            expected="ACME",
                        )),
                    ),
                    CreateSuiteItemCommandDto(
                        order=3,
                        description="assert local",
                        cfg=_cfg_payload(AssertConfigurationCommandDto(
                            commandCode="jsonEquals",
                            commandType="assert",
                            actualConstantRef={"definitionId": "def-local-customer"},
                            expected="C-001",
                        )),
                    ),
                ],
            )
        ],
    )

    response = asyncio.run(insert_test_suite_api(dto))
    test_suite_id = str(response.get("id") or "").strip()
    assert test_suite_id

    payload = asyncio.run(find_test_suite_api(test_suite_id))
    assert payload["description"] == "orders suite"
    assert len(payload["hooks"]) == 2
    assert len(payload["tests"]) == 1

    _execute(
        TestSuiteExecutionInput(
            execution_id=str(uuid4()),
            test_suite_id=test_suite_id,
            test_suite_description="orders suite",
        )
    )

    with managed_session() as session:
        executions = TestSuiteExecutionService().get_all_by_suite_id(session, test_suite_id, limit=10)
        assert len(executions) == 1
        execution = executions[0]
        assert str(execution.status or "").strip().lower() == "success"
        items = SuiteItemExecutionService().get_all_by_execution_id(session, execution.id)
        assert len(items) == 3
        assert {str(item.item_kind) for item in items} == {"hook", "test"}


def test_test_execution_cannot_write_global_context(alembic_container):
    del alembic_container
    dto = CreateTestSuiteDto(
        description="suite global guard",
        tests=[
            CreateSuiteItemDto(
                description="test invalid global write",
                commands=[
                    CreateSuiteItemCommandDto(
                        order=1,
                        description="set global in test",
                        cfg=_cfg_payload(SetVarConfigurationOperationDto(
                            definitionId="def-forbidden",
                            key="forbidden",
                            value="boom",
                            scope="global",
                            target="$.global.forbidden",
                        )),
                    )
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="Scope 'global' is not writable in section 'test'"):
        asyncio.run(insert_test_suite_api(dto))


def test_suite_item_operation_dto_rejects_legacy_operation_id_field():
    with pytest.raises(ValidationError, match="operation_id"):
        CreateSuiteItemCommandDto(
            order=1,
            description="legacy import",
            cfg=_cfg_payload(
                DataConfigurationOperationDto(
                    definitionId="def-actualRows",
                    data=[{"id": 1}],
                    target="$.local.actualRows",
                )
            ),
            operation_id="legacy-operation-id",
        )

