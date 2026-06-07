"""2026030112_QSM_005

Revision ID: c0b7e0f9d1aa
Revises: 938080744ade
Create Date: 2026-03-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c0b7e0f9d1aa"
down_revision: Union[str, Sequence[str], None] = "938080744ade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "scenario_steps",
        sa.Column("description", sa.Text(), nullable=True),
        schema="quality_flow_service",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("scenario_steps", "description", schema="quality_flow_service")

