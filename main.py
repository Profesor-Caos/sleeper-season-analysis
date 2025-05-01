# sleeper-season-analysis/main.py

import requests
import pandas as pd
from tabulate import tabulate

# ----- Configuration -----
LEAGUE_ID = "1127468541545930752"
SEASON_YEAR = 2024
WEEKS = 14

# ----- Fetch Functions -----
def get_users(league_id):
    url = f"https://api.sleeper.app/v1/league/{league_id}/users"
    return requests.get(url).json()

def get_rosters(league_id):
    url = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    return requests.get(url).json()

def get_matchups(league_id, week):
    url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
    return requests.get(url).json()

# ----- Analysis -----
def build_team_lookup(users, rosters):
    user_id_to_name = {u['user_id']: u['display_name'] for u in users}
    team_map = {}
    for r in rosters:
        owner_id = r['owner_id']
        team_id = r['roster_id']
        team_map[team_id] = user_id_to_name.get(owner_id, f"Team {team_id}")
    return team_map

def build_weekly_tables(league_id, team_map):
    points = []
    results = []
    opponent_points = {team: [0]*WEEKS for team in team_map.values()}
    matchups_by_team = {team: [] for team in team_map.values()}
    matchups_by_week = [{} for _ in range(WEEKS)]

    for week in range(1, WEEKS + 1):
        matchups = get_matchups(league_id, week)
        week_points = {}
        week_results = {}
        matchup_map = {}

        for m in matchups:
            team = team_map.get(m['roster_id'], f"T{m['roster_id']}")
            points_scored = m.get('points', 0)
            week_points[team] = points_scored
            matchup_id = m.get('matchup_id')
            if matchup_id is not None:
                matchup_map.setdefault(matchup_id, []).append((team, points_scored))

        row_result = {}
        for matchup in matchup_map.values():
            if len(matchup) == 2:
                (team1, pts1), (team2, pts2) = matchup
                row_result[team1] = 'W' if pts1 > pts2 else 'L'
                row_result[team2] = 'W' if pts2 > pts1 else 'L'
                opponent_points[team1][week-1] = pts2
                opponent_points[team2][week-1] = pts1
                matchups_by_team[team1].append(team2)
                matchups_by_team[team2].append(team1)
                matchups_by_week[week-1][team1] = team2
                matchups_by_week[week-1][team2] = team1
            else:
                for team, _ in matchup:
                    row_result[team] = '-'

        points.append(week_points)
        results.append(row_result)

    df_points = pd.DataFrame(points).fillna(0).astype(float).T
    df_results = pd.DataFrame(results).fillna('-').T
    df_points.columns = df_results.columns = [str(i) for i in range(1, WEEKS + 1)]

    df_sos = pd.DataFrame(opponent_points).T
    df_sos.columns = [str(i) for i in range(1, WEEKS + 1)]
    df_sos["Total SoS"] = df_sos.sum(axis=1)

    # BCS-style SOS calculation using normalized win percentages
    win_counts = {team: (df_results.loc[team] == 'W').sum() for team in df_results.index}
    loss_counts = {team: (df_results.loc[team] == 'L').sum() for team in df_results.index}

    or_percent = {}
    oor_percent = {}
    games_per_team = WEEKS
    max_or_games = games_per_team * (games_per_team - 1)  # 14 * 13 = 182

    # Precompute each team's OR for reuse in OOR
    team_or_raw = {}
    for team in df_results.index:
        opponents = matchups_by_team[team]
        team_or_raw[team] = sum([win_counts.get(opp, 0) for opp in opponents]) - loss_counts.get(team, 0)

    for team in df_results.index:
        opponents = matchups_by_team[team]
        or_total = team_or_raw[team]
        or_percent[team] = or_total / max_or_games if max_or_games > 0 else 0

        oor_total = sum([team_or_raw.get(opp, 0) for opp in opponents])
        max_oor_games = WEEKS * len(opponents) * (games_per_team - 1)
        oor_percent[team] = oor_total / max_oor_games if max_oor_games > 0 else 0

    df_bcs_sos = pd.DataFrame({
        "OR Win %": or_percent,
        "OOR Win %": oor_percent
    })
    df_bcs_sos['BCS SOS'] = (2 * df_bcs_sos["OR Win %"] + df_bcs_sos["OOR Win %"]) / 3

    return df_points, df_results, df_sos, df_bcs_sos

# ----- Main CLI Output -----
def main():
    print("Fetching league data...")
    users = get_users(LEAGUE_ID)
    rosters = get_rosters(LEAGUE_ID)
    team_map = build_team_lookup(users, rosters)

    print("Building tables...")
    df_points, df_results, df_sos, df_bcs_sos = build_weekly_tables(LEAGUE_ID, team_map)

    print("\nPoints Scored by Team Each Week:")
    print(tabulate(df_points, headers="keys", tablefmt="pretty"))

    print("\nWin/Loss Results by Week:")
    print(tabulate(df_results, headers="keys", tablefmt="pretty"))

    print("\nStrength of Schedule (Opponent Points Scored per Week):")
    print(tabulate(df_sos, headers="keys", tablefmt="pretty"))

    print("\nBCS-Style Strength of Schedule (Normalized Win %):")
    print(tabulate(df_bcs_sos, headers="keys", tablefmt="pretty", floatfmt=".3f"))

if __name__ == "__main__":
    main()
