"""add token split fields

Revision ID: a2b3c4d5e6f7
Revises: f103d417ba5a
Create Date: 2026-05-31 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f103d417ba5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add default_max_input_tokens column (default 128000 for existing rows)
    op.add_column('providers', sa.Column('default_max_input_tokens', sa.Integer(), nullable=False, server_default='128000'))

    # Rename default_max_tokens to default_max_output_tokens
    # SQLite doesn't support ALTER TABLE RENAME COLUMN directly in older versions,
    # so we use batch mode which recreates the table
    with op.batch_alter_table('providers') as batch_op:
        batch_op.alter_column('default_max_tokens', new_column_name='default_max_output_tokens')


def downgrade() -> None:
    # Rename back
    with op.batch_alter_table('providers') as batch_op:
        batch_op.alter_column('default_max_output_tokens', new_column_name='default_max_tokens')

    # Drop the input tokens column
    op.drop_column('providers', 'default_max_input_tokens')
