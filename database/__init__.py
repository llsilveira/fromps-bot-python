from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, scoped_session

from datetime import datetime

from datatypes import Games
from database.model import PlayerEntry, Weekly, Base


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
            engine_options={}
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
        self.engine = create_engine(url, **engine_options, future=True)
        self.Session = scoped_session(sessionmaker(self.engine, future=True))

    def get_weekly(self, selector):
        if isinstance(selector, Games):
            return self.get_current_weekly(selector)
        return self.Session.get(Weekly, selector)

    def get_current_weekly(self, game):
        return self.Session.execute(
            select(Weekly)
                .where(Weekly.game == game)
                .order_by(Weekly.created_at.desc())
        ).scalars().first()

    def create_weekly(self, game, seed_url, seed_hash, submission_end):
        weekly = Weekly(
            game=game,
            seed_url=seed_url,
            seed_hash=seed_hash,
            created_at=datetime.now(),
            submission_end=submission_end
        )
        self.Session.add(weekly)
        self.Session.commit()
        return weekly

    def update_weekly(self, selector, **kwargs):
        weekly = self.get_weekly(selector)
        if weekly is not None:
            for key, value in kwargs.items():
                setattr(weekly, key, value)
            self.Session.commit()

    def close_current_weekly(self, game):
        self.update_weekly(game, submission_end=datetime.now())

    def get_player_entry(self, weekly, discord_id):
        return self.Session.get(PlayerEntry, (weekly.id, discord_id))

    def register(self, weekly, discord_id, discord_name):
        entry = PlayerEntry(
            weekly=weekly,
            discord_id=discord_id,
            discord_name=discord_name,
            registered_at=datetime.now()
        )
        self.Session.add(entry)
        self.Session.commit()
        return entry

    def submit_time(self, weekly, discord_id, finish_time, print_url):
        entry = self.get_player_entry(weekly, discord_id)
        entry.finish_time = finish_time
        entry.print_url = print_url
        entry.time_submitted_at = datetime.now()
        self.Session.commit()

    def submit_vod(self, weekly, discord_id, vod_url):
        entry = self.get_player_entry(weekly, discord_id)
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
