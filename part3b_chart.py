"""
Part 3 chart: two ways to be unbeaten.
  Left: style profile (11 v 11), one row per measure, both teams on the row's own scale.
  Right: how the goals were scored.

Input:  results/style_summary.csv, results/goal_types.csv (from part 3)
Output: figures/part3_two_styles.png
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

SURFACE, INK, INK_2, INK_3 = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e8e7e3"
A, L = "Arsenal 2003/04", "Leverkusen 2023/24"
COL = {A: "#DB0007", L: "#1a1a1a"}

ROWS = [
    ("With the ball", None, None),
    ("Passes per possession", "passes_per_poss", "{:.1f}"),
    ("Possessions with 5+ passes", "share_poss_5plus", "{:.0%}"),
    ("Long-ball share (35+ yards)", "long_share", "{:.0%}"),
    ("Seconds from own half to final third", "buildup_sec", "{:.1f}s"),
    ("Box entries per match", "box_entries", "{:.1f}"),
    ("Without the ball", None, None),
    ("Defensive actions: yards from own goal", "def_height", "{:.0f}"),
    ("Pressures in the opponent half", "pressure_opp_half", "{:.0%}"),
    ("Ball regains in the final third", "high_regains", "{:.1f}"),
    ("Opponent non-penalty xG per match", "opp_np_xg", "{:.2f}"),
]
GOALS = ["Open play", "Fast attack (15s)", "Set piece", "Direct free kick", "Penalty", "Own goal"]
GLAB = {"Open play": "Open play, built up", "Fast attack (15s)": "Fast attack (within 15s)",
        "Set piece": "Corner or free kick", "Direct free kick": "Direct free kick",
        "Penalty": "Penalty", "Own goal": "Own goal"}


def main():
    os.makedirs("figures", exist_ok=True)
    for f in font_manager.findSystemFonts():
        if "Inter" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams.update({"font.family": "Inter", "text.color": INK,
                         "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
    S = pd.read_csv("results/style_summary.csv", index_col=0)
    G = pd.read_csv("results/goal_types.csv", header=[0, 1], index_col=0)

    fig = plt.figure(figsize=(15, 8))
    ax = fig.add_axes([0.03, 0.08, 0.5, 0.74])
    n = len(ROWS)
    ax.set_xlim(-0.95, 1.12)
    ax.set_ylim(n - 0.4, -0.9)
    ax.axis("off")
    for i, (lab, key, fmt) in enumerate(ROWS):
        if key is None:
            ax.text(-0.95, i + 0.15, lab.upper(), fontsize=10.5, fontweight="bold", color=INK_3)
            continue
        a, l = S.loc[key, A], S.loc[key, L]
        top = max(a, l) * 1.12
        xa, xl = a / top, l / top
        ax.text(-0.95, i, lab, fontsize=11.5, va="center", color=INK)
        ax.hlines(i, 0, 1, color=GRID, lw=1.2, zorder=1)
        ax.hlines(i, min(xa, xl), max(xa, xl), color=INK_3, lw=2.5, zorder=2)
        for x, t, v in [(xa, A, a), (xl, L, l)]:
            ax.scatter(x, i, s=150, color=COL[t], zorder=3, edgecolor=SURFACE, lw=1.5)
            left = x == min(xa, xl)
            ax.text(x + (-0.035 if left else 0.035), i, fmt.format(v), fontsize=10.5,
                    fontweight="bold", color=COL[t], va="center",
                    ha="right" if left else "left")
    ax.text(-0.95, -0.75, "How they played", fontsize=13.5, fontweight="bold")

    bx = fig.add_axes([0.66, 0.08, 0.32, 0.66])
    h = 0.36
    tot = {t: G[t]["for"].sum() for t in (A, L)}
    for i, g in enumerate(GOALS):
        for j, t in enumerate((A, L)):
            v = int(G.loc[g, (t, "for")])
            y = i + (j - 0.5) * (h + 0.04)
            bx.barh(y, v, height=h, color=COL[t])
            bx.text(v + 0.8, y, f"{v}  ({v / tot[t]:.0%})", va="center", fontsize=10,
                    color=COL[t], fontweight="bold" if g in ("Fast attack (15s)", "Set piece")
                    else "normal")
        bx.text(-1, i, GLAB[g], ha="right", va="center", fontsize=11)
    bx.set_ylim(len(GOALS) - 0.4, -0.6)
    bx.set_xlim(0, 62)
    bx.axis("off")
    fig.text(0.535, 0.83, "How they scored", fontsize=13.5, fontweight="bold")
    fig.text(0.535, 0.795, f"Goals for (share of all goals). Arsenal {tot[A]}, Leverkusen {tot[L]}.",
             fontsize=10, color=INK_2)

    fig.text(0.03, 0.965, "Two ways to be unbeaten: Arsenal ran at teams, Leverkusen pinned "
             "them in", fontsize=19, fontweight="bold", va="top")
    fig.text(0.03, 0.918, "Per match. Each row on its own scale, starting from zero.",
             fontsize=11, color=INK_2, va="top")
    from matplotlib.lines import Line2D
    hs = [Line2D([], [], marker="o", ls="", ms=10, color=COL[t], label=t) for t in (A, L)]
    fig.legend(handles=hs, loc="upper left", bbox_to_anchor=(0.36, 0.935), ncol=2,
               frameon=False, fontsize=11, handletextpad=0.3, columnspacing=1.5)
    fig.text(0.03, 0.02, "Data: StatsBomb open data. Style measures use 11 v 11 play only (to the "
             "first red card). Set piece = corner or free-kick possession, goal within 20 seconds "
             "of the restart. Fast attack = shot within 15 seconds of winning the ball in open play.",
             fontsize=8, color=INK_3)
    fig.savefig("figures/part3_two_styles.png", dpi=200)
    print("Saved figures/part3_two_styles.png")


if __name__ == "__main__":
    main()
