"""Added games table

Revision ID: 8da9320b9b5a
Revises: 81d409b223a9
Create Date: 2022-08-28 06:27:22.886871

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8da9320b9b5a'
down_revision = '81d409b223a9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'games',
        sa.Column('game', sa.Enum('ALTTPR', 'OOTR', 'MMR', 'TMCR', 'PKMN_CRYSTAL', 'SMR', 'HKR', name='games', native_enum=False), nullable=False),
        sa.Column('settings_text', sa.String, nullable=False),
        sa.Column('verification_text', sa.String, nullable=False),
        sa.PrimaryKeyConstraint('game')
    )


def downgrade():
    raise Exception("Downgrading from this point is not possible without the risk of data loss.")
