"""initial_rakthasethu_schema

Revision ID: 7a17b6da95a4
Revises: 
Create Date: 2026-09-24 21:56:55.693076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7a17b6da95a4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define PostgreSQL enum types with exact domain values
blood_group_enum = postgresql.ENUM(
    'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-',
    name='blood_group_enum',
    create_type=False,
)
user_role_enum = postgresql.ENUM(
    'SUPER_ADMIN', 'HOSPITAL_ADMIN', 'STAFF',
    name='user_role_enum',
    create_type=False,
)
donation_status_enum = postgresql.ENUM(
    'SCHEDULED', 'COMPLETED', 'CANCELLED', 'REJECTED',
    name='donation_status_enum',
    create_type=False,
)
request_status_enum = postgresql.ENUM(
    'PENDING', 'IN_PROGRESS', 'FULFILLED', 'CANCELLED', 'REJECTED',
    name='request_status_enum',
    create_type=False,
)
request_urgency_enum = postgresql.ENUM(
    'NORMAL', 'URGENT', 'CRITICAL',
    name='request_urgency_enum',
    create_type=False,
)
import_status_enum = postgresql.ENUM(
    'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED',
    name='import_status_enum',
    create_type=False,
)


def upgrade() -> None:
    # 1. Create all PostgreSQL ENUM types explicitly
    sa.Enum('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', name='blood_group_enum').create(op.get_bind(), checkfirst=True)
    sa.Enum('SUPER_ADMIN', 'HOSPITAL_ADMIN', 'STAFF', name='user_role_enum').create(op.get_bind(), checkfirst=True)
    sa.Enum('SCHEDULED', 'COMPLETED', 'CANCELLED', 'REJECTED', name='donation_status_enum').create(op.get_bind(), checkfirst=True)
    sa.Enum('PENDING', 'IN_PROGRESS', 'FULFILLED', 'CANCELLED', 'REJECTED', name='request_status_enum').create(op.get_bind(), checkfirst=True)
    sa.Enum('NORMAL', 'URGENT', 'CRITICAL', name='request_urgency_enum').create(op.get_bind(), checkfirst=True)
    sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='import_status_enum').create(op.get_bind(), checkfirst=True)

    # 2. Create hospitals table
    op.create_table(
        'hospitals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('hospital_code', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('hospital_type', sa.String(length=50), server_default='Government', nullable=False),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('panchayat', sa.String(length=100), nullable=True),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('emergency_number', sa.String(length=20), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_hospitals_district', 'hospitals', ['district'], unique=False)
    op.create_index('idx_hospitals_is_active', 'hospitals', ['is_active'], unique=False)
    op.create_index(op.f('ix_hospitals_hospital_code'), 'hospitals', ['hospital_code'], unique=True)
    op.create_index(op.f('ix_hospitals_name'), 'hospitals', ['name'], unique=False)

    # 3. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_code', sa.String(length=32), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('role', user_role_enum, server_default='STAFF', nullable=False),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('panchayat', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=False)
    op.create_index('idx_users_hospital_id', 'users', ['hospital_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_user_code'), 'users', ['user_code'], unique=True)

    # 4. Create donors table
    op.create_table(
        'donors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('donor_code', sa.String(length=32), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=True),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('blood_group', blood_group_enum, nullable=False),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('panchayat', sa.String(length=100), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_available', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_donors_blood_group', 'donors', ['blood_group'], unique=False)
    op.create_index('idx_donors_district', 'donors', ['district'], unique=False)
    op.create_index('idx_donors_active_available', 'donors', ['is_active', 'is_available'], unique=False)
    op.create_index('idx_donors_matching_composite', 'donors', ['blood_group', 'district', 'is_active', 'is_available'], unique=False)
    op.create_index(op.f('ix_donors_donor_code'), 'donors', ['donor_code'], unique=True)
    op.create_index(op.f('ix_donors_full_name'), 'donors', ['full_name'], unique=False)
    op.create_index(op.f('ix_donors_phone'), 'donors', ['phone'], unique=True)

    # 5. Create donations table
    op.create_table(
        'donations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('donation_code', sa.String(length=32), nullable=False),
        sa.Column('donor_id', sa.Integer(), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=True),
        sa.Column('donation_date', sa.Date(), nullable=False),
        sa.Column('donation_type', sa.String(length=50), server_default='Voluntary', nullable=False),
        sa.Column('units_donated', sa.Integer(), server_default='1', nullable=False),
        sa.Column('status', donation_status_enum, server_default='COMPLETED', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('units_donated > 0', name='chk_units_donated_positive'),
        sa.ForeignKeyConstraint(['donor_id'], ['donors.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_donations_donor_id', 'donations', ['donor_id'], unique=False)
    op.create_index('idx_donations_hospital_id', 'donations', ['hospital_id'], unique=False)
    op.create_index('idx_donations_date_status', 'donations', ['donation_date', 'status'], unique=False)
    op.create_index(op.f('ix_donations_donation_code'), 'donations', ['donation_code'], unique=True)
    op.create_index(op.f('ix_donations_donation_date'), 'donations', ['donation_date'], unique=False)

    # 6. Create blood_requests table
    op.create_table(
        'blood_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_code', sa.String(length=32), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=False),
        sa.Column('patient_name', sa.String(length=150), nullable=False),
        sa.Column('blood_group', blood_group_enum, nullable=False),
        sa.Column('units_requested', sa.Integer(), server_default='1', nullable=False),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=False),
        sa.Column('emergency_contact', sa.String(length=20), nullable=True),
        sa.Column('required_date', sa.Date(), nullable=False),
        sa.Column('urgency', request_urgency_enum, server_default='NORMAL', nullable=False),
        sa.Column('status', request_status_enum, server_default='PENDING', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('units_requested > 0', name='chk_units_requested_positive'),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_requests_blood_group', 'blood_requests', ['blood_group'], unique=False)
    op.create_index('idx_requests_district', 'blood_requests', ['district'], unique=False)
    op.create_index('idx_requests_hospital_id', 'blood_requests', ['hospital_id'], unique=False)
    op.create_index('idx_requests_status', 'blood_requests', ['status'], unique=False)
    op.create_index('idx_requests_urgency', 'blood_requests', ['urgency'], unique=False)
    op.create_index(op.f('ix_blood_requests_request_code'), 'blood_requests', ['request_code'], unique=True)

    # 7. Create donor_import_batches table
    op.create_table(
        'donor_import_batches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('batch_code', sa.String(length=32), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_by_user_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_format', sa.String(length=10), server_default='csv', nullable=False),
        sa.Column('total_records', sa.Integer(), server_default='0', nullable=False),
        sa.Column('successful_records', sa.Integer(), server_default='0', nullable=False),
        sa.Column('failed_records', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', import_status_enum, server_default='PENDING', nullable=False),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_import_batches_hospital_id', 'donor_import_batches', ['hospital_id'], unique=False)
    op.create_index('idx_import_batches_status', 'donor_import_batches', ['status'], unique=False)
    op.create_index(op.f('ix_donor_import_batches_batch_code'), 'donor_import_batches', ['batch_code'], unique=True)


def downgrade() -> None:
    # 1. Drop tables in reverse topological order
    op.drop_table('donor_import_batches')
    op.drop_table('donations')
    op.drop_table('donors')
    op.drop_table('users')
    op.drop_table('blood_requests')
    op.drop_table('hospitals')

    # 2. Drop custom PostgreSQL ENUM types
    sa.Enum(name='import_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='request_urgency_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='request_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='donation_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='user_role_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='blood_group_enum').drop(op.get_bind(), checkfirst=True)
