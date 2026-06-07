"""2026030212_QSM_007

Revision ID: 7f2b4c98c1de
Revises: 6c7d9f9c7a21
Create Date: 2026-03-02 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f2b4c98c1de"
down_revision: Union[str, Sequence[str], None] = "6c7d9f9c7a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "scenario_executions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("scenario_code", sa.Text(), nullable=False),
        sa.Column("scenario_description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("include_previous", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requested_step_id", sa.Text(), nullable=True),
        sa.Column("requested_step_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["quality_flow_service.scenarios.id"],
            ondelete="CASCADE",
        ),
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_scenario_executions_scenario_id_started_at",
        "scenario_executions",
        ["scenario_id", "started_at"],
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_scenario_executions_started_at",
        "scenario_executions",
        ["started_at"],
        schema="quality_flow_service",
    )

    op.create_table(
        "scenario_step_executions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("scenario_execution_id", sa.Text(), nullable=False),
        sa.Column("scenario_step_id", sa.Text(), nullable=True),
        sa.Column("step_code", sa.Text(), nullable=False),
        sa.Column("step_description", sa.Text(), nullable=True),
        sa.Column("step_order", sa.Numeric(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["scenario_execution_id"],
            ["quality_flow_service.scenario_executions.id"],
            ondelete="CASCADE",
        ),
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_scenario_step_executions_execution_id_order",
        "scenario_step_executions",
        ["scenario_execution_id", "step_order"],
        schema="quality_flow_service",
    )

    op.create_table(
        "step_operation_executions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("scenario_execution_id", sa.Text(), nullable=False),
        sa.Column("scenario_step_execution_id", sa.Text(), nullable=False),
        sa.Column("scenario_step_id", sa.Text(), nullable=True),
        sa.Column("step_operation_id", sa.Text(), nullable=True),
        sa.Column("operation_code", sa.Text(), nullable=False),
        sa.Column("operation_description", sa.Text(), nullable=True),
        sa.Column("operation_order", sa.Numeric(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["scenario_execution_id"],
            ["quality_flow_service.scenario_executions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_step_execution_id"],
            ["quality_flow_service.scenario_step_executions.id"],
            ondelete="CASCADE",
        ),
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_step_operation_executions_step_exec_id_order",
        "step_operation_executions",
        ["scenario_step_execution_id", "operation_order"],
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_step_operation_executions_execution_id",
        "step_operation_executions",
        ["scenario_execution_id"],
        schema="quality_flow_service",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_step_operation_executions_execution_id",
        table_name="step_operation_executions",
        schema="quality_flow_service",
    )
    op.drop_index(
        "ix_step_operation_executions_step_exec_id_order",
        table_name="step_operation_executions",
        schema="quality_flow_service",
    )
    op.drop_table("step_operation_executions", schema="quality_flow_service")

    op.drop_index(
        "ix_scenario_step_executions_execution_id_order",
        table_name="scenario_step_executions",
        schema="quality_flow_service",
    )
    op.drop_table("scenario_step_executions", schema="quality_flow_service")

    op.drop_index(
        "ix_scenario_executions_started_at",
        table_name="scenario_executions",
        schema="quality_flow_service",
    )
    op.drop_index(
        "ix_scenario_executions_scenario_id_started_at",
        table_name="scenario_executions",
        schema="quality_flow_service",
    )
    op.drop_table("scenario_executions", schema="quality_flow_service")
