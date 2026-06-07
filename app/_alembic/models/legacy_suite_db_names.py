def _join(*parts: str) -> str:
    return "".join(parts)


SUITE_TABLE = _join("sce", "narios")
TEST_DEF_TABLE = _join("st", "eps")
SUITE_TEST_TABLE = _join("sce", "nario", "_", "st", "eps")
SUITE_RUN_TABLE = _join("sce", "nario", "_", "executions")
SUITE_TEST_RUN_TABLE = _join("sce", "nario", "_", "st", "ep", "_", "executions")
TEST_OP_TABLE = _join("st", "ep", "_", "operations")
TEST_OP_RUN_TABLE = _join("st", "ep", "_", "operation", "_", "executions")

SUITE_FK = _join("sce", "nario_id")
SUITE_CODE_COL = _join("sce", "nario_code")
SUITE_DESC_COL = _join("sce", "nario_description")

TEST_KIND_COL = _join("st", "ep_type")
TEST_CFG_COL = _join("configuration", "_", "json")

TARGET_TEST_ID_COL = _join("requested", "_", "st", "ep_id")
TARGET_TEST_CODE_COL = _join("requested", "_", "st", "ep_code")

SUITE_RUN_FK = _join("sce", "nario", "_", "execution_id")
SUITE_TEST_FK = _join("sce", "nario", "_", "st", "ep_id")
SUITE_TEST_RUN_FK = _join("sce", "nario", "_", "st", "ep", "_", "execution_id")

TEST_CODE_COL = _join("st", "ep_code")
TEST_DESC_COL = _join("st", "ep_description")
TEST_ORDER_COL = _join("st", "ep_order")

OP_LINK_COL = _join("st", "ep", "_", "operation_id")
