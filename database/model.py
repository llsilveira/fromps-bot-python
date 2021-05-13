from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Time, DateTime, Enum, ForeignKey
from datetime import datetime

from datatypes import Games, EntryStatus, WeeklyStatus


Base = declarative_base()


class Weekly(Base):
    __tablename__ = 'weeklies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    game = Column(Enum(Games, native_enum=False, validate_strings=True, length=20), nullable=False)
    status = Column(Enum(WeeklyStatus, native_enum=False, validate_strings=True, length=20), nullable=False)
    seed_url = Column(String, nullable=False)
    seed_hash = Column(String)
    created_at = Column(DateTime, nullable=False)
    submission_end = Column(DateTime, nullable=False)

    entries = relationship("PlayerEntry")

    def is_open(self):
        return self.submission_end > datetime.now()


class PlayerEntry(Base):
    __tablename__ = 'player_entries'

    weekly_id = Column('weekly_id', ForeignKey('weeklies.id'), primary_key=True)
    discord_id = Column(Integer, primary_key=True)
    discord_name = Column(String, nullable=False)
    status = Column(Enum(EntryStatus, native_enum=False, validate_strings=True, length=20), nullable=False)
    finish_time = Column(Time)
    print_url = Column(String)
    vod_url = Column(String)
    registered_at = Column(DateTime, nullable=False)
    time_submitted_at = Column(DateTime)
    vod_submitted_at = Column(DateTime)

    weekly = relationship("Weekly", back_populates="entries")
