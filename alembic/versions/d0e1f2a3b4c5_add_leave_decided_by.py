"""add leaves.decided_by + decided_at (qui a valide/refuse le conge)

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-06-24 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('leaves', schema=None) as batch_op:
        batch_op.add_column(sa.Column('decided_by', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('decided_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('leaves', schema=None) as batch_op:
        batch_op.drop_column('decided_at')
        batch_op.drop_column('decided_by')
