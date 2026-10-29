"""
Part 2: The escapes. Trailing, comebacks and late goals.

  Game state: the score at every moment of each match (match clock from the
  events; stoppage time included). Minutes leading / level / trailing.
  Comebacks: matches where they trailed at some point, and the points they took.
  Late goals: goals from the 85th minute onwards (StatsBomb minute >= 85),
  and stoppage-time goals (second-half minute >= 90).
  Points from late goals: points with the score at 84:59 vs the final score.
  Late finishing: goals vs non-penalty xG from the 85th minute, and the
  probability of scoring at least that many late goals from those chances.

Output: results/game_state.csv, results/late_goals.csv, printed tables
"""

import numpy as np
import pandas as pd

from common import TEAMS, clock, load_events, side, team_matches

LATE = 85


def pts(gf, ga):
    return 3 if gf > ga else (1 if gf == ga else 0)


def scoring_events(ev, tid, oid):
    """List of (clock, team_id) for every goal, in order."""
    out = []
    for e in ev:
        t = e["type"]["name"]
        if (t == "Shot" and e["shot"]["outcome"]["name"] == "Goal") or t == "Own Goal For":
            out.append((clock(e), e["team"]["id"], e["minute"], e["period"]))
    return sorted(out)


def poisson_binomial_ge(ps, k):
    d = np.array([1.0])
    for p in ps:
        d = np.convolve(d, [1 - p, p])
    return d[k:].sum()


def main():
    rows, late = [], []
    for label, (_, _, team) in TEAMS.items():
        for m in team_matches(label):
            ev = load_events(m["match_id"])
            tid, opp, oid, home = side(m, team)
            end = max(clock(e) for e in ev)
            goals = scoring_events(ev, tid, oid)
            pens = {(clock(e), e["team"]["id"], e["minute"]) for e in ev
                    if e["type"]["name"] == "Shot" and e["shot"]["outcome"]["name"] == "Goal"
                    and e["shot"].get("type", {}).get("name") == "Penalty"}
            t_prev, gf, ga = 0.0, 0, 0
            state = {"leading": 0.0, "level": 0.0, "trailing": 0.0}
            trailed = False
            gf85 = ga85 = None
            for c, team_id, minute, period in goals:
                if gf85 is None and c >= LATE:
                    gf85, ga85 = gf, ga
                key = "leading" if gf > ga else ("level" if gf == ga else "trailing")
                state[key] += c - t_prev
                t_prev = c
                if team_id == tid:
                    gf += 1
                else:
                    ga += 1
                trailed |= gf < ga
                if minute >= LATE:
                    late.append({"team": label, "opponent": opp, "date": m["match_date"],
                                 "minute": minute, "stoppage": period == 2 and minute >= 90,
                                 "for": team_id == tid, "score_after": f"{gf}-{ga}",
                                 "penalty": (c, team_id, minute) in pens})
            key = "leading" if gf > ga else ("level" if gf == ga else "trailing")
            state[key] += end - t_prev
            if gf85 is None:
                gf85, ga85 = gf, ga
            # late chances (non-penalty) for and against
            def late_xg(team_id):
                return [e["shot"].get("statsbomb_xg", 0) for e in ev
                        if e["type"]["name"] == "Shot" and e["team"]["id"] == team_id
                        and e["minute"] >= LATE and e["shot"].get("type", {}).get("name") != "Penalty"]
            rows.append({"team": label, "date": m["match_date"], "opponent": opp, "home": home,
                         "gf": gf, "ga": ga, "trailed": trailed, **state, "minutes": end,
                         "pts_at_85": pts(gf85, ga85), "pts_final": pts(gf, ga),
                         "late_xg_for": late_xg(tid), "late_xg_against": late_xg(oid),
                         "late_goals_for": gf - gf85, "late_goals_against": ga - ga85})
    G = pd.DataFrame(rows)
    L = pd.DataFrame(late)
    G.drop(columns=["late_xg_for", "late_xg_against"]).to_csv("results/game_state.csv", index=False)
    L.to_csv("results/late_goals.csv", index=False)

    for label, g in G.groupby("team"):
        tot = g[["leading", "level", "trailing"]].sum()
        share = tot / tot.sum()
        tr = g[g.trailed]
        swing = (g.pts_final - g.pts_at_85)
        lf = [x for v in g.late_xg_for for x in v]
        la = [x for v in g.late_xg_against for x in v]
        lgf, lga = int(g.late_goals_for.sum()), int(g.late_goals_against.sum())
        l = L[L.team == label]
        print(f"{label}")
        print(f"  time leading {share.leading:.0%}, level {share.level:.0%}, trailing "
              f"{share.trailing:.0%} ({tot.trailing:.0f} minutes trailing in total)")
        print(f"  trailed at some point in {len(tr)} of {len(g)} matches; took "
              f"{int(tr.pts_final.sum())} of {3 * len(tr)} points from them "
              f"(W{(tr.gf > tr.ga).sum()} D{(tr.gf == tr.ga).sum()})")
        print(f"  goals from minute {LATE}: {lgf} for, {lga} against; stoppage-time goals for "
              f"{int((l['for'] & l.stoppage).sum())}")
        print(f"  points changed by goals from minute {LATE}: +{int(swing[swing > 0].sum())} "
              f"gained, {int(swing[swing < 0].sum())} lost, net {int(swing.sum()):+d}")
        print(f"  late non-penalty chances: {len(lf)} shots, {sum(lf):.2f} xG for; "
              f"{len(la)} shots, {sum(la):.2f} xG against")
        npl = int((l["for"] & ~l.penalty).sum())  # non-penalty late goals (incl. own goals)
        print(f"  non-penalty late goals {npl} from {sum(lf):.2f} np xG; chance of {npl}+ "
              f"with average finishing: {poisson_binomial_ge(lf, npl):.3f}")
        sv = g[swing > 0][["date", "opponent", "gf", "ga", "pts_at_85", "pts_final"]]
        print("  matches rescued or won late:")
        print("   " + sv.to_string(index=False).replace("\n", "\n   "))
        print()


if __name__ == "__main__":
    main()
