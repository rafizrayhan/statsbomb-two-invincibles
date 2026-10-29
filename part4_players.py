"""
Part 4: The players.

Minutes: starters from the Starting XI event; substitutions and red cards
(straight red or second yellow) end or start a player's time. Match length =
last event on the match clock.

Per player (league, full matches): minutes, starts, goals, penalties, non-penalty
goals, assists (passes marked goal_assist), non-penalty xG, xA (xG of shots
assisted by their key passes), and per-90 rates for players with 900+ minutes.

Team: number of players used, different scorers, players with 5+ goals, the
top scorer's share of goals, the top three's share of goals plus assists and of non-penalty xG, and how
many players played half the league minutes or more.

Output: results/players.csv, printed tables
"""

import numpy as np
import pandas as pd

from common import TEAMS, clock, load_events, side, team_matches

MIN90 = 900
RED = {"Red Card", "Second Yellow"}


def card(e):
    for k in ("foul_committed", "bad_behaviour"):
        c = e.get(k, {}).get("card", {}).get("name")
        if c:
            return c
    return None


def minutes(ev, tid):
    end = max(clock(e) for e in ev)
    on, out = {}, {}
    for e in ev:
        if e["team"]["id"] != tid:
            continue
        t = e["type"]["name"]
        if t == "Starting XI":
            for p in e["tactics"]["lineup"]:
                on[p["player"]["name"]] = 0.0
        elif t == "Substitution":
            out[e["player"]["name"]] = clock(e)
            on[e["substitution"]["replacement"]["name"]] = clock(e)
        elif card(e) in RED and "player" in e:
            out[e["player"]["name"]] = clock(e)
    return {p: out.get(p, end) - s for p, s in on.items()}, \
        {p for p, s in on.items() if s == 0.0}


def main():
    rows, team_rows = [], []
    for label, (_, _, team) in TEAMS.items():
        acc = {}
        n_matches = 0
        team_mins = 0.0
        for m in team_matches(label):
            ev = load_events(m["match_id"])
            tid, opp, oid, home = side(m, team)
            n_matches += 1
            team_mins += max(clock(e) for e in ev)
            mins, starters = minutes(ev, tid)
            for p, v in mins.items():
                a = acc.setdefault(p, dict(minutes=0, apps=0, starts=0, goals=0, pens=0,
                                           assists=0, npxg=0.0, xa=0.0, shots=0))
                a["minutes"] += v
                a["apps"] += 1
                a["starts"] += p in starters
            shots = {e["id"]: e for e in ev if e["type"]["name"] == "Shot"}
            for e in ev:
                if e["team"]["id"] != tid or "player" not in e or e["period"] > 4:
                    continue
                p = e["player"]["name"]
                a = acc.setdefault(p, dict(minutes=0, apps=0, starts=0, goals=0, pens=0,
                                           assists=0, npxg=0.0, xa=0.0, shots=0))
                if e["type"]["name"] == "Shot":
                    pen = e["shot"].get("type", {}).get("name") == "Penalty"
                    g = e["shot"]["outcome"]["name"] == "Goal"
                    a["goals"] += g
                    a["pens"] += g and pen
                    if not pen:
                        a["npxg"] += e["shot"].get("statsbomb_xg", 0)
                        a["shots"] += 1
                elif e["type"]["name"] == "Pass":
                    a["assists"] += bool(e["pass"].get("goal_assist"))
                    sid = e["pass"].get("assisted_shot_id")
                    if sid in shots:
                        a["xa"] += shots[sid]["shot"].get("statsbomb_xg", 0)
        P = pd.DataFrame(acc).T.reset_index().rename(columns={"index": "player"})
        P["team"] = label
        P["np_goals"] = P.goals - P.pens
        for c in ["np_goals", "assists", "npxg", "xa"]:
            P[c + "_90"] = np.where(P.minutes >= MIN90, P[c] / P.minutes * 90, np.nan)
        P["ga"] = P.goals + P.assists
        rows.append(P)

        tg = P.goals.sum()
        own = None
        top3 = P.sort_values("ga", ascending=False).head(3)
        team_rows.append({
            "team": label, "matches": n_matches,
            "players_used": int((P.minutes > 0).sum()),
            "players_half_minutes": int((P.minutes >= team_mins / 2).sum()),
            "different_scorers": int((P.goals > 0).sum()),
            "players_5plus_goals": int((P.goals >= 5).sum()),
            "player_goals": int(tg),
            "top_scorer": P.sort_values("goals").iloc[-1].player,
            "top_scorer_goals": int(P.goals.max()),
            "top_scorer_share": P.goals.max() / tg,
            "top3_ga": ", ".join(top3.player),
            "top3_share_of_ga": top3.ga.sum() / P.ga.sum(),
            "top3_share_npxg": (P.sort_values("npxg", ascending=False).head(3).npxg.sum())
            / P.npxg.sum(),
        })
    A = pd.concat(rows)
    A.to_csv("results/players.csv", index=False)
    T = pd.DataFrame(team_rows).set_index("team").T
    pd.set_option("display.width", 220)
    print(T.to_string())
    for label, g in A.groupby("team"):
        print(f"\n{label}: top 10 by goals + assists")
        g = g.sort_values(["ga", "goals"], ascending=False).head(10)
        g = g.assign(minutes=g.minutes.astype(float).round(0))
        print(g[["player", "minutes", "starts", "goals", "pens", "assists", "npxg", "xa",
                 "np_goals_90", "assists_90", "npxg_90", "xa_90"]]
              .to_string(index=False, float_format=lambda v: f"{v:.2f}"))


if __name__ == "__main__":
    main()
