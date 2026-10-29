"""
Shared data loading for the Invincibles project.

Arsenal, Premier League 2003/04 (38 matches) and Bayer Leverkusen,
Bundesliga 2023/24 (34 matches), from StatsBomb open data.
Only these two teams' matches are in the data, not the rest of either league.
"""

import json
import os
import time
import urllib.request

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
EVENT_DIR = "data/events"
TEAMS = {  # label: (competition name, season name, team name)
    "Arsenal 2003/04": ("Premier League", "2003/2004", "Arsenal"),
    "Leverkusen 2023/24": ("1. Bundesliga", "2023/2024", "Bayer Leverkusen"),
}
RED = {"Red Card", "Second Yellow"}


def get_json(url, retries=6):
    """Download JSON, waiting and retrying if GitHub rate-limits (HTTP 429)."""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt * 2)


def team_matches(label):
    comp, season, team = TEAMS[label]
    c = [x for x in get_json(f"{BASE}/competitions.json")
         if x["competition_name"] == comp and x["season_name"] == season][0]
    ms = get_json(f"{BASE}/matches/{c['competition_id']}/{c['season_id']}.json")
    return [m for m in ms if team in (m["home_team"]["home_team_name"],
                                      m["away_team"]["away_team_name"])]


def load_events(match_id):
    os.makedirs(EVENT_DIR, exist_ok=True)
    path = os.path.join(EVENT_DIR, f"{match_id}.json")
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(get_json(f"{BASE}/events/{match_id}.json"), f)
    with open(path) as f:
        return json.load(f)


def clock(e):
    """Match clock in minutes (StatsBomb 2nd-half minutes already start at 45)."""
    return e["minute"] + e["second"] / 60


def side(m, team):
    """(team_id, opponent name, opponent id, home?) for one match."""
    home = m["home_team"]["home_team_name"] == team
    if home:
        return (m["home_team"]["home_team_id"], m["away_team"]["away_team_name"],
                m["away_team"]["away_team_id"], True)
    return (m["away_team"]["away_team_id"], m["home_team"]["home_team_name"],
            m["home_team"]["home_team_id"], False)


def red_cards(events):
    out = []
    for e in events:
        card = (e.get("foul_committed", {}).get("card", {}).get("name")
                or e.get("bad_behaviour", {}).get("card", {}).get("name"))
        if card in RED:
            out.append((e["team"]["id"], e["team"]["name"], clock(e)))
    return out


def eleven_v_eleven(events):
    """Events before the first red card (for style measures)."""
    reds = red_cards(events)
    if not reds:
        return events, None
    cut = min(r[2] for r in reds)
    return [e for e in events if clock(e) < cut], cut


def goals(events, team_id):
    """Goals scored by team_id: its scored shots plus own goals credited to it."""
    g = 0
    for e in events:
        t = e["type"]["name"]
        if t == "Shot" and e["team"]["id"] == team_id and e["shot"]["outcome"]["name"] == "Goal":
            g += 1
        elif t == "Own Goal For" and e["team"]["id"] == team_id:
            g += 1
    return g
