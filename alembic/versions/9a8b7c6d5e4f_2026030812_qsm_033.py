"""2026030812_QSM_033

Revision ID: 9a8b7c6d5e4f
Revises: d97e5e8ab3b1
Create Date: 2026-03-08 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = "d97e5e8ab3b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mock_server_invocations",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("mock_server_id", sa.Text(), nullable=False),
        sa.Column("mock_server_code", sa.Text(), nullable=False),
        sa.Column("trigger_type", sa.Text(), nullable=False),
        sa.Column("trigger_code", sa.Text(), nullable=True),
        sa.Column("event_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["mock_server_id"],
            ["quality_flow_service.mock_servers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_mock_server_invocations_server_created_at",
        "mock_server_invocations",
        ["mock_server_id", "created_at"],
        schema="quality_flow_service",
    )

    op.add_column(
        "scenario_executions",
        sa.Column("invocation_id", sa.Text(), nullable=True),
        schema="quality_flow_service",
    )
    op.add_column(
        "scenario_executions",
        sa.Column("vars_init_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        schema="quality_flow_service",
    )
    op.add_column(
        "scenario_executions",
        sa.Column("result_json", sa.JSON(), nullable=True),
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_scenario_executions_invocation_id",
        "scenario_executions",
        ["invocation_id"],
        schema="quality_flow_service",
    )
    op.create_foreign_key(
        "fk_scenario_executions_invocation_id",
        "scenario_executions",
        "mock_server_invocations",
        ["invocation_id"],
        ["id"],
        source_schema="quality_flow_service",
        referent_schema="quality_flow_service",
        ondelete="SET NULL",
    )
    op.alter_column(
        "scenario_executions",
        "vars_init_json",
        schema="quality_flow_service",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_scenario_executions_invocation_id",
        "scenario_executions",
        schema="quality_flow_service",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_scenario_executions_invocation_id",
        table_name="scenario_executions",
        schema="quality_flow_service",
    )
    op.drop_column("scenario_executions", "result_json", schema="quality_flow_service")
    op.drop_column("scenario_executions", "vars_init_json", schema="quality_flow_service")
    op.drop_column("scenario_executions", "invocation_id", schema="quality_flow_service")

    op.drop_index(
        "ix_mock_server_invocations_server_created_at",
        table_name="mock_server_invocations",
        schema="quality_flow_service",
    )
    op.drop_table("mock_server_invocations", schema="quality_flow_service")
