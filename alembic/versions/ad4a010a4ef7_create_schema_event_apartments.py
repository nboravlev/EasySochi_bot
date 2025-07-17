"""create schema event apartments

Revision ID: ad4a010a4ef7
Revises: 
Create Date: 2025-07-17 13:53:50.094879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad4a010a4ef7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS apartments")
    op.execute("CREATE SCHEMA IF NOT EXISTS events")

def downgrade():
    op.execute("DROP SCHEMA IF EXISTS  apartments CASCADE")
    op.execute("DROP SCHEMA IF EXISTS  events CASCADE")
