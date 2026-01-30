"""add_subcategory_to_tags

Revision ID: 680342bf43a5
Revises: 9809a1824ca3
Create Date: 2026-01-29 12:23:29.638594

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '680342bf43a5'
down_revision: str | Sequence[str] | None = '9809a1824ca3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add subcategory column and populate it based on tag patterns."""
    # Add the column
    op.add_column('tags', sa.Column('subcategory', sa.String(50), nullable=True))
    op.create_index('ix_tags_subcategory', 'tags', ['subcategory'])

    # Populate subcategory for scene tags
    connection = op.get_bind()

    # Indoor locations
    indoor_patterns = [
        'indoor', 'room', 'library', 'cafe', 'store', 'shop', 'office', 'classroom',
        'bedroom', 'kitchen', 'bathroom', 'living', 'hall', 'gym', 'train', 'bus',
        'convenience_store', 'restaurant', 'bar', 'hospital', 'church', 'temple'
    ]

    for pattern in indoor_patterns:
        connection.execute(
            sa.text(f"""
                UPDATE tags 
                SET subcategory = 'indoor'
                WHERE category = 'scene' 
                AND (name LIKE '%{pattern}%' OR name = '{pattern}')
                AND subcategory IS NULL
            """)
        )

    # Outdoor locations
    outdoor_patterns = [
        'outdoor', 'forest', 'beach', 'park', 'street', 'sky', 'cloud', 'mountain',
        'sea', 'ocean', 'river', 'garden', 'city', 'town', 'village', 'view',
        'field', 'meadow', 'hill', 'valley', 'bridge', 'rooftop'
    ]

    for pattern in outdoor_patterns:
        connection.execute(
            sa.text(f"""
                UPDATE tags 
                SET subcategory = 'outdoor'
                WHERE category = 'scene' 
                AND (name LIKE '%{pattern}%' OR name = '{pattern}')
                AND subcategory IS NULL
            """)
        )

    # Time/weather
    time_patterns = [
        'day', 'night', 'morning', 'evening', 'sunset', 'sunrise', 'dusk', 'dawn',
        'sunny', 'cloudy', 'rainy', 'snowy', 'foggy'
    ]

    for pattern in time_patterns:
        connection.execute(
            sa.text(f"""
                UPDATE tags 
                SET subcategory = 'time'
                WHERE category = 'scene' 
                AND (name LIKE '%{pattern}%' OR name = '{pattern}')
                AND subcategory IS NULL
            """)
        )

    # Clothing (for general category)
    clothing_patterns = [
        'shirt', 'dress', 'skirt', 'pants', 'uniform', 'suit', 'jacket', 'coat',
        'hat', 'shoes', 'boots', 'gloves', 'glasses', 'necklace', 'tie', 'hoodie',
        'sweater', 'blouse', 'vest', 'shorts', 'socks', 'stockings'
    ]

    for pattern in clothing_patterns:
        connection.execute(
            sa.text(f"""
                UPDATE tags 
                SET subcategory = 'clothing'
                WHERE category = 'general' 
                AND (name LIKE '%{pattern}%' OR name = '{pattern}')
                AND subcategory IS NULL
            """)
        )


def downgrade() -> None:
    """Remove subcategory column."""
    op.drop_index('ix_tags_subcategory', 'tags')
    op.drop_column('tags', 'subcategory')
