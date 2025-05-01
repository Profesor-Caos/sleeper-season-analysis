# sleeper-season-analysis/main.py

import requests
import pandas as pd
from tabulate import tabulate

# ----- Configuration -----
LEAGUE_ID = "1127468541545930752"  # Replace with your Sleeper dynasty league ID
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

    # BCS-style SOS calculation (excluding games vs team being calculated)
    win_counts_per_team = {team: (df_results.loc[team] == 'W').sum() for team in df_results.index}
    team_opponents = matchups_by_team

    or_record = {}
    oor_record = {}

    for team in team_opponents:
        opponents = team_opponents[team]
        or_wins = sum([win_counts_per_team.get(opp, 0) - (1 if team in team_opponents.get(opp, []) else 0) for opp in opponents])
        or_record[team] = or_wins

        grand_opponents = set()
        for opp in opponents:
            grand_opponents.update(team_opponents.get(opp, []))
        grand_opponents.discard(team)
        oor_wins = sum([win_counts_per_team.get(gopp, 0) - (1 if opp in team_opponents.get(gopp, []) else 0) for gopp in grand_opponents for opp in opponents if gopp != team])
        oor_record[team] = oor_wins

    df_bcs_sos = pd.DataFrame({
        "Opponents' Wins (OR)": or_record,
        "Opponents' Opponents' Wins (OOR)": oor_record
    })
    df_bcs_sos['BCS SOS'] = (2 * df_bcs_sos["Opponents' Wins (OR)"] + df_bcs_sos["Opponents' Opponents' Wins (OOR)"]) / 3

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

    print("\nBCS-Style Strength of Schedule:")
    print(tabulate(df_bcs_sos, headers="keys", tablefmt="pretty"))

if __name__ == "__main__":
    main()
