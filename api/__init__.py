from quart import Quart, jsonify
from util import time_to_timedelta


def create_api(db, config):
    api = Quart(__name__)
    api.secret_key = config["secret_key"]

    @api.route("/leaderboard/<int:id>", methods=['GET'])
    async def leaderboard(id):
        with db.Session() as session:
            lb = db.get_leaderboard(session, id)
            if lb is None:
                return jsonify({
                    "error": "Não existe uma Leaderboard com id %d" % id
                }), 404
            entries = sorted(
                filter(lambda e: e.leaderboard_data.get("position", None) is not None, lb.entries),
                key=lambda e: e.leaderboard_data["position"]
            )
            return jsonify(
                id=lb.id,
                game=lb.game.name,
                status=lb.status.name,
                created_at=lb.created_at,
                data=lb.leaderboard_data,
                entries=[
                    {
                        "name": e.player.name,
                        "position": e.leaderboard_data["position"],
                        "points": e.leaderboard_data["final_points"],
                        "weeklies": e.leaderboard_data["weeklies"]
                    } for e in entries
                ]
            )

    @api.route("/leaderboard/<int:id>/<int:week_id>", methods=['GET'])
    async def leaderboard_week(id, week_id):
        with db.Session() as session:
            lb = db.get_leaderboard(session, id)
            if lb is None:
                return jsonify({
                    "error": "Não existe uma Leaderboard com id %d" % id
                }), 404
            if week_id <= 0 or week_id > len(lb.leaderboard_data["weeklies"]):
                return jsonify({
                    "A leaderboard selecionada não possuí a semanal #%d" % (week_id + 1)
                }), 404

            weekly = db.get_weekly(session, lb.leaderboard_data["weeklies"][week_id - 1])
            entries = sorted(
                filter(lambda e: not e.leaderboard_data.get("excluded", False), weekly.entries),
                key=lambda e: e.leaderboard_data["points"],
                reverse=True
            )
            return jsonify(
                leaderboard_id=lb.id,
                leaderboard_week=week_id,
                weekly_id=weekly.id,
                game=weekly.game.name,
                status=weekly.status.name,
                created_at=weekly.created_at,
                seed=weekly.seed_url,
                hash=weekly.seed_hash,
                entries=[
                    {
                        "name": e.player.name,
                        "position": e.leaderboard_data["position"],
                        "points": e.leaderboard_data["points"],
                        "time": None if e.finish_time is None else int(time_to_timedelta(e.finish_time).total_seconds())
                    } for e in entries
                ]
            )

    return api
