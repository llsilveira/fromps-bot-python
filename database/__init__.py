from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, scoped_session

from datetime import datetime

from datatypes import EntryStatus, WeeklyStatus
from database.model import PlayerEntry, Weekly, Base

#TODO: properly treat errors with rollback

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
        self.Session = scoped_session(sessionmaker(self.engine, future=True))

    def get_weekly(self, id):
        return self.Session.get(Weekly, id)

    def get_open_weekly(self, game):
        return self.Session.execute(
            select(Weekly)
                .where(Weekly.game == game, Weekly.status == WeeklyStatus.OPEN)
                .order_by(Weekly.created_at.desc())
        ).scalars().first()

    def create_weekly(self, game, seed_url, seed_hash, submission_end, *, force_close=False):
        open_weekly = self.get_open_weekly(game)
        if open_weekly is not None:
            if force_close:
                self.close_weekly(open_weekly)
            else:
                #TODO: definir exceção
                raise

        weekly = Weekly(
            game=game,
            status=WeeklyStatus.OPEN,
            seed_url=seed_url,
            seed_hash=seed_hash,
            created_at=datetime.now(),
            submission_end=submission_end
        )
        self.Session.add(weekly)
        self.Session.commit()
        return weekly

    def close_weekly(self, weekly):
        for entry in weekly.entries:
            if entry.status != EntryStatus.DONE and entry.status != EntryStatus.DNF:
                entry.status = EntryStatus.DNF
        weekly.status = WeeklyStatus.CLOSED
        self.Session.commit()

    def get_player_entry(self, weekly, discord_id):
        return self.Session.get(PlayerEntry, (weekly.id, discord_id))

    def get_registered_entry(self, discord_id):
        registered = self.Session.execute(
            select(PlayerEntry).where(PlayerEntry.discord_id == discord_id, PlayerEntry.status == EntryStatus.REGISTERED)
        ).scalars().all()

        if len(registered) == 0:
            return None

        if len(registered) > 1:
            #TODO: log as a consistency error
            pass
        return registered[0]

    def register_player(self, weekly, discord_id, discord_name):
        if self.get_registered_entry(discord_id) is not None:
            #TODO: error and log
            return None

        entry = PlayerEntry(
            weekly=weekly,
            discord_id=discord_id,
            discord_name=discord_name,
            status=EntryStatus.REGISTERED,
            registered_at=datetime.now()
        )
        self.Session.add(entry)
        self.Session.commit()
        return entry

    def forfeit_player(self, weekly, discord_id):
        entry = self.get_player_entry(weekly, discord_id)
        if entry.status != EntryStatus.REGISTERED:
            #TODO: definir exceção
            raise
        entry.status = EntryStatus.DNF
        self.Session.commit()

    def submit_time(self, weekly, discord_id, finish_time, print_url):
        entry = self.get_player_entry(weekly, discord_id)
        if entry.status != EntryStatus.REGISTERED:
            #TODO: definir exceção
            raise
        entry.finish_time = finish_time
        entry.print_url = print_url
        entry.time_submitted_at = datetime.now()
        entry.status = EntryStatus.TIME_SUBMITTED
        self.Session.commit()

    def submit_vod(self, weekly, discord_id, vod_url):
        entry = self.get_player_entry(weekly, discord_id)
        if entry.status != EntryStatus.TIME_SUBMITTED:
            #TODO: definir exceção
            raise
        entry.status = EntryStatus.DONE
        entry.vod_url = vod_url
        entry.vod_submitted_at = datetime.now()
        self.Session.commit()

    def _generate_schema(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session.remove()

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
