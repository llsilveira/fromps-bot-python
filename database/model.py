from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy import Column, Integer, BigInteger, String, Time, DateTime, Enum, ForeignKey, JSON
from datetime import datetime

from datatypes import Games, PlayerStatus, EntryStatus, WeeklyStatus, LeaderboardStatus


Base = declarative_base()


class Player(Base):
    __tablename__ = 'players'

    discord_id = Column(BigInteger, primary_key=True, autoincrement=False)
    name = Column(String(length=32), nullable=False)
    status = Column(Enum(PlayerStatus, native_enum=False, validate_strings=True, length=20), nullable=False)
    leaderboard_data = Column(MutableDict.as_mutable(JSON))

    weekly_entries = relationship("PlayerEntry", back_populates="player")  # bi-directional
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="player")  # bi-directional


class Weekly(Base):
    __tablename__ = 'weeklies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    game = Column(Enum(Games, native_enum=False, validate_strings=True, length=20), nullable=False)
    status = Column(Enum(WeeklyStatus, native_enum=False, validate_strings=True, length=20), nullable=False)
    seed_url = Column(String, nullable=False)
    seed_hash = Column(String)
    created_at = Column(DateTime, nullable=False)
    submission_end = Column(DateTime, nullable=False)
    leaderboard_id = Column(ForeignKey('leaderboards.id'))  # relationship: leaderboard

    entries = relationship("PlayerEntry", back_populates="weekly")  # bi-directional
    leaderboard = relationship("Leaderboard", back_populates="weeklies")  # bi-directional

    def is_open(self):
        return self.submission_end > datetime.now()


class PlayerEntry(Base):
    __tablename__ = 'player_entries'

    weekly_id = Column('weekly_id', ForeignKey('weeklies.id'), primary_key=True)  # relationship: weekly
    player_discord_id = Column(ForeignKey('players.discord_id'), primary_key=True)  # relationship: player
    status = Column(Enum(EntryStatus, native_enum=False, validate_strings=True, length=20), nullable=False)
    finish_time = Column(Time)
    print_url = Column(String)
    vod_url = Column(String)
    comment = Column(String)
    registered_at = Column(DateTime, nullable=False)
    time_submitted_at = Column(DateTime)
    vod_submitted_at = Column(DateTime)
    leaderboard_data = Column(MutableDict.as_mutable(JSON))

    weekly = relationship("Weekly", back_populates="entries")  # bi-directional
    player = relationship("Player", back_populates="weekly_entries")  # bi-directional


class Leaderboard(Base):
    __tablename__ = 'leaderboards'

    id = Column(Integer, primary_key=True, autoincrement=True)
    game = Column(Enum(Games, native_enum=False, validate_strings=True, length=20), nullable=False)
    results_url = Column(String)
    status = Column(Enum(LeaderboardStatus, native_enum=False, validate_strings=True, length=20), nullable=False)
    created_at = Column(DateTime, nullable=False)
    leaderboard_data = Column(MutableDict.as_mutable(JSON))

    weeklies = relationship("Weekly", back_populates='leaderboard')  # bi-directional
    entries = relationship("LeaderboardEntry", back_populates='leaderboard')  # bi-directional


class LeaderboardEntry(Base):
    __tablename__ = 'leaderboard_entries'

    leaderboard_id = Column(ForeignKey('leaderboards.id'), primary_key=True)  # relationship: leaderboard
    player_discord_id = Column(ForeignKey('players.discord_id'), primary_key=True) #relationship: player
    leaderboard_data = Column(MutableDict.as_mutable(JSON))

    leaderboard = relationship("Leaderboard", back_populates='entries')  # bi-directional
    player = relationship("Player", back_populates='leaderboard_entries')  # bi-directional
