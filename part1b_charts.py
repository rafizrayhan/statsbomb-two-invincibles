"""
Part 1 charts.
  A. How many defeats their chances 'should' have produced: the full probability
     distribution of defeats for each team, with the actual zero highlighted.
  B. Every match: chance of win, draw and defeat from the simulation, with the
     actual result marked.

Input:  results/match_probabilities.csv (from part 1)
Output: figures/part1a_expected_defeats.png, figures/part1b_every_match.png
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

SURFACE, INK, INK_2, INK_3 = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984"
GRID, GREY = "#e8e7e3", "#c9c8c2"
COL = {"Arsenal 2003/04": "#DB0007", "Leverkusen 2023/24": "#1a1a1a"}
WIN, DRAW, LOSS = "#2a8a5c", "#c9c8c2", "#b8b7b0"


def fonts():
    for f in font_manager.findSystemFonts():
        if "Inter" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams.update({"font.family": "Inter", "text.color": INK,
                         "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})


def dist(p):
    d = np.array([1.0])
    for x in p:
        d = np.convolve(d, [1 - x, x])
    return d


def chart_a(P):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), sharey=True)
    for ax, (team, g) in zip(axes, P.groupby("team")):
        d = dist(g.p_loss_shot.values)[:16]
        c = COL[team]
        bars = ax.bar(range(len(d)), d, color=GREY, width=0.75, zorder=2)
        bars[0].set_color(c)
        pu = d[0]
        exp = g.p_loss_shot.sum()
        odds = round(1 / pu, -3) if 1 / pu > 5000 else round(1 / pu, -1)
        ax.annotate(f"Unbeaten:\nabout 1 in {odds:,.0f}", (0, pu), xytext=(1.2, 0.212),
                    fontsize=12, fontweight="bold", color=c,
                    arrowprops=dict(arrowstyle="-", color=c, lw=1.2))
        ax.axvline(exp, color=INK_3, ls="--", lw=1.2, zorder=1)
        ax.text(exp + 0.25, 0.248, f"Expected: {exp:.1f} defeats", fontsize=10, color=INK_2,
                va="top")
        ax.set_title(team, loc="left", fontsize=14, fontweight="bold", color=c, pad=10)
        ax.set_xticks(range(0, 16, 1))
        ax.set_xlim(-0.6, 15.6)
        ax.set_xlabel("Number of defeats in the season", fontsize=10.5, color=INK_2)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        for sp in ["top", "right", "left"]:
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(length=0, labelsize=9, colors=INK_3)
        ax.grid(axis="y", color=GRID, lw=0.7)
        ax.set_axisbelow(True)
        ax.set_ylim(0, 0.25)
        ax.set_yticks([0, 0.05, 0.10, 0.15, 0.20])
    fig.text(0.03, 0.965, "Neither team's chances should have produced an unbeaten season",
             fontsize=18, fontweight="bold", va="top")
    fig.text(0.03, 0.905, "Probability of each number of defeats, from replaying every shot "
             "in every match 20,000 times. Both went unbeaten.", fontsize=11, color=INK_2,
             va="top")
    fig.text(0.03, 0.045, "Data: StatsBomb open data. Arsenal: Premier League 2003/04 (38 "
             "matches). Leverkusen: Bundesliga 2023/24 (34 matches). Each shot scored with "
             "probability = its xG.", fontsize=8, color=INK_3)
    fig.text(0.03, 0.018, "Caveat: shots are treated as independent of the score. Teams that "
             "lead often ease off and concede late chances, so this method tends to underrate "
             "strong sides.", fontsize=8, color=INK_3)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.78, bottom=0.15, wspace=0.08)
    fig.savefig("figures/part1a_expected_defeats.png", dpi=200)
    print("Saved figures/part1a_expected_defeats.png")


def chart_b(P):
    fig, axes = plt.subplots(2, 1, figsize=(14, 8.4))
    for ax, (team, g) in zip(axes, P.groupby("team")):
        g = g.sort_values("date").reset_index(drop=True)
        x = np.arange(len(g))
        ax.bar(x, g.p_win_shot, color=WIN, width=0.8, label="Win", zorder=2)
        ax.bar(x, g.p_draw_shot, bottom=g.p_win_shot, color=DRAW, width=0.8, label="Draw",
               zorder=2)
        ax.bar(x, g.p_loss_shot, bottom=g.p_win_shot + g.p_draw_shot, color="#e7a3a3",
               width=0.8, label="Defeat", zorder=2)
        for xi, r in zip(x, g.result):
            ax.text(xi, 1.04, r, ha="center", fontsize=8.5, fontweight="bold",
                    color=WIN if r == "W" else INK_2)
        top = g.sort_values("p_loss_shot", ascending=False).head(2).sort_index()
        offsets = [6, 14]
        for (i, row), off in zip(top.iterrows(), offsets):
            where = "away" if not row.home else "home"
            ax.annotate(f"v {row.opponent} ({where}): {int(row.gf)}-{int(row.ga)}, "
                        f"{row.p_loss_shot:.0%} chance of defeat", (i, 1.0),
                        xytext=(min(i + off, len(g) - 14), 1.38 if off == 6 else 1.2),
                        fontsize=9.5, color=COL[team], fontweight="semibold",
                        arrowprops=dict(arrowstyle="-", color=COL[team], lw=0.8))
        ax.set_xlim(-0.7, len(g) - 0.3)
        ax.set_ylim(0, 1.55)
        ax.set_yticks([0, 0.5, 1])
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.set_xticks([])
        for sp in ["top", "right", "left", "bottom"]:
            ax.spines[sp].set_visible(False)
        ax.tick_params(length=0, labelsize=9, colors=INK_3)
        ax.set_title(f"{team}: {len(g)} matches in order", loc="left", fontsize=13,
                     fontweight="bold", color=COL[team], pad=4)
    axes[0].legend(frameon=False, ncol=3, loc="upper right", bbox_to_anchor=(1, 1.32),
                   fontsize=10, labelcolor=INK_2)
    fig.text(0.03, 0.975, "Every match: what the chances said, and what happened", fontsize=18,
             fontweight="bold", va="top")
    fig.text(0.03, 0.935, "Bars = chance of a win, draw or defeat from both teams' shots. "
             "Letter = actual result.", fontsize=11, color=INK_2, va="top")
    fig.text(0.03, 0.015, "Data: StatsBomb open data. Each shot scored with probability = "
             "its xG, 20,000 replays per match.", fontsize=8, color=INK_3)
    fig.subplots_adjust(left=0.05, right=0.98, top=0.84, bottom=0.05, hspace=0.55)
    fig.savefig("figures/part1b_every_match.png", dpi=200)
    print("Saved figures/part1b_every_match.png")


def main():
    os.makedirs("figures", exist_ok=True)
    fonts()
    P = pd.read_csv("results/match_probabilities.csv")
    chart_a(P)
    chart_b(P)


if __name__ == "__main__":
    main()
