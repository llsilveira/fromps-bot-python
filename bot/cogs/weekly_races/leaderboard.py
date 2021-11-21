from functools import reduce
from datetime import time

from datatypes.enums import PlayerStatus
from util import time_to_timedelta
from bot.exceptions import FrompsBotException


def update_leaderboard(db, session, leaderboard):
    sorted_entries = sorted(
        filter(lambda e: e.player.status is PlayerStatus.ACTIVE, leaderboard.entries),
        key=lambda e: e.leaderboard_data["final_points"],
        reverse=True
    )

    def finished_weeklies(entry):
        return set(filter(
            lambda k: not entry.leaderboard_data["weeklies"][k]["discarded"]
                and entry.leaderboard_data["weeklies"][k]["points"] > 0,
            entry.leaderboard_data["weeklies"].keys()
        ))

    tied_entries = []
    tiebreak_data = {}
    pos = 1
    while len(sorted_entries) > 0:
        tied_entries.append(sorted_entries.pop(0))
        if len(sorted_entries) > 0 and (
                sorted_entries[0].leaderboard_data["final_points"] == tied_entries[0].leaderboard_data["final_points"]
        ):
            continue

        if len(tied_entries) == 1:
            tied_entries[0].leaderboard_data["position"] = pos
            tied_entries[0].leaderboard_data["tiebreak"] = None
            pos += 1
            tied_entries = []
        else:
            common_weeklies = finished_weeklies(tied_entries[0])
            for i in range(1, len(tied_entries)):
                common_weeklies &= finished_weeklies(tied_entries[i])
            tiebreak_data[pos] = {
                "common_weeklies": sorted(list(common_weeklies))
            }

            max_time = time(23, 59, 59)
            for e in tied_entries:
                common_points = reduce(lambda a, w: a + e.leaderboard_data["weeklies"][w]["points"], common_weeklies, 0)
                minimum_time = max_time
                for w in common_weeklies:
                    player_entry = db.get_player_entry(
                        session,
                        leaderboard.leaderboard_data["weeklies"][int(w)],
                        e.player_discord_id
                    )
                    if minimum_time > player_entry.finish_time:
                        minimum_time = player_entry.finish_time
                e.leaderboard_data["tiebreak"] = {
                    "common_points": common_points,
                    "minimum_time": int(time_to_timedelta(minimum_time).total_seconds())
                }

            max_time = int(time_to_timedelta(max_time).total_seconds())
            tied_entries = sorted(
                tied_entries,
                key=lambda e: (
                    e.leaderboard_data["tiebreak"]["common_points"],
                    max_time - e.leaderboard_data["tiebreak"]["minimum_time"]
                ),
                reverse=True
            )

            still_tied = []
            while len(tied_entries) > 0:
                still_tied.append(tied_entries.pop(0))
                if len(tied_entries) > 0:
                    common_points = still_tied[0].leaderboard_data["tiebreak"]["common_points"]
                    minimum_time = still_tied[0].leaderboard_data["tiebreak"]["minimum_time"]
                    if tied_entries[0].leaderboard_data["tiebreak"]["common_points"] == common_points\
                            and tied_entries[0].leaderboard_data["tiebreak"]["minimum_time"] == minimum_time:
                        continue

                for e in still_tied:
                    e.leaderboard_data["position"] = pos
                pos += len(still_tied)
                still_tied = []

    leaderboard.leaderboard_data["tiebreak_data"] = tiebreak_data


def update_leaderboard_entry(db, session, player_entry, week_number, included_weeklies):
    data = player_entry.leaderboard_data
    lb_entry = db.get_or_create_leaderboard_entry(session, player_entry.weekly.leaderboard, player_entry.player)
    lb_entry.leaderboard_data["weeklies"][str(week_number)] = {
        "points": data["points"]
    }

    sorted_weeklies = sorted(
        sorted(lb_entry.leaderboard_data["weeklies"].keys(), key=int),
        key=lambda w: lb_entry.leaderboard_data["weeklies"][w]["points"],
        reverse=True
    )

    total_points = 0
    final_points = 0
    for i in range(len(sorted_weeklies)):
        result = lb_entry.leaderboard_data["weeklies"][sorted_weeklies[i]]
        total_points += result["points"]

        if i < included_weeklies:
            result["discarded"] = False
            final_points += result["points"]
        else:
            result["discarded"] = True

    lb_entry.leaderboard_data["total_points"] = total_points
    lb_entry.leaderboard_data["final_points"] = final_points


def update_weekly(db, session, weekly):
    lb = weekly.leaderboard
    if lb is None:
        raise FrompsBotException("A semanal escolhida não faz parte de uma leaderboard.")

    try:
        week_number = lb.leaderboard_data["weeklies"].index(weekly.id)
    except ValueError:
        week_number = len(lb.leaderboard_data["weeklies"])
        lb.leaderboard_data["weeklies"] += [weekly.id]
    included_weeklies = int(lb.leaderboard_data["included_weeklies"])

    def points_generator():
        for i in 15, 13, 12, 10, 9, 8, 7, 6, 5, 4, 3, 2:
            yield i
        while True:
            yield 1

    included_entries = list(filter(lambda e: not e.leaderboard_data["excluded"], weekly.entries))
    finished = sorted(
        list(filter(lambda e: e.finish_time is not None, included_entries)),
        key=lambda e: e.finish_time
    )
    points = points_generator()
    tied_entries = []
    pos = 1
    while len(finished) > 0:
        tied_entries.append(finished.pop(0))
        if len(finished) > 0 and finished[0].finish_time == tied_entries[0].finish_time:
            continue

        acc_points = 0
        for i in range(len(tied_entries)):
            acc_points += next(points)
        acc_points /= len(tied_entries)

        for entry in tied_entries:
            entry.leaderboard_data.update({
                "position": str(pos),
                "points": acc_points
            })
            update_leaderboard_entry(db, session, entry, week_number, included_weeklies)

        pos += len(tied_entries)
        tied_entries = []

    not_finished = list(filter(lambda e: e.finish_time is None, included_entries))
    for entry in not_finished:
        entry.leaderboard_data.update({
            "position": "DNF",
            "points": 0
        })
        update_leaderboard_entry(db, session, entry, week_number, included_weeklies)
