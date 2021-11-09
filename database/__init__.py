from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from datetime import datetime

from datatypes import PlayerStatus, EntryStatus, WeeklyStatus
from database.model import Player, PlayerEntry, Weekly, Base

import logging
logger = logging.getLogger(__name__)


class ConsistencyError(Exception):
    pass


class Database:
    def __init__(
            self,
            *,
            dialect,
            dbapi="",
            user="",
            password="",
            host="",
            port="",
            dbpath,
            engine_options=None
    ):
        url = Database.build_database_url(
            dialect=dialect,
            dbapi=dbapi,
            user=user,
            password=password,
            host=host,
            port=port,
            dbpath=dbpath
        )
        options = engine_options or {}
        self.engine = create_engine(url, **options, future=True)
        self.Session = sessionmaker(self.engine, future=True)

    def get_player(self, session, discord_id):
        return session.get(Player, discord_id)

    def create_player(self, session, discord_user):
        player = Player(
            discord_id=discord_user.id,
            name=discord_user.display_name,
            status=PlayerStatus.ACTIVE
        )
        session.add(player)
        return player

    def get_or_create_player(self, session, discord_user):
        player = self.get_player(session, discord_user.id)
        if player is None:
            player = self.create_player(session, discord_user)
        return player

    def get_weekly(self, session, weekly_id):
        return session.get(Weekly, weekly_id)

    def get_open_weekly(self, session, game):
        return session.execute(
            select(Weekly).where(Weekly.game == game, Weekly.status == WeeklyStatus.OPEN).order_by(
                Weekly.created_at.desc()
            )
        ).scalars().first()

    def get_last_closed_weekly(self, session, game):
        return session.execute(
            select(Weekly).where(Weekly.game == game, Weekly.status == WeeklyStatus.CLOSED).order_by(
                Weekly.created_at.desc()
            )
        ).scalars().first()

    def reopen_weekly(self, session, weekly):
        if weekly.status is not WeeklyStatus.CLOSED:
            raise ConsistencyError("Attempt to reopen a weekly that was not closed.")
        open_weekly = self.get_open_weekly(session, weekly.game)
        if open_weekly is not None:
            raise ConsistencyError(
                "Attempt to reopen a weekly while another one for the same game is open"
            )
        weekly.status = WeeklyStatus.OPEN

    def list_open_weeklies(self, session):
        return session.execute(
            select(Weekly).where(Weekly.status == WeeklyStatus.OPEN)
        ).scalars().all()

    def create_weekly(self, session, game, seed_url, seed_hash, submission_end):
        open_weekly = self.get_open_weekly(session, game)
        if open_weekly is not None:
            raise ConsistencyError(
                "Attempt to create a weekly while another one for the same game is still open"
            )

        weekly = Weekly(
            game=game,
            status=WeeklyStatus.OPEN,
            seed_url=seed_url,
            seed_hash=seed_hash,
            created_at=datetime.now(),
            submission_end=submission_end
        )
        session.add(weekly)
        return weekly

    def update_weekly(self, session, weekly, seed_url, seed_hash, submission_end):
        weekly.seed_url = seed_url
        weekly.seed_hash = seed_hash
        weekly.submission_end = submission_end
        return weekly

    def close_weekly(self, session, weekly):
        for entry in weekly.entries:
            if entry.status == EntryStatus.REGISTERED:
                entry.status = EntryStatus.DNF
        weekly.status = WeeklyStatus.CLOSED

    def get_player_entry(self, session, weekly, player):
        return session.get(PlayerEntry, (weekly.id, player.discord_id))

    def get_registered_entry(self, session, player):
        registered = session.execute(
            select(PlayerEntry).where(PlayerEntry.player_discord_id == player.discord_id,
                                      PlayerEntry.status == EntryStatus.REGISTERED)
        ).scalars().all()

        if len(registered) == 0:
            return None

        if len(registered) > 1:
            logger.error(
                "An inconsistency was found while quering the database: user %d has more than one 'REGISTERED' entry.",
                player.discord_id
            )
        return registered[0]

    def register_player(self, session, weekly, player):
        if self.get_registered_entry(session, player) is not None:
            raise ConsistencyError(
                "Attempt to register a player that is already registered to a weekly."
            )

        entry = PlayerEntry(
            weekly=weekly,
            player=player,
            status=EntryStatus.REGISTERED,
            registered_at=datetime.now()
        )
        session.add(entry)
        return entry

    def forfeit(self, session, entry):
        if entry.status != EntryStatus.REGISTERED:
            raise ConsistencyError(
                "Attempt to forfeit a player that is not registered to a weekly."
            )
        entry.status = EntryStatus.DNF

    def submit_time(self, session, entry, finish_time, print_url):
        if entry.status != EntryStatus.REGISTERED:
            raise ConsistencyError(
                "Attempt to register a time for a player that is not registered to a weekly."
            )
        entry.finish_time = finish_time
        entry.print_url = print_url
        entry.time_submitted_at = datetime.now()
        entry.status = EntryStatus.TIME_SUBMITTED

    def submit_vod(self, session, entry, vod_url):
        if entry.status is not EntryStatus.TIME_SUBMITTED:
            raise ConsistencyError(
                "Attempt to register a VOD for a player that did not have a time submitted for their weekly."
            )
        entry.status = EntryStatus.DONE
        entry.vod_url = vod_url
        entry.vod_submitted_at = datetime.now()

    def submit_comment(self, session, entry, comment):
        entry.comment = comment

    def update_time(self, session, entry, new_time):
        if entry.status not in [EntryStatus.TIME_SUBMITTED, EntryStatus.DONE]:
            raise ConsistencyError(
                "Attempt to alter a time for a player that did not have submitted their time."
            )
        entry.finish_time = new_time

    def update_vod(self, session, entry, new_vod):
        if entry.status is not EntryStatus.DONE:
            raise ConsistencyError(
                "Attempt to alter a VOD for a player that did not have submitted their VOD."
            )
        entry.vod_url = new_vod

    def _generate_schema(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    @staticmethod
    def build_database_url(*, dialect, dbapi="", user="", password="", host="", port="", dbpath):
        def add_if_not_none(value, *, prefix="", suffix=""):
            if value is not None and len(value) > 0:
                return prefix + value + suffix
            return ""

        url = dialect + add_if_not_none(dbapi, prefix="+") + "://"
        auth = add_if_not_none(user) + add_if_not_none(password, prefix=":")
        url += add_if_not_none(auth, suffix="@") + host + add_if_not_none(port, prefix=":") + "/"
        url += dbpath

        return url
