"""add_telegram_donor_registration_tables

Revision ID: f3a1d9b42100
Revises: e891c94b1a20
Create Date: 2026-10-21 13:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a1d9b42100'
down_revision: Union[str, None] = 'e891c94b1a20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. telegram_donors (Voluntary donor account binding)
    op.create_table(
        'telegram_donors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('donor_id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_username', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['donor_id'], ['donors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_telegram_donors_donor_id', 'telegram_donors', ['donor_id'], unique=True)
    op.create_index('ix_telegram_donors_telegram_user_id', 'telegram_donors', ['telegram_user_id'], unique=True)

    # 2. telegram_donor_review_cases (Admin review queue for ambiguous duplicates)
    op.create_table(
        'telegram_donor_review_cases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('submitted_name', sa.String(length=150), nullable=False),
        sa.Column('submitted_blood_group', sa.String(length=10), nullable=False),
        sa.Column('submitted_district', sa.String(length=100), nullable=False),
        sa.Column('existing_donor_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['existing_donor_id'], ['donors.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_telegram_donor_review_cases_telegram_user_id', 'telegram_donor_review_cases', ['telegram_user_id'], unique=False)
    op.create_index('ix_telegram_donor_review_cases_phone', 'telegram_donor_review_cases', ['phone'], unique=False)
    op.create_index('ix_telegram_donor_review_cases_status', 'telegram_donor_review_cases', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('telegram_donor_review_cases')
    op.drop_table('telegram_donors')
