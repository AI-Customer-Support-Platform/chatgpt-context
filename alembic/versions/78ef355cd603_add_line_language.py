"""Add line language

Revision ID: 78ef355cd603
Revises: a36990aecebc
Create Date: 2023-09-01 20:51:50.429420

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '78ef355cd603'
down_revision = 'a36990aecebc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('collections', sa.Column('line_language', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('collections', 'line_language')
    # ### end Alembic commands ###