"""drop attempts.question_id foreign key

Revision ID: 002_drop_fk
Revises: a9c41c94b087
Create Date: 2026-07-05 20:50:00.000000

Drop the FK constraint on attempts.question_id -> questions.id.
The v2 content system uses string IDs that don't reference the questions table.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_drop_fk'
down_revision: Union[str, None] = 'a9c41c94b087'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('attempts_question_id_fkey', 'attempts', type_='foreignkey')


def downgrade() -> None:
    op.create_foreign_key(
        'attempts_question_id_fkey',
        'attempts', 'questions',
        ['question_id'], ['id']
    )
