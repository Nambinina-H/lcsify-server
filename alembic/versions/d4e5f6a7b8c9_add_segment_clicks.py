"""add segment clicks (APM)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('segments', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('clicks', sa.Integer(), nullable=True, server_default='0')
        )


def downgrade() -> None:
    with op.batch_alter_table('segments', schema=None) as batch_op:
        batch_op.drop_column('clicks')
