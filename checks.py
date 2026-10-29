"""
Checks for the whole project.

  1. Results: scores rebuilt from events match the official scores (all matches).
  2. xG calibration: goals against xG for every shot in these matches (both teams),
     and each team's non-penalty goals against non-penalty xG, for and against.
  3. Simulation check: the exact P(defeat) per match (Poisson-binomial goals for each
     side, no random numbers) against the 20,000-replay estimate.
  4. Sensitivity of P(unbeaten): shot model, possession model, and every shot's xG
     scaled by the season's calibration factor (goals / xG), and by 0.9 and 1.1.
  5. Red cards: key style measures with and without the 11 v 11 cut.
  6. Game state: points against expected points, and how many of the 'lost on xG'
     matches they were leading when the shots that tipped the xG came.

Output: printed report, results/checks.txt
"""

import contextlib
import io

import numpy as np
import pandas as pd

import part3_style
from common import TEAMS, load_events, side, team_matches
from part1_dominance import chances


def dist(ps):
    d = np.array([1.0])
    for p in ps:
        d = np.convolve(d, [1 - p, p])
    return d


def exact(pf, pa):
    f, a = dist(pf), dist(pa)
    joint = np.outer(f, a)
    i, j = np.indices(joint.shape)
    return joint[i > j].sum(), joint[i == j].sum(), joint[i < j].sum()


def main():
    out = io.StringIO()

    def say(*a):
        print(*a)
        print(*a, file=out)

    M = pd.read_csv("results/matches.csv")
    P = pd.read_csv("results/match_probabilities.csv")
    S = pd.read_csv("results/season_summary.csv", index_col=0)

    say("1. Results")
    for t, g in M.groupby("team"):
        ok = ((g.gf == g.gf_events) & (g.ga == g.ga_events)).sum()
        say(f"   {t}: {ok} of {len(g)} scores rebuilt exactly; W{(g.result == 'W').sum()} "
            f"D{(g.result == 'D').sum()} L{(g.result == 'L').sum()}")

    say("\n2. xG calibration")
    cache = {}
    for label, (_, _, team) in TEAMS.items():
        allg = allx = 0
        for m in team_matches(label):
            ev = load_events(m["match_id"])
            tid, opp, oid, home = side(m, team)
            cache[m["match_id"]] = (label, ev, tid, oid)
            for e in ev:
                if e["type"]["name"] == "Shot" and e["period"] <= 4:
                    allx += e["shot"].get("statsbomb_xg", 0)
                    allg += e["shot"]["outcome"]["name"] == "Goal"
        say(f"   {label}: all shots in these matches {allg} goals from {allx:.1f} xG "
            f"(ratio {allg / allx:.2f})")
        S.loc[label, "calib"] = allg / allx

    say("\n3. Exact match probabilities against the simulation (shot model)")
    rows = []
    for _, r in P.iterrows():
        label, ev, tid, oid = cache[r.match_id]
        w, d, l = exact(chances(ev, tid, False), chances(ev, oid, False))
        rows.append((label, w, d, l, r.p_loss_shot, 3 * w + d))
    E = pd.DataFrame(rows, columns=["team", "w", "d", "l", "l_sim", "xpts"])
    for t, g in E.groupby("team"):
        say(f"   {t}: largest gap in P(defeat) {np.abs(g.l - g.l_sim).max():.4f}; "
            f"P(unbeaten) exact {np.prod(1 - g.l):.5f} (1 in {1 / np.prod(1 - g.l):,.0f}), "
            f"simulated {S.loc[t, 'p_unbeaten_shot']:.5f}")

    say("\n4. Sensitivity of P(unbeaten)")
    for label in TEAMS:
        res = {"shot model": S.loc[label, "p_unbeaten_shot"],
               "possession model": S.loc[label, "p_unbeaten_poss"]}
        for name, k in [("xG x calibration", S.loc[label, "calib"]), ("xG x 0.9", 0.9),
                        ("xG x 1.1", 1.1)]:
            pu = 1.0
            for mid, (lab, ev, tid, oid) in cache.items():
                if lab != label:
                    continue
                pf = [min(x * k, 0.99) for x in chances(ev, tid, False)]
                pa = [min(x * k, 0.99) for x in chances(ev, oid, False)]
                pu *= 1 - exact(pf, pa)[2]
            res[name] = pu
        say(f"   {label}: " + "; ".join(f"{k} 1 in {1 / v:,.0f}" for k, v in res.items()))

    say("\n5. Red cards: style with and without the 11 v 11 cut")
    keys = ["passes_per_poss", "long_share", "pressure_opp_half", "def_height", "np_xg",
            "opp_np_xg"]
    full_rows, cut_rows = [], []
    for mid, (label, ev, tid, oid) in cache.items():
        cut_rows.append({"team": label, **part3_style.style(ev, tid, oid)})
        orig = part3_style.eleven_v_eleven
        part3_style.eleven_v_eleven = lambda e: (e, None)
        with contextlib.redirect_stdout(io.StringIO()):
            full_rows.append({"team": label, **part3_style.style(ev, tid, oid)})
        part3_style.eleven_v_eleven = orig
    C = pd.DataFrame(cut_rows).groupby("team")[keys].mean()
    F = pd.DataFrame(full_rows).groupby("team")[keys].mean()
    for t in C.index:
        say(f"   {t}: " + "; ".join(f"{k} {C.loc[t, k]:.2f} (all play {F.loc[t, k]:.2f})"
                                     for k in keys))

    say("\n6. Game state and expected points")
    for t, g in E.groupby("team"):
        pts = S.loc[t, "points"]
        say(f"   {t}: {pts} points from {g.xpts.sum():.1f} expected (exact). "
            f"Teams that lead often sit back and give up shots late, so xPts tends to "
            f"underrate strong sides; part 2 shows how often each team led.")

    open("results/checks.txt", "w").write(out.getvalue())


if __name__ == "__main__":
    main()
