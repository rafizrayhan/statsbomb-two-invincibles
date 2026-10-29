"""
Part 1: How dominant were they, and how likely was an unbeaten season?

  A. Dominance per match: xG for and against, possession (time on the ball),
     field tilt, and matches "won" on xG. Style-type measures (possession,
     field tilt) use 11 v 11 play only; xG and results use full matches.
  B. Match simulation: every shot (both teams, penalties included at their xG)
     is scored with probability = its xG; 20,000 replays per match give each
     match's chance of a win, draw and loss.
     Possession version (stricter): shots in the same possession are combined
     into one chance, P(goal) = 1 - prod(1 - xG), so rebounds are not double counted.
  C. Season: expected points, expected losses, and P(unbeaten) =
     product over matches of (1 - P(loss)), plus the full distribution of losses.

Output: results/match_probabilities.csv, results/season_summary.csv
"""

import numpy as np
import pandas as pd

from common import TEAMS, eleven_v_eleven, load_events, side, team_matches

SIMS = 20_000
SET_PIECES = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}


def ts(e):
    h, m, s = e["timestamp"].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def chances(events, team_id, by_possession):
    """List of goal probabilities for team_id's chances in the match."""
    shots = [e for e in events if e["type"]["name"] == "Shot" and e["team"]["id"] == team_id
             and e["period"] <= 4]
    if not by_possession:
        return [e["shot"].get("statsbomb_xg", 0) for e in shots]
    grp = {}
    for e in shots:
        grp.setdefault((e["period"], e["possession"]), []).append(e["shot"].get("statsbomb_xg", 0))
    return [1 - np.prod([1 - x for x in v]) for v in grp.values()]


def simulate(p_for, p_against, rng):
    gf = (rng.random((SIMS, len(p_for))) < np.array(p_for)).sum(axis=1) if p_for else np.zeros(SIMS)
    ga = (rng.random((SIMS, len(p_against))) < np.array(p_against)).sum(axis=1) \
        if p_against else np.zeros(SIMS)
    return (gf > ga).mean(), (gf == ga).mean(), (gf < ga).mean()


def possession_tilt(events, tid, oid):
    ev, _ = eleven_v_eleven(events)
    spans = {}
    for e in ev:
        if e["period"] > 2:
            continue
        k = (e["period"], e["possession"])
        t = ts(e)
        lo, hi, team = spans.get(k, (t, t, e["possession_team"]["id"]))
        spans[k] = (min(lo, t), max(hi, t), team)
    own = sum(hi - lo for lo, hi, t in spans.values() if t == tid)
    tot = sum(hi - lo for lo, hi, t in spans.values())
    ft = {tid: 0, oid: 0}
    for e in ev:
        if e["type"]["name"] == "Pass" and e["pass"].get("type", {}).get("name") not in SET_PIECES \
                and e["location"][0] >= 80 and e["team"]["id"] in ft:
            ft[e["team"]["id"]] += 1
    return own / tot, ft[tid] / max(ft[tid] + ft[oid], 1)


def losses_distribution(p_loss):
    """Exact distribution of the number of defeats (Poisson-binomial)."""
    dist = np.array([1.0])
    for p in p_loss:
        dist = np.convolve(dist, [1 - p, p])
    return dist


def main():
    rng = np.random.default_rng(2004)
    rows = []
    for label, (_, _, team) in TEAMS.items():
        for m in team_matches(label):
            ev = load_events(m["match_id"])
            tid, opp, oid, home = side(m, team)
            row = {"team": label, "match_id": m["match_id"], "date": m["match_date"],
                   "opponent": opp, "home": home,
                   "gf": m["home_score"] if home else m["away_score"],
                   "ga": m["away_score"] if home else m["home_score"]}
            for tag, byp in [("shot", False), ("poss", True)]:
                pw, pd_, pl = simulate(chances(ev, tid, byp), chances(ev, oid, byp), rng)
                row.update({f"p_win_{tag}": pw, f"p_draw_{tag}": pd_, f"p_loss_{tag}": pl})
            row["xg_for"] = sum(chances(ev, tid, False))
            row["xg_against"] = sum(chances(ev, oid, False))
            row["possession"], row["field_tilt"] = possession_tilt(ev, tid, oid)
            rows.append(row)
    P = pd.DataFrame(rows).sort_values(["team", "date"])
    P["result"] = np.select([P.gf > P.ga, P.gf == P.ga], ["W", "D"], "L")
    P.to_csv("results/match_probabilities.csv", index=False)

    out = []
    for label, g in P.groupby("team"):
        n = len(g)
        r = {"team": label, "matches": n,
             "points": int(3 * (g.result == "W").sum() + (g.result == "D").sum()),
             "xg_for_pm": g.xg_for.mean(), "xg_against_pm": g.xg_against.mean(),
             "possession": g.possession.mean(), "field_tilt": g.field_tilt.mean(),
             "won_on_xg": int((g.xg_for > g.xg_against).sum()),
             "lost_on_xg": int((g.xg_for < g.xg_against).sum())}
        for tag in ["shot", "poss"]:
            pl = g[f"p_loss_{tag}"].values
            dist = losses_distribution(pl)
            r[f"xpts_{tag}"] = (3 * g[f"p_win_{tag}"] + g[f"p_draw_{tag}"]).sum()
            r[f"exp_losses_{tag}"] = pl.sum()
            r[f"p_unbeaten_{tag}"] = np.prod(1 - pl)
            r[f"p_le2_losses_{tag}"] = dist[:3].sum()
            r[f"most_likely_losses_{tag}"] = int(dist.argmax())
        out.append(r)
    S = pd.DataFrame(out).set_index("team")
    S.to_csv("results/season_summary.csv")

    pd.set_option("display.width", 200)
    show = S.T.copy()
    print("Season summary (shot = every shot independent; poss = one chance per possession)\n")
    print(show.to_string(float_format=lambda v: f"{v:.3f}"))

    for label, g in P.groupby("team"):
        print(f"\n{label}: the five matches with the highest chance of defeat (shot model)")
        t = g.sort_values("p_loss_shot", ascending=False).head(5)
        print(t[["date", "opponent", "home", "gf", "ga", "xg_for", "xg_against",
                 "p_win_shot", "p_draw_shot", "p_loss_shot"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
