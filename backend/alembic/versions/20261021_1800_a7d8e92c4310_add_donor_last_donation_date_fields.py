"""add_donor_last_donation_date_fields

Revision ID: a7d8e92c4310
Revises: f3a1d9b42100
Create Date: 2026-10-21 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d8e92c4310'
down_revision: Union[str, None] = 'f3a1d9b42100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Additive schema change on donors table to track self-reported last donation date, provenance, and timestamp
    op.add_column('donors', sa.Column('last_donation_date', sa.Date(), nullable=True))
    op.add_column('donors', sa.Column('last_donation_date_source', sa.String(length=30), nullable=True))
    op.add_column('donors', sa.Column('last_donation_date_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_donors_last_donation_date', 'donors', ['last_donation_date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_donors_last_donation_date', table_name='donors')
    op.drop_column('donors', 'last_donation_date_updated_at')
    op.drop_column('donors', 'last_donation_date_source')
    op.drop_column('donors', 'last_donation_date')
