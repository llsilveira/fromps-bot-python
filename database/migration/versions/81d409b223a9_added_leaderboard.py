"""Added Leaderboard

Revision ID: 81d409b223a9
Revises: 31f9ee5600e4
Create Date: 2021-11-10 08:45:48.362672

"""
from alembic import op
import sqlalchemy as sa

from database.model import Player, PlayerEntry


# revision identifiers, used by Alembic.
revision = '81d409b223a9'
down_revision = '31f9ee5600e4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'leaderboards',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('game', sa.Enum('ALTTPR', 'OOTR', 'MMR', 'PKMN_CRYSTAL', 'SMR', 'HKR', name='games', native_enum=False), nullable=False),
        sa.Column('results_url', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('OPEN', 'CLOSED', name='leaderboardstatus', native_enum=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('leaderboard_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'leaderboard_entries',
        sa.Column('leaderboard_id', sa.Integer(), nullable=False),
        sa.Column('player_discord_id', sa.BigInteger(), nullable=False),
        sa.Column('leaderboard_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['leaderboard_id'], ['leaderboards.id'], ),
        sa.ForeignKeyConstraint(['player_discord_id'], ['players.discord_id'], ),
        sa.PrimaryKeyConstraint('leaderboard_id', 'player_discord_id')
    )
    op.add_column('player_entries', sa.Column('leaderboard_data', sa.JSON(), nullable=True))
    op.add_column('players', sa.Column('leaderboard_data', sa.JSON(), nullable=True))
    op.add_column('weeklies', sa.Column('leaderboard_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'weeklies', 'leaderboards', ['leaderboard_id'], ['id'])

    op.execute(
        sa.update(Player).values({"leaderboard_data": {"excluded_from": []}})
    )

    op.execute(
        sa.update(PlayerEntry).values({"leaderboard_data": {"excluded": False}})
    )


def downgrade():
    raise Exception("Downgrading from this point is not possible without the risk of data loss.")
