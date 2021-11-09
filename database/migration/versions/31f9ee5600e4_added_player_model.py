"""Added Player model

Revision ID: 31f9ee5600e4
Revises: aa1822e145e0
Create Date: 2021-11-07 09:37:32.980197

"""
from alembic import op
import sqlalchemy as sa

from database.model import Player


# revision identifiers, used by Alembic.
revision = '31f9ee5600e4'
down_revision = 'aa1822e145e0'
branch_labels = None
depends_on = None


def extract_name(discord_name):
    return discord_name.split("#")[0]


def upgrade():
    op.create_table(
        'players',
        sa.Column('discord_id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column(
            'status',
            sa.Enum('ACTIVE', 'RESTRICTED', 'BANNED', name='playerstatus', native_enum=False, length=20),
            nullable=False
        ),
        sa.PrimaryKeyConstraint('discord_id')
    )

    # Bulk insertion of players using existing data in 'player_entries'
    select = """
        SELECT discord_id, discord_name
        FROM player_entries
        ORDER BY player_entries.registered_at
    """
    players = {}
    for entry in op.get_bind().execute(select).all():
        players[entry['discord_id']] = extract_name(entry['discord_name'])
    inserts = [
        {'discord_id': int(discord_id), 'name': name, 'status': 'ACTIVE'} for discord_id, name in players.items()
    ]
    op.bulk_insert(Player.__table__, inserts)

    op.alter_column('player_entries', 'discord_id', new_column_name='player_discord_id')
    op.create_foreign_key(None, 'player_entries', 'players', ['player_discord_id'], ['discord_id'])

    op.drop_column('player_entries', 'discord_name')


def downgrade():
    raise Exception("Downgrading from this point is not possible without the risk of data loss.")
