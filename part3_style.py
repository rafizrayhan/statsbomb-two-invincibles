"""
Part 3: Two ways to be unbeaten.

Style measures use 11 v 11 play only (cut at the first red card) and periods 1-2.
How they scored uses every goal (full matches).

  On the ball:  possession (time), passes, pass completion, passes per possession,
                long-ball share (passes of 35+ yards, open play), build-up time
                (open-play possessions starting in their own half that reach the
                final third: seconds from start to first touch in the final third),
                final-third and box entries.
  Out of it:    PPDA (opponent passes in their own 60% / our tackles, interceptions
                and fouls in that zone), pressures, share of pressures in the
                opponent half, high regains (recoveries, interceptions and won
                tackles in the final third, x >= 80).
  Transition:   fast shots = shots within 15 seconds of a possession that started in
                open play (Regular Play or From Counter), and goals from them.
  Defending:    shots and np xG against, opponent box entries, opponent passes
                completed into the final third.
  Opponents:    opponent possession, opponent long-ball share, the average height
                of opponent defensive actions (how deep they sat).
  Goals:        penalty, direct free kick, set piece (a corner or free-kick
                possession, goal within 20 seconds of the restart), fast attack,
                open play (everything else, including moves that began with a
                throw-in), own goal.

Output: results/style_by_match.csv, results/style_summary.csv, results/goal_types.csv
"""

import numpy as np
import pandas as pd

from common import TEAMS, eleven_v_eleven, load_events, side, team_matches

LONG = 35
FAST = 15
OPEN = {"Regular Play", "From Counter"}
SET = {"From Corner", "From Free Kick"}
SET_SEC = 20


def ts(e):
    h, m, s = e["timestamp"].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def is_pass(e):
    return e["type"]["name"] == "Pass"


def open_pass(e):
    return is_pass(e) and e["pass"].get("type", {}).get("name") not in \
        {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}


def completed(e):
    return "outcome" not in e["pass"]


def def_action(e):
    t = e["type"]["name"]
    return t in {"Interception", "Foul Committed"} or \
        (t == "Duel" and e["duel"].get("type", {}).get("name") == "Tackle")


def regain(e):
    t = e["type"]["name"]
    if t == "Ball Recovery":
        return not e.get("ball_recovery", {}).get("recovery_failure", False)
    if t == "Interception":
        return e["interception"]["outcome"]["name"] in {"Won", "Success", "Success In Play",
                                                        "Success Out"}
    if t == "Duel" and e["duel"].get("type", {}).get("name") == "Tackle":
        return e["duel"].get("outcome", {}).get("name") in {"Won", "Success", "Success In Play",
                                                            "Success Out"}
    return False


def in_box(loc):
    return loc[0] >= 102 and 18 <= loc[1] <= 62


def possessions(ev):
    """(period, possession) -> dict with team, start time, pattern, events."""
    P = {}
    for e in ev:
        k = (e["period"], e["possession"])
        if k not in P:
            P[k] = {"team": e["possession_team"]["id"], "start": ts(e),
                    "pattern": e["play_pattern"]["name"], "events": []}
        P[k]["events"].append(e)
    return P


def style(ev, tid, oid):
    ev11, _ = eleven_v_eleven(ev)
    ev11 = [e for e in ev11 if e["period"] <= 2]
    r = {}
    P = possessions(ev11)
    for who, me, op in [("", tid, oid), ("opp_", oid, tid)]:
        mine = [e for e in ev11 if e["team"]["id"] == me]
        passes = [e for e in mine if is_pass(e)]
        op_ = [e for e in passes if open_pass(e)]
        r[who + "passes"] = len(passes)
        r[who + "pass_pct"] = np.mean([completed(e) for e in passes]) if passes else np.nan
        r[who + "long_share"] = np.mean([e["pass"]["length"] >= LONG for e in op_]) if op_ else np.nan
        own_poss = [p for p in P.values() if p["team"] == me]
        npp = [sum(1 for e in p["events"] if is_pass(e) and e["team"]["id"] == me) for p in own_poss]
        r[who + "possessions"] = len(own_poss)
        r[who + "passes_per_poss"] = np.mean(npp) if npp else np.nan
        r[who + "share_poss_5plus"] = np.mean([n >= 5 for n in npp]) if npp else np.nan
        # build-up time
        bt = []
        for p in own_poss:
            if p["pattern"] not in OPEN:
                continue
            evs = [e for e in p["events"] if e["team"]["id"] == me and "location" in e]
            if not evs or evs[0]["location"][0] >= 60:
                continue
            ft = next((e for e in evs if e["location"][0] >= 80), None)
            if ft is not None:
                bt.append(ts(ft) - p["start"])
        r[who + "buildup_n"] = len(bt)
        r[who + "buildup_sec"] = np.median(bt) if bt else np.nan
        # entries (completed open-play passes and carries ending in zone from outside)
        ft_ent = box_ent = 0
        for e in mine:
            if open_pass(e) and completed(e):
                s, t = e["location"], e["pass"]["end_location"]
            elif e["type"]["name"] == "Carry":
                s, t = e["location"], e["carry"]["end_location"]
            else:
                continue
            ft_ent += s[0] < 80 <= t[0]
            box_ent += (not in_box(s)) and in_box(t)
        r[who + "final_third_entries"] = ft_ent
        r[who + "box_entries"] = box_ent
        # pressing
        opp_passes_own60 = sum(1 for e in ev11 if is_pass(e) and e["team"]["id"] == op
                               and e["location"][0] <= 72)
        acts_high = sum(1 for e in mine if def_action(e) and e["location"][0] >= 48)
        r[who + "ppda"] = opp_passes_own60 / max(acts_high, 1)
        pr = [e for e in mine if e["type"]["name"] == "Pressure"]
        r[who + "pressures"] = len(pr)
        r[who + "pressure_opp_half"] = np.mean([e["location"][0] >= 60 for e in pr]) if pr else np.nan
        r[who + "high_regains"] = sum(1 for e in mine if regain(e) and e["location"][0] >= 80)
        da = [e["location"][0] for e in mine if def_action(e) or e["type"]["name"] == "Pressure"]
        r[who + "def_height"] = np.mean(da) if da else np.nan
        # shots
        sh = [e for e in mine if e["type"]["name"] == "Shot"
              and e["shot"].get("type", {}).get("name") != "Penalty"]
        r[who + "np_shots"] = len(sh)
        r[who + "np_xg"] = sum(e["shot"].get("statsbomb_xg", 0) for e in sh)
        fast = []
        for p in own_poss:
            if p["pattern"] in OPEN:
                fast += [e for e in p["events"] if e["type"]["name"] == "Shot"
                         and e["team"]["id"] == me and ts(e) - p["start"] <= FAST]
        r[who + "fast_shots"] = len(fast)
        r[who + "fast_xg"] = sum(e["shot"].get("statsbomb_xg", 0) for e in fast)
    return r


def goal_types(ev, tid):
    out = []
    P = possessions(ev)
    for e in ev:
        if e["period"] > 4:
            continue
        if e["type"]["name"] == "Own Goal For" and e["team"]["id"] == tid:
            out.append("Own goal")
            continue
        if not (e["type"]["name"] == "Shot" and e["team"]["id"] == tid
                and e["shot"]["outcome"]["name"] == "Goal"):
            continue
        st = e["shot"].get("type", {}).get("name")
        p = P[(e["period"], e["possession"])]
        if st == "Penalty":
            out.append("Penalty")
        elif st == "Free Kick":
            out.append("Direct free kick")
        elif p["pattern"] in SET and ts(e) - p["start"] <= SET_SEC:
            out.append("Set piece")
        elif p["pattern"] in OPEN and ts(e) - p["start"] <= FAST:
            out.append("Fast attack (15s)")
        else:
            out.append("Open play")
    return out


def main():
    rows, goals = [], []
    for label, (_, _, team) in TEAMS.items():
        for m in team_matches(label):
            ev = load_events(m["match_id"])
            tid, opp, oid, home = side(m, team)
            _, cut = eleven_v_eleven(ev)
            r = {"team": label, "date": m["match_date"], "opponent": opp, "home": home,
                 "cut": cut, **style(ev, tid, oid)}
            rows.append(r)
            for g in goal_types(ev, tid):
                goals.append({"team": label, "date": m["match_date"], "type": g, "side": "for"})
            for g in goal_types(ev, oid):
                goals.append({"team": label, "date": m["match_date"], "type": g, "side": "against"})
    S = pd.DataFrame(rows)
    S.to_csv("results/style_by_match.csv", index=False)
    Pm = pd.read_csv("results/match_probabilities.csv")[["team", "date", "possession"]]
    S = S.merge(Pm, on=["team", "date"])

    cols = ["possession", "passes", "pass_pct", "passes_per_poss", "share_poss_5plus",
            "long_share", "buildup_sec", "final_third_entries", "box_entries",
            "ppda", "pressures", "pressure_opp_half", "high_regains", "def_height",
            "np_shots", "np_xg", "fast_shots", "fast_xg"]
    summ = {}
    for label, g in S.groupby("team"):
        d = {c: g[c].mean() for c in cols}
        # build-up: pool all possessions? use median of match medians weighted by n
        d["buildup_sec"] = np.average(g.buildup_sec.dropna(), weights=g.buildup_n[g.buildup_sec.notna()])
        for c in cols[1:]:
            d["opp_" + c] = g["opp_" + c].mean()
        d["opp_possession"] = 1 - d["possession"]
        summ[label] = d
    T = pd.DataFrame(summ)
    T.to_csv("results/style_summary.csv")
    G = pd.DataFrame(goals)
    GT = G.pivot_table(index="type", columns=["team", "side"], aggfunc="size", fill_value=0)
    GT.to_csv("results/goal_types.csv")

    pd.set_option("display.width", 200)
    order = [c for c in cols] + ["opp_" + c for c in ["passes", "pass_pct", "passes_per_poss",
             "long_share", "ppda", "pressures", "def_height", "np_shots", "np_xg",
             "box_entries", "final_third_entries", "fast_shots", "fast_xg"]]
    print("Per match, 11 v 11, periods 1-2\n")
    print(T.loc[order].to_string(float_format=lambda v: f"{v:.2f}"))
    print("\nGoals by type (full matches)\n")
    print(GT.to_string())


if __name__ == "__main__":
    main()
