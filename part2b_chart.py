"""
Part 2 chart: what happened after the 85th minute.
  Left: late goals for and against, with the xG of late chances.
  Right: every match where a goal from the 85th minute changed the points.

Input:  results/game_state.csv, results/late_goals.csv (from part 2), cached events
Output: figures/part2_late_goals.png
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

from common import TEAMS, load_events, side, team_matches

SURFACE, INK, INK_2, INK_3 = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984"
GRID, GREY = "#e8e7e3", "#c9c8c2"
COL = {"Arsenal 2003/04": "#DB0007", "Leverkusen 2023/24": "#1a1a1a"}
LATE = 85


def late_xg():
    out = {}
    for label, (_, _, team) in TEAMS.items():
        f = a = 0.0
        for m in team_matches(label):
            ev = load_events(m["match_id"])
            tid, opp, oid, home = side(m, team)
            for e in ev:
                if e["type"]["name"] == "Shot" and e["minute"] >= LATE \
                        and e["shot"].get("type", {}).get("name") != "Penalty":
                    if e["team"]["id"] == tid:
                        f += e["shot"].get("statsbomb_xg", 0)
                    else:
                        a += e["shot"].get("statsbomb_xg", 0)
        out[label] = (f, a)
    return out


def main():
    os.makedirs("figures", exist_ok=True)
    for f in font_manager.findSystemFonts():
        if "Inter" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams.update({"font.family": "Inter", "text.color": INK,
                         "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
    G = pd.read_csv("results/game_state.csv")
    L = pd.read_csv("results/late_goals.csv")
    X = late_xg()
    teams = list(TEAMS)

    fig = plt.figure(figsize=(14, 7))
    ax = fig.add_axes([0.05, 0.14, 0.4, 0.6])
    w = 0.34
    for i, t in enumerate(teams):
        l = L[L.team == t]
        gf = int((l["for"] & ~l.penalty).sum())
        ga = int((~l["for"] & ~l.penalty).sum())
        pf = int((l["for"] & l.penalty).sum())
        xf, xa = X[t]
        for j, (v, xv, lab) in enumerate([(gf, xf, "for"), (ga, xa, "against")]):
            x = i + (j - 0.5) * (w + 0.04)
            ax.bar(x, v, width=w, color=COL[t] if j == 0 else GREY, zorder=2)
            ax.hlines(xv, x - w / 2, x + w / 2, color="#2a78d6", lw=3, zorder=3)
            ax.text(x, max(v, xv) + 0.3, f"{v}", ha="center", fontsize=14, fontweight="bold",
                    color=COL[t] if j == 0 else INK_2)
            ax.text(x, -0.9, lab, ha="center", fontsize=10, color=INK_2)
            if j == 0 and pf:
                ax.text(x, v + 1.3, f"+{pf} pens", ha="center", fontsize=9, color=INK_3)
        ax.text(i, -1.9, t, ha="center", fontsize=12, fontweight="bold", color=COL[t])
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylim(0, 15)
    ax.axis("off")
    ax.text(-0.55, 14.6, "Non-penalty goals after 85:00", fontsize=13.5, fontweight="bold")
    ax.text(-0.55, 13.7, "Blue line = xG of those late chances", fontsize=10,
            color="#2a78d6")

    ax2 = fig.add_axes([0.52, 0.1, 0.45, 0.66])
    ax2.axis("off")
    ax2.text(0, 1.04, "Points changed by goals after 85:00", fontsize=13.5,
             fontweight="bold", transform=ax2.transAxes)
    y = 0.94
    for t in teams:
        g = G[G.team == t].copy()
        g["swing"] = g.pts_final - g.pts_at_85
        ch = g[g.swing != 0].sort_values("date")
        net = int(ch.swing.sum())
        ax2.text(0, y, f"{t}: {net:+d} points", fontsize=13, fontweight="bold", color=COL[t],
                 transform=ax2.transAxes)
        y -= 0.075
        for r in ch.itertuples():
            late = L[(L.team == t) & (L.date == r.date)]
            mins = ", ".join(f"{int(mn) + 1}'" for mn, fr in zip(late.minute, late["for"])
                             if fr == (r.swing > 0))
            ax2.text(0.02, y, f"{r.swing:+d}", fontsize=11.5, fontweight="bold",
                     color="#2a8a5c" if r.swing > 0 else "#b3261e", transform=ax2.transAxes)
            ax2.text(0.09, y, f"v {r.opponent}: final {r.gf}-{r.ga}"
                     + (f"  (late goals {mins})" if mins else ""), fontsize=10.5,
                     color=INK_2, transform=ax2.transAxes)
            y -= 0.06
        y -= 0.05

    fig.text(0.03, 0.965, "Leverkusen won their games late. Arsenal let points slip late.",
             fontsize=18, fontweight="bold", va="top")
    fig.text(0.03, 0.915, "Leverkusen scored 11 non-penalty goals in the last five minutes and stoppage time "
             "from 7.2 xG: an average finisher would match that about 1 time in 13.",
             fontsize=11, color=INK_2, va="top")
    fig.text(0.03, 0.02, "Data: StatsBomb open data. Late = from 85:00 on the match clock, stoppage time included; "
             "minutes shown in the usual way (85:30 = 86'). "
             "Points change = final points minus points with the score at 85:00.",
             fontsize=8, color=INK_3)
    fig.savefig("figures/part2_late_goals.png", dpi=200)
    print("Saved figures/part2_late_goals.png")


if __name__ == "__main__":
    main()
