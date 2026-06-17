"""add spaces (categories de collaborateurs)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'spaces',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=False, server_default='#1d4ed8'),
        sa.Column('icon', sa.String(length=40), nullable=False, server_default='grid'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.add_column(sa.Column('space_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_employee_space', 'spaces', ['space_id'], ['id'], ondelete='SET NULL'
        )
        batch_op.create_index('idx_employee_space', ['space_id'])


def downgrade() -> None:
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.drop_index('idx_employee_space')
        batch_op.drop_constraint('fk_employee_space', type_='foreignkey')
        batch_op.drop_column('space_id')
    op.drop_table('spaces')