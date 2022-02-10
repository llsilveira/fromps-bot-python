from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, aliased

from datetime import datetime, timedelta

from datatypes import PlayerStatus, EntryStatus, WeeklyStatus, LeaderboardStatus
from database.model import Player, PlayerEntry, Weekly, Leaderboard, LeaderboardEntry, Base

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
            status=PlayerStatus.ACTIVE,
            leaderboard_data={
                "excluded_from": [],
            }
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

    def create_weekly(self, session, game, seed_url, seed_hash, submission_end, leaderboard=None):
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
            submission_end=submission_end,
            leaderboard=leaderboard
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

    def get_player_entry(self, session, weekly_id, player_discord_id):
        return session.get(PlayerEntry, (weekly_id, player_discord_id))

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
            registered_at=datetime.now(),
            leaderboard_data={"excluded": self.excluded_from_leaderboard(self, player, weekly.game)}
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

    def get_leaderboard(self, session, leaderboard_id):
        return session.get(Leaderboard, leaderboard_id)

    def get_open_leaderboard(self, session, game):
        return session.execute(
            select(Leaderboard).where(Leaderboard.game == game, Leaderboard.status == LeaderboardStatus.OPEN).order_by(
                Leaderboard.created_at.desc()
            )
        ).scalars().first()

    def create_leaderboard(self, session, game, results_url=None):
        open_lb = self.get_open_leaderboard(session, game)
        if open_lb is not None:
            raise ConsistencyError(
                "Attempt to open a leaderboard while another one for the same game is still open"
            )

        lb = Leaderboard(
            game=game,
            results_url=results_url,
            status=LeaderboardStatus.OPEN,
            created_at=datetime.now(),
            leaderboard_data={
                "included_weeklies": "6",
                "weeklies": []
            }
        )
        session.add(lb)
        return lb

    def close_leaderboard(self, session, leaderboard):
        for weekly in leaderboard.weeklies:
            if weekly.status == WeeklyStatus.OPEN:
                raise ConsistencyError(
                    "Cannot close a leaderboard that has an open weekly."
                )
        leaderboard.status = LeaderboardStatus.CLOSED

    def get_last_closed_leaderboard(self, session, game):
        return session.execute(
            select(Leaderboard).where(
                Leaderboard.game == game, Leaderboard.status == LeaderboardStatus.CLOSED
            ).order_by(Leaderboard.created_at.desc())
        ).scalars().first()

    def reopen_leaderboard(self, session, leaderboard):
        if leaderboard.status is not LeaderboardStatus.CLOSED:
            raise ConsistencyError("Attempt to reopen a leaderboard that was not closed.")
        open_leaderboard = self.get_open_leaderboard(session, leaderboard.game)
        if open_leaderboard is not None:
            raise ConsistencyError(
                "Attempt to reopen a leaderboard while another one for the same game is open"
            )
        leaderboard.status = LeaderboardStatus.OPEN

    def get_leaderboard_entry(self, session, leaderboard_id, player_discord_id):
        return session.get(LeaderboardEntry, (leaderboard_id, player_discord_id))

    def create_leaderboard_entry(self, session, leaderboard, player):
        lb_entry = LeaderboardEntry(
            leaderboard=leaderboard,
            player=player,
            leaderboard_data={
                "weeklies": {},
                "total_points": 0,
                "final_points": 0
            }
        )
        session.add(lb_entry)
        return lb_entry

    def get_or_create_leaderboard_entry(self, session, leaderboard, player):
        lb_entry = self.get_leaderboard_entry(session, leaderboard.id, player.discord_id)
        if lb_entry is not None:
            return lb_entry
        return self.create_leaderboard_entry(session, leaderboard, player)

    def excluded_from_leaderboard(self, session, player, game):
        return game.name in player.leaderboard_data["excluded_from"]

    def exclude_from_leaderboard(self, session, player, game):
        if not self.excluded_from_leaderboard(session, player, game):
            player.leaderboard_data["excluded_from"] += [game.name]

    def include_on_leaderboard(self, session, player, game):
        if self.excluded_from_leaderboard(session, player, game):
            player.leaderboard_data["excluded_from"] = [
                g for g in player.leaderboard_data["excluded_from"] if g != game.name
            ]

    def get_head_to_head(self, session, game, player1_id, player2_id, initial_date=None, final_date=None):
        entry1 = aliased(PlayerEntry, name="entry1")
        entry2 = aliased(PlayerEntry, name="entry2")
        weekly = aliased(Weekly, name="weekly")

        stmt = select(entry1, entry2, weekly)\
            .join(entry2, entry1.weekly_id == entry2.weekly_id)\
            .join(weekly, entry1.weekly_id == weekly.id)\
            .where(
                entry1.player_discord_id == player1_id,
                entry2.player_discord_id == player2_id,
                weekly.game == game,
                weekly.status == WeeklyStatus.CLOSED
            )

        if initial_date is not None:
            compare_time = datetime.combine(initial_date, datetime.min.time())
            stmt = stmt.where(weekly.submission_end >= compare_time)

        if final_date is not None:
            compare_time = datetime.combine(final_date, datetime.min.time()) + timedelta(days=1)
            stmt = stmt.where(weekly.submission_end < compare_time)

        values = session.execute(stmt).all()
        ret = {}
        for row in values:
            ret[row.weekly.id] = {
                "weekly": row.weekly,
                "entries": [row.entry1, row.entry2]
            }
        return ret

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
