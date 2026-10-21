"""add_telegram_bot_integration_tables

Revision ID: e891c94b1a20
Revises: 35b43421006d
Create Date: 2026-10-21 10:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e891c94b1a20'
down_revision: Union[str, None] = '35b43421006d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. telegram_updates (Durable idempotency & replay protection)
    op.create_table(
        'telegram_updates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('update_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=True),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('update_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PROCESSING', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_telegram_updates_update_id', 'telegram_updates', ['update_id'], unique=True)
    op.create_index('ix_telegram_updates_status', 'telegram_updates', ['status'], unique=False)

    # 2. telegram_blood_requests (Privacy-preserving request ownership)
    op.create_table(
        'telegram_blood_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('blood_request_id', sa.Integer(), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_username', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['blood_request_id'], ['blood_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_telegram_blood_requests_blood_request_id', 'telegram_blood_requests', ['blood_request_id'], unique=True)
    op.create_index('ix_telegram_blood_requests_telegram_user_id', 'telegram_blood_requests', ['telegram_user_id'], unique=False)
    op.create_index('idx_telegram_user_blood_request', 'telegram_blood_requests', ['telegram_user_id', 'blood_request_id'])

    # 3. telegram_link_tokens (Cryptographic one-time staff linking tokens)
    op.create_table(
        'telegram_link_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_used', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_telegram_link_tokens_token_hash', 'telegram_link_tokens', ['token_hash'], unique=True)
    op.create_index('ix_telegram_link_tokens_user_id', 'telegram_link_tokens', ['user_id'], unique=False)

    # 4. telegram_linked_staff (Persistent authorized staff bindings)
    op.create_table(
        'telegram_linked_staff',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_username', sa.String(length=64), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('linked_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_telegram_linked_staff_telegram_user_id', 'telegram_linked_staff', ['telegram_user_id'], unique=True)
    op.create_index('ix_telegram_linked_staff_user_id', 'telegram_linked_staff', ['user_id'], unique=True)

    # 5. telegram_conversations (Conversational state machine persistence)
    op.create_table(
        'telegram_conversations',
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('current_step', sa.String(length=32), server_default='IDLE', nullable=False),
        sa.Column('state_data', sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('telegram_user_id'),
    )


def downgrade() -> None:
    op.drop_table('telegram_conversations')
    op.drop_table('telegram_linked_staff')
    op.drop_table('telegram_link_tokens')
    op.drop_table('telegram_blood_requests')
    op.drop_table('telegram_updates')
