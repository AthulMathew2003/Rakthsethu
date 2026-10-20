"""add_spatial_locations_and_gist_indexes

Revision ID: ba833b851732
Revises: 1c2c096c0f25
Create Date: 2026-10-20 18:36:20.267657

"""
import geoalchemy2
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba833b851732'
down_revision: Union[str, None] = '1c2c096c0f25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable geography location column to donors
    op.add_column(
        'donors',
        sa.Column(
            'location',
            geoalchemy2.types.Geography(
                geometry_type='POINT',
                srid=4326,
                from_text='ST_GeogFromText',
                name='geography',
                nullable=True,
                spatial_index=False,
            ),
            nullable=True,
        ),
    )
    op.create_index(
        'idx_donors_location_gist',
        'donors',
        ['location'],
        unique=False,
        postgresql_using='gist',
    )

    # 2. Add nullable geography location column to hospitals
    op.add_column(
        'hospitals',
        sa.Column(
            'location',
            geoalchemy2.types.Geography(
                geometry_type='POINT',
                srid=4326,
                from_text='ST_GeogFromText',
                name='geography',
                nullable=True,
                spatial_index=False,
            ),
            nullable=True,
        ),
    )

    # 3. Backfill hospital spatial points from verified latitude/longitude fields
    op.execute("""
        UPDATE hospitals
        SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND latitude BETWEEN -90.0 AND 90.0
          AND longitude BETWEEN -180.0 AND 180.0;
    """)

    # 4. Create GiST spatial index on hospitals.location
    op.create_index(
        'idx_hospitals_location_gist',
        'hospitals',
        ['location'],
        unique=False,
        postgresql_using='gist',
    )


def downgrade() -> None:
    # 1. Drop spatial indexes
    op.drop_index('idx_hospitals_location_gist', table_name='hospitals', postgresql_using='gist')
    op.drop_index('idx_donors_location_gist', table_name='donors', postgresql_using='gist')

    # 2. Drop location columns
    op.drop_column('hospitals', 'location')
    op.drop_column('donors', 'location')
