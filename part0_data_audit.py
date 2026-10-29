"""
Part 0: Data audit for both seasons.

For every match: the official score from the match file, the score rebuilt from
the events, red cards, shots and xG for both teams, and minutes played.

Output: results/matches.csv, printed audit
"""

import concurrent.futures as cf
import os

import pandas as pd

from common import TEAMS, clock, goals, load_events, red_cards, side, team_matches


def match_row(label, team, m):
    ev = load_events(m["match_id"])
    tid, opp, oid, home = side(m, team)
    gf_off = m["home_score"] if home else m["away_score"]
    ga_off = m["away_score"] if home else m["home_score"]
    reds = red_cards(ev)

    def shots(team_id):
        s = [e for e in ev if e["type"]["name"] == "Shot" and e["team"]["id"] == team_id
             and e["period"] <= 4]
        np_ = [e for e in s if e["shot"].get("type", {}).get("name") != "Penalty"]
        return len(np_), sum(e["shot"].get("statsbomb_xg", 0) for e in np_), \
            sum(1 for e in s if e["shot"].get("type", {}).get("name") == "Penalty")

    s_f, xg_f, pen_f = shots(tid)
    s_a, xg_a, pen_a = shots(oid)
    return {
        "team": label, "match_id": m["match_id"], "date": m["match_date"],
        "week": m.get("match_week"), "opponent": opp, "home": home,
        "gf": gf_off, "ga": ga_off, "gf_events": goals(ev, tid), "ga_events": goals(ev, oid),
        "result": "W" if gf_off > ga_off else ("D" if gf_off == ga_off else "L"),
        "np_shots_for": s_f, "np_xg_for": xg_f, "pens_for": pen_f,
        "np_shots_against": s_a, "np_xg_against": xg_a, "pens_against": pen_a,
        "minutes": max(clock(e) for e in ev),
        "reds_for": sum(r[0] == tid for r in reds), "reds_against": sum(r[0] == oid for r in reds),
        "first_red_minute": min((r[2] for r in reds), default=None),
    }


def main():
    os.makedirs("results", exist_ok=True)
    rows = []
    for label, (_, _, team) in TEAMS.items():
        ms = team_matches(label)
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            rows += list(ex.map(lambda m: match_row(label, team, m), ms))
    M = pd.DataFrame(rows).sort_values(["team", "date"])
    M.to_csv("results/matches.csv", index=False)

    for label, g in M.groupby("team"):
        mism = g[(g.gf != g.gf_events) | (g.ga != g.ga_events)]
        print(f"{label}: {len(g)} matches, W{(g.result == 'W').sum()} D{(g.result == 'D').sum()} "
              f"L{(g.result == 'L').sum()}, goals {g.gf.sum()}-{g.ga.sum()}, "
              f"points {3 * (g.result == 'W').sum() + (g.result == 'D').sum()}")
        print(f"   scores rebuilt from events: {len(g) - len(mism)} of {len(g)} match "
              f"exactly{'' if mism.empty else '; mismatches: ' + str(mism[['opponent', 'gf', 'gf_events', 'ga', 'ga_events']].values.tolist())}")
        print(f"   per match: np xG {g.np_xg_for.mean():.2f} for, {g.np_xg_against.mean():.2f} "
              f"against; np shots {g.np_shots_for.mean():.1f} for, "
              f"{g.np_shots_against.mean():.1f} against; penalties {g.pens_for.sum()} for, "
              f"{g.pens_against.sum()} against")
        r = g[g.first_red_minute.notna()]
        print(f"   matches with a red card: {len(r)} "
              + ", ".join(f"v {x.opponent} ({int(x.first_red_minute)}', "
                          f"{'own' if x.reds_for else 'opponent'})" for x in r.itertuples()))
        print(f"   match length (last event): {g.minutes.min():.0f} to {g.minutes.max():.0f} min\n")


if __name__ == "__main__":
    main()
