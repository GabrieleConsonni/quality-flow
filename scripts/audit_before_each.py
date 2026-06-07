"""Pre-migration audit: report which test suites still rely on the
per-test `beforeEach` semantics.

The Test Suites refactor (Phase 1) collapses the four legacy hooks
(`before-all`, `before-each`, `after-each`, `after-all`) into two
(`setup`, `teardown`). The `before-each` hook used to run once per test;
after the collapse it will run only once before the whole suite. Any
suite that uses a non-empty `before-each` for per-test state reset is at
risk and needs an explicit migration of that logic into each test (or
into a dedicated "reset" test at the start of the suite).

This script counts, per tenant, the suite_items with
`hook_phase = 'before-each'` that own at least one row in
`suite_item_commands`. The total is purely informational — it does NOT
block the Alembic migration that follows.

Usage
-----
Inside the docker container (PYTHONPATH already configured):
    docker exec quality-flow python /quality-flow/scripts/audit_before_each.py

From the host with the project venv:
    PYTHONPATH=app python scripts/audit_before_each.py

Exit codes
----------
    0 -- no `before-each` usage with commands found, safe to proceed.
    1 -- at least one suite at risk; review the report before applying
         the 4 -> 2 hook migration.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_APP_PATH = Path(__file__).resolve().parent.parent / "app"
if str(_APP_PATH) not in sys.path:
    sys.path.insert(0, str(_APP_PATH))

from sqlalchemy import text

from _alembic.constants import SCHEMA
from _alembic.services.session_context_manager import managed_session
from elaborations.models.enums.hook_phase import HookPhase
from services.multitenant.multitenant_service import get_tenants


@dataclass(frozen=True)
class BeforeEachUsage:
    tenant_id: str
    suite_id: str
    suite_code: str
    suite_description: str | None
    suite_item_id: str
    commands_count: int


_QUERY = text(
    f"""
    SELECT
        si.id                                          AS suite_item_id,
        ts.id                                          AS suite_id,
        ts.code                                        AS suite_code,
        ts.description                                 AS suite_description,
        COUNT(sic.id)                                  AS commands_count
    FROM {SCHEMA}.suite_items     AS si
    JOIN {SCHEMA}.test_suites     AS ts  ON ts.id = si.test_suite_id
    LEFT JOIN {SCHEMA}.suite_item_commands AS sic ON sic.suite_item_id = si.id
    WHERE si.hook_phase = :hook_phase
    GROUP BY si.id, ts.id, ts.code, ts.description
    HAVING COUNT(sic.id) > 0
    ORDER BY ts.code, si.id
    """
)


def audit_tenant(tenant_id: str) -> list[BeforeEachUsage]:
    rows: list[BeforeEachUsage] = []
    with managed_session(tenant_id=tenant_id) as session:
        result = session.execute(
            _QUERY, {"hook_phase": HookPhase.BEFORE_EACH.value}
        )
        for r in result:
            rows.append(
                BeforeEachUsage(
                    tenant_id=tenant_id,
                    suite_id=str(r.suite_id),
                    suite_code=str(r.suite_code),
                    suite_description=r.suite_description,
                    suite_item_id=str(r.suite_item_id),
                    commands_count=int(r.commands_count),
                )
            )
    return rows


def audit_all_tenants() -> list[BeforeEachUsage]:
    out: list[BeforeEachUsage] = []
    for t in get_tenants():
        try:
            out.extend(audit_tenant(t.tenant_id))
        except Exception as exc:
            print(
                f"[warn] audit failed for tenant '{t.tenant_id}': {exc}",
                file=sys.stderr,
            )
    return out


def _format_report(rows: list[BeforeEachUsage]) -> str:
    title = "=== Pre-migration audit: beforeEach usage ==="
    if not rows:
        return (
            f"{title}\n"
            "No suite_items with hook_phase='before-each' and non-empty commands were found.\n"
            "The 4 -> 2 hook collapse can proceed without per-test semantics loss.\n"
        )

    tenants = sorted({r.tenant_id for r in rows})
    suite_keys = {(r.tenant_id, r.suite_id) for r in rows}
    total_steps = sum(r.commands_count for r in rows)

    w_tenant = max(len("Tenant"), *(len(r.tenant_id) for r in rows))
    w_code = max(len("Suite code"), *(len(r.suite_code) for r in rows))
    w_item = 36  # uuid width

    header = (
        f"{'Tenant':<{w_tenant}}  "
        f"{'Suite code':<{w_code}}  "
        f"{'Suite item id':<{w_item}}  "
        "Cmds"
    )
    sep = "-" * len(header)
    body = [
        f"{r.tenant_id:<{w_tenant}}  "
        f"{r.suite_code:<{w_code}}  "
        f"{r.suite_item_id:<{w_item}}  "
        f"{r.commands_count}"
        for r in rows
    ]

    summary = (
        f"\n{sep}\n"
        f"TOTAL: {len(suite_keys)} suite(s) across {len(tenants)} tenant(s); "
        f"{total_steps} beforeEach command(s) overall.\n\n"
        "Breaking change risk: these suites currently rely on the per-test\n"
        "semantics of beforeEach. After the 4 -> 2 hook collapse those commands\n"
        "will run ONCE before all tests, NOT before each test.\n\n"
        "Recommended action before applying the migration: review each suite\n"
        "above and either (a) move the per-test reset to the first step of\n"
        "every test, or (b) add a dedicated 'reset' test at the start of the\n"
        "suite.\n"
    )

    return f"{title}\n{header}\n{sep}\n" + "\n".join(body) + summary


def main() -> int:
    rows = audit_all_tenants()
    print(_format_report(rows))
    return 1 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
