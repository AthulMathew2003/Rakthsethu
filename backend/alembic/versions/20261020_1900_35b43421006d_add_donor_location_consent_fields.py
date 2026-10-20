"""add_donor_location_consent_fields

Revision ID: 35b43421006d
Revises: ba833b851732
Create Date: 2026-10-20 19:00:16.971028

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35b43421006d'
down_revision: Union[str, None] = 'ba833b851732'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'donors',
        sa.Column(
            'location_consent',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
        ),
    )
    op.add_column(
        'donors',
        sa.Column(
            'location_consent_recorded_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('donors', 'location_consent_recorded_at')
    op.drop_column('donors', 'location_consent')
