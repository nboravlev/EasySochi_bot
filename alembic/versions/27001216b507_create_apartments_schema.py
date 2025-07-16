"""create apartments schema

Revision ID: 27001216b507
Revises: 
Create Date: 2025-07-16 12:45:26.691568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27001216b507'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS apartments")

def downgrade():
    op.execute("DROP SCHEMA IF EXISTS apartments CASCADE")

