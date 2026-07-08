"""set wongeric1417@gmail.com as admin

Revision ID: 003_set_admin
Revises: 002_drop_fk
Create Date: 2026-07-06 12:30:00.000000

Set the initial admin user so we can query users via the admin API.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_set_admin'
down_revision: Union[str, None] = '002_drop_fk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE users SET is_admin = true WHERE email = 'wongeric1417@gmail.com'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE users SET is_admin = false WHERE email = 'wongeric1417@gmail.com'"
    )
