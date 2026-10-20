"""enable_postgis_extension

Revision ID: 1c2c096c0f25
Revises: 7a17b6da95a4
Create Date: 2026-10-20 18:22:41.536427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c2c096c0f25'
down_revision: Union[str, None] = '7a17b6da95a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS postgis RESTRICT;")
