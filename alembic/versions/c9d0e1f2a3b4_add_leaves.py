"""add hr_collaborateurs + leaves (gestion des conges)

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'hr_collaborateurs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('matricule', sa.String(length=50), nullable=False),
        sa.Column('nom', sa.String(length=255), nullable=True),
        sa.Column('prenom', sa.String(length=255), nullable=True),
        sa.Column('solde_initial', sa.Float(), server_default='0', nullable=False),
        sa.Column('date_solde', sa.Date(), nullable=True),
        sa.Column('poste', sa.String(length=255), nullable=True),
        sa.Column('service', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('matricule', name='uq_hr_matricule'),
    )
    op.create_table(
        'leaves',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('hr_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=40), nullable=False),
        sa.Column('date_debut', sa.Date(), nullable=False),
        sa.Column('date_fin', sa.Date(), nullable=False),
        sa.Column('nb_jours', sa.Float(), server_default='0', nullable=False),
        sa.Column('motif', sa.Text(), nullable=True),
        sa.Column('statut', sa.String(length=20), server_default='approuve', nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['hr_id'], ['hr_collaborateurs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_leave_hr', 'leaves', ['hr_id'])
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hr_collaborateur_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_employee_hr', 'hr_collaborateurs', ['hr_collaborateur_id'], ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_index('idx_employee_hr', ['hr_collaborateur_id'])


def downgrade() -> None:
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.drop_index('idx_employee_hr')
        batch_op.drop_constraint('fk_employee_hr', type_='foreignkey')
        batch_op.drop_column('hr_collaborateur_id')
    op.drop_index('idx_leave_hr', table_name='leaves')
    op.drop_table('leaves')
    op.drop_table('hr_collaborateurs')
