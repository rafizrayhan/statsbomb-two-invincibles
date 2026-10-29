"""
Part 4 chart: one star or many scorers.
  Each team's top eight players by goal involvements (goals + assists), shown as a
  share of all the team's league goals.

Input:  results/players.csv (from part 4)
Output: figures/part4_players.png
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from matplotlib.patches import Patch

SURFACE, INK, INK_2, INK_3 = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984"
A, L = "Arsenal 2003/04", "Leverkusen 2023/24"
COL = {A: ("#DB0007", "#f0a8a8"), L: ("#1a1a1a", "#a3a29d")}
TEAM_GOALS = {A: 73, L: 89}  # includes own goals by opponents (part 0 audit)
SHORT = {"Thierry Henry": "Henry", "Robert Pirès": "Pirès", "Dennis Bergkamp": "Bergkamp",
         "Fredrik Ljungberg": "Ljungberg", "Gilberto Aparecido da Silva": "Gilberto Silva",
         "Patrick Vieira": "Vieira", "Eduardo César Daude Gaspar": "Edu",
         "José Antonio Reyes Calderón": "Reyes", "Sylvain Wiltord": "Wiltord",
         "Alejandro Grimaldo García": "Grimaldo", "Victor Okoh Boniface": "Boniface",
         "Florian Wirtz": "Wirtz", "Jeremie Frimpong": "Frimpong", "Jonas Hofmann": "Hofmann",
         "Amine Adli": "Adli", "Exequiel Alejandro Palacios": "Palacios",
         "Patrik Schick": "Schick", "Nathan Tella": "Tella", "Robert Andrich": "Andrich"}
TOP = 8


def main():
    os.makedirs("figures", exist_ok=True)
    for f in font_manager.findSystemFonts():
        if "Inter" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams.update({"font.family": "Inter", "text.color": INK,
                         "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
    P = pd.read_csv("results/players.csv")

    fig, axes = plt.subplots(1, 2, figsize=(14, 7.2))
    for ax, t in zip(axes, (A, L)):
        g = P[P.team == t].sort_values(["ga", "goals"], ascending=False).head(TOP)
        tg = TEAM_GOALS[t]
        dark, light = COL[t]
        for i, r in enumerate(g.itertuples()):
            gs, as_ = r.goals / tg, r.assists / tg
            ax.barh(i, gs, color=dark, height=0.68)
            ax.barh(i, as_, left=gs, color=light, height=0.68)
            ax.text(gs + as_ + 0.01, i, f"{int(r.ga)}  ({r.ga / tg:.0%})", va="center",
                    fontsize=11, fontweight="bold", color=dark)
            ax.text(-0.012, i, SHORT.get(r.player, r.player), ha="right", va="center",
                    fontsize=11.5)
            ax.text(-0.012, i + 0.33, f"{int(r.goals)}g {int(r.assists)}a", ha="right",
                    va="center", fontsize=8.5, color=INK_3)
        ax.set_ylim(TOP - 0.4, -0.9)
        ax.set_xlim(0, 0.6)
        ax.axis("off")
        n5 = int((P[P.team == t].goals >= 5).sum())
        sc = int((P[P.team == t].goals > 0).sum())
        ax.text(-0.16, -1.05, t, fontsize=14, fontweight="bold", color=dark)
        ax.text(-0.16, -0.62, f"{tg} goals. {sc} different scorers, {n5} with 5 or more.",
                fontsize=10.5, color=INK_2)
        ax.legend(handles=[Patch(color=dark, label="Goals"), Patch(color=light, label="Assists")],
                  loc="lower right", frameon=False, fontsize=10, ncol=2)
    fig.text(0.03, 0.965, "One star, or goals from everywhere", fontsize=19, fontweight="bold",
             va="top")
    fig.text(0.03, 0.918, "Goal involvements (goals + assists) as a share of each team's league "
             "goals. Henry was involved in almost half of Arsenal's.", fontsize=11, color=INK_2,
             va="top")
    fig.text(0.03, 0.02, "Data: StatsBomb open data. Goals and assists as recorded in StatsBomb "
             "events; assist counts can differ from official league figures. Team goals include "
             "opponent own goals.", fontsize=8, color=INK_3)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.78, bottom=0.07, wspace=0.42)
    fig.savefig("figures/part4_players.png", dpi=200)
    print("Saved figures/part4_players.png")


if __name__ == "__main__":
    main()
