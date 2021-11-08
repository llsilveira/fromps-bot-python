"""Init alembic (for existing databases, define 'DONT_CREATE_TABLES_ON_INITIAL_MIGRATION')

This revision was created while the main application were already running with a structured database. Since the upgrade
procedure uses 'create_table' operations, applying this revision on such databases will fail. To circumvent this, just
define an environment variable called 'DONT_CREATE_TABLES_ON_INITIAL_MIGRATION'. With that, all the 'create_table'
operations will be ignored (be sure that the database have the correct structure before doing this).

Revision ID: aa1822e145e0
Revises: 
Create Date: 2021-07-09 09:36:22.657039

"""
from alembic import op
import sqlalchemy as sa
import os


# revision identifiers, used by Alembic.
revision = 'aa1822e145e0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    if os.environ.get('DONT_CREATE_TABLES_ON_INITIAL_MIGRATION', None) is None:
        op.create_table(
            'weeklies',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                'game',
                sa.Enum('ALTTPR', 'OOTR', 'MMR', 'PKMN_CRYSTAL', 'SMR', name='games', native_enum=False, length=20),
                nullable=False
            ),
            sa.Column(
                'status',
                sa.Enum('OPEN', 'CLOSED', name='weeklystatus', native_enum=False, length=20),
                nullable=False
            ),
            sa.Column('seed_url', sa.String(), nullable=False),
            sa.Column('seed_hash', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('submission_end', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_table(
            'player_entries',
            sa.Column('weekly_id', sa.Integer(), nullable=False),
            sa.Column('discord_id', sa.BigInteger(), nullable=False),
            sa.Column('discord_name', sa.String(), nullable=False),
            sa.Column(
                'status',
                sa.Enum(
                    'REGISTERED', 'TIME_SUBMITTED', 'DONE', 'DNF', name='entrystatus', native_enum=False, length=20
                ),
                nullable=False
            ),
            sa.Column('finish_time', sa.Time(), nullable=True),
            sa.Column('print_url', sa.String(), nullable=True),
            sa.Column('vod_url', sa.String(), nullable=True),
            sa.Column('comment', sa.String(), nullable=True),
            sa.Column('registered_at', sa.DateTime(), nullable=False),
            sa.Column('time_submitted_at', sa.DateTime(), nullable=True),
            sa.Column('vod_submitted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(('weekly_id',), ['weeklies.id'], ),
            sa.PrimaryKeyConstraint('weekly_id', 'discord_id')
        )


def downgrade():
    raise Exception("Downgrading from this point is not possible without the risk of data loss.")
