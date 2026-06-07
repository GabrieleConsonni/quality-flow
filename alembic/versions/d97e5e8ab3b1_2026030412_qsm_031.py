"""2026030412_QSM_031

Revision ID: d97e5e8ab3b1
Revises: 7f2b4c98c1de
Create Date: 2026-03-04 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d97e5e8ab3b1"
down_revision: Union[str, Sequence[str], None] = "7f2b4c98c1de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mock_servers",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint", name="uq_mock_servers_endpoint"),
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_mock_servers_endpoint",
        "mock_servers",
        ["endpoint"],
        schema="quality_flow_service",
    )

    op.create_table(
        "mock_server_apis",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("mock_server_id", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("order", sa.Numeric(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["mock_server_id"],
            ["quality_flow_service.mock_servers.id"],
            ondelete="CASCADE",
        ),
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_mock_server_apis_server_order",
        "mock_server_apis",
        ["mock_server_id", "order"],
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_mock_server_apis_server_method_path_order",
        "mock_server_apis",
        ["mock_server_id", "method", "path", "order"],
        schema="quality_flow_service",
    )

    op.create_table(
        "ms_api_operations",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("mock_server_api_id", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("order", sa.Numeric(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["mock_server_api_id"],
            ["quality_flow_service.mock_server_apis.id"],
            ondelete="CASCADE",
        ),
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_ms_api_operations_api_order",
        "ms_api_operations",
        ["mock_server_api_id", "order"],
        schema="quality_flow_service",
    )

    op.create_table(
        "mock_server_queues",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("mock_server_id", sa.Text(), nullable=False),
        sa.Column("queue_id", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("order", sa.Numeric(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["mock_server_id"],
            ["quality_flow_service.mock_servers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["queue_id"],
            ["quality_flow_service.queues.id"],
        ),
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_mock_server_queues_server_queue",
        "mock_server_queues",
        ["mock_server_id", "queue_id"],
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_mock_server_queues_server_order",
        "mock_server_queues",
        ["mock_server_id", "order"],
        schema="quality_flow_service",
    )

    op.create_table(
        "ms_queue_operations",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("mock_server_queue_id", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("order", sa.Numeric(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["mock_server_queue_id"],
            ["quality_flow_service.mock_server_queues.id"],
            ondelete="CASCADE",
        ),
        schema="quality_flow_service",
    )
    op.create_index(
        "ix_ms_queue_operations_queue_order",
        "ms_queue_operations",
        ["mock_server_queue_id", "order"],
        schema="quality_flow_service",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_ms_queue_operations_queue_order",
        table_name="ms_queue_operations",
        schema="quality_flow_service",
    )
    op.drop_table("ms_queue_operations", schema="quality_flow_service")

    op.drop_index(
        "ix_mock_server_queues_server_order",
        table_name="mock_server_queues",
        schema="quality_flow_service",
    )
    op.drop_index(
        "ix_mock_server_queues_server_queue",
        table_name="mock_server_queues",
        schema="quality_flow_service",
    )
    op.drop_table("mock_server_queues", schema="quality_flow_service")

    op.drop_index(
        "ix_ms_api_operations_api_order",
        table_name="ms_api_operations",
        schema="quality_flow_service",
    )
    op.drop_table("ms_api_operations", schema="quality_flow_service")

    op.drop_index(
        "ix_mock_server_apis_server_method_path_order",
        table_name="mock_server_apis",
        schema="quality_flow_service",
    )
    op.drop_index(
        "ix_mock_server_apis_server_order",
        table_name="mock_server_apis",
        schema="quality_flow_service",
    )
    op.drop_table("mock_server_apis", schema="quality_flow_service")

    op.drop_index(
        "ix_mock_servers_endpoint",
        table_name="mock_servers",
        schema="quality_flow_service",
    )
    op.drop_table("mock_servers", schema="quality_flow_service")
