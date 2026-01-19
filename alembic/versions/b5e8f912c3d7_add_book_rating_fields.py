"""add_book_rating_fields

Revision ID: b5e8f912c3d7
Revises: af7671001473
Create Date: 2026-01-19 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5e8f912c3d7'
down_revision: Union[str, None] = 'af7671001473'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add average_rating column to books table
    op.add_column(
        'books',
        sa.Column(
            'average_rating',
            sa.Numeric(precision=3, scale=2),
            nullable=True,
            comment='Average review rating (1.00-5.00), null if no reviews'
        )
    )
    op.create_index(
        op.f('ix_books_average_rating'),
        'books',
        ['average_rating'],
        unique=False
    )

    # Add review_count column to books table
    op.add_column(
        'books',
        sa.Column(
            'review_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Number of reviews for this book'
        )
    )
    op.create_index(
        op.f('ix_books_review_count'),
        'books',
        ['review_count'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_books_review_count'), table_name='books')
    op.drop_column('books', 'review_count')
    op.drop_index(op.f('ix_books_average_rating'), table_name='books')
    op.drop_column('books', 'average_rating')
