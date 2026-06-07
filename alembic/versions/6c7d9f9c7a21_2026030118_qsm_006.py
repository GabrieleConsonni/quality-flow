"""2026030118_QSM_006

Revision ID: 6c7d9f9c7a21
Revises: c0b7e0f9d1aa
Create Date: 2026-03-01 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c7d9f9c7a21"
down_revision: Union[str, Sequence[str], None] = "c0b7e0f9d1aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("scenario_steps", sa.Column("code", sa.Text(), nullable=True), schema="quality_flow_service")
    op.add_column("scenario_steps", sa.Column("step_type", sa.Text(), nullable=True), schema="quality_flow_service")
    op.add_column("scenario_steps", sa.Column("configuration_json", sa.JSON(), nullable=True), schema="quality_flow_service")

    op.execute(
        """
        UPDATE quality_flow_service.scenario_steps AS ss
        SET
            code = COALESCE(st.code, ss.step_id),
            step_type = COALESCE(st.step_type, 'sleep'),
            configuration_json = COALESCE(st.configuration_json, '{}'::json)
        FROM quality_flow_service.steps AS st
        WHERE st.id = ss.step_id
        """
    )
    op.execute(
        """
        UPDATE quality_flow_service.scenario_steps
        SET
            code = COALESCE(code, 'step-' || id),
            step_type = COALESCE(step_type, 'sleep'),
            configuration_json = COALESCE(configuration_json, '{}'::json)
        """
    )

    op.alter_column("scenario_steps", "code", nullable=False, schema="quality_flow_service")
    op.alter_column("scenario_steps", "step_type", nullable=False, schema="quality_flow_service")
    op.alter_column("scenario_steps", "configuration_json", nullable=False, schema="quality_flow_service")

    op.drop_column("scenario_steps", "step_id", schema="quality_flow_service")

    op.add_column("step_operations", sa.Column("code", sa.Text(), nullable=True), schema="quality_flow_service")
    op.add_column("step_operations", sa.Column("description", sa.Text(), nullable=True), schema="quality_flow_service")
    op.add_column("step_operations", sa.Column("operation_type", sa.Text(), nullable=True), schema="quality_flow_service")
    op.add_column("step_operations", sa.Column("configuration_json", sa.JSON(), nullable=True), schema="quality_flow_service")

    op.execute(
        """
        UPDATE quality_flow_service.step_operations AS so
        SET
            code = COALESCE(opr.code, so.operation_id),
            description = opr.description,
            operation_type = COALESCE(opr.operation_type, 'publish'),
            configuration_json = COALESCE(opr.configuration_json, '{}'::json)
        FROM quality_flow_service.operations AS opr
        WHERE opr.id = so.operation_id
        """
    )
    op.execute(
        """
        UPDATE quality_flow_service.step_operations
        SET
            code = COALESCE(code, 'operation-' || id),
            operation_type = COALESCE(operation_type, 'publish'),
            configuration_json = COALESCE(configuration_json, '{}'::json)
        """
    )

    op.alter_column("step_operations", "code", nullable=False, schema="quality_flow_service")
    op.alter_column("step_operations", "operation_type", nullable=False, schema="quality_flow_service")
    op.alter_column("step_operations", "configuration_json", nullable=False, schema="quality_flow_service")

    op.drop_column("step_operations", "operation_id", schema="quality_flow_service")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("scenario_steps", sa.Column("step_id", sa.Text(), nullable=True), schema="quality_flow_service")
    op.execute(
        """
        UPDATE quality_flow_service.scenario_steps AS ss
        SET step_id = st.id
        FROM quality_flow_service.steps AS st
        WHERE st.code = ss.code
        """
    )
    op.alter_column("scenario_steps", "step_id", nullable=False, schema="quality_flow_service")
    op.create_foreign_key(
        "scenario_steps_step_id_fkey",
        "scenario_steps",
        "steps",
        ["step_id"],
        ["id"],
        source_schema="quality_flow_service",
        referent_schema="quality_flow_service",
    )

    op.drop_column("scenario_steps", "configuration_json", schema="quality_flow_service")
    op.drop_column("scenario_steps", "step_type", schema="quality_flow_service")
    op.drop_column("scenario_steps", "code", schema="quality_flow_service")

    op.add_column("step_operations", sa.Column("operation_id", sa.Text(), nullable=True), schema="quality_flow_service")
    op.execute(
        """
        UPDATE quality_flow_service.step_operations AS so
        SET operation_id = opr.id
        FROM quality_flow_service.operations AS opr
        WHERE opr.code = so.code
        """
    )
    op.alter_column("step_operations", "operation_id", nullable=False, schema="quality_flow_service")
    op.create_foreign_key(
        "step_operations_operation_id_fkey",
        "step_operations",
        "operations",
        ["operation_id"],
        ["id"],
        source_schema="quality_flow_service",
        referent_schema="quality_flow_service",
    )

    op.drop_column("step_operations", "configuration_json", schema="quality_flow_service")
    op.drop_column("step_operations", "operation_type", schema="quality_flow_service")
    op.drop_column("step_operations", "description", schema="quality_flow_service")
    op.drop_column("step_operations", "code", schema="quality_flow_service")
