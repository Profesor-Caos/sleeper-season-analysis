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

def build_totals(league_id, team_map):
    team_points_for = {team: [0] * WEEKS for team in team_map.values()}
    team_points_against = {team: [0] * WEEKS for team in team_map.values()}
    total_points_for_by_team = {team: 0 for team in team_map.values()}
    total_points_against_by_team = {team: 0 for team in team_map.values()}
    match_results_by_team = {team: [] for team in team_map.values()}
    matchups_by_team = {team: [] for team in team_map.values()}

    for week in range(1, WEEKS + 1):
        matchups = get_matchups(league_id, week)
        match_id_to_teams_involved = {}
        
        for team in matchups:
            team_id = team_map.get(team['roster_id'], f"T{team['roster_id']}")
            points_scored = team.get('points', 0)
            team_points_for[team_id][week-1] = points_scored
            total_points_for_by_team[team_id] += points_scored
            matchup_id = team.get('matchup_id')
            if matchup_id is not None:
                match_id_to_teams_involved.setdefault(matchup_id, []).append((team_id, points_scored))
        
        for matchup in match_id_to_teams_involved.values():
            if len(matchup) == 2:
                (team1, pts1), (team2, pts2) = matchup
                match_results_by_team[team1].append('W' if pts1 > pts2 else 'L' if pts1 < pts2 else 'D')
                match_results_by_team[team2].append('W' if pts2 > pts1 else 'L' if pts2 < pts1 else 'D')
                team_points_against[team1][week-1] = pts2
                team_points_against[team2][week-1] = pts1
                total_points_against_by_team[team1] += pts2
                total_points_against_by_team[team2] += pts1
                matchups_by_team[team1].append(team2)
                matchups_by_team[team2].append(team1)
            else:
                for team, _ in matchup:
                    match_results_by_team[team].append('-')

    team_records = {}
    for team in team_map.values():
        wins = match_results_by_team[team].count('W')
        losses = match_results_by_team[team].count('L')
        draws = match_results_by_team[team].count('D')
        team_records[team] = {
            "wins": wins,
            "losses": losses,
            "draws": draws
        }

    opponents_wins_against_other_teams = {}
    opponents_points_against_other_teams = {}
    for team in team_map.values():
        opponent_wins = 0
        total_opponent_points = 0
        for opponent in matchups_by_team[team]:
            opponent_wins += team_records[opponent]["wins"]
            opponent_wins += 0.5 * team_records[opponent]["draws"]
            total_opponent_points += total_points_for_by_team[opponent]
        opponents_wins_against_other_teams[team] = (
            opponent_wins # all the wins opponents had
            - team_records[team]["losses"] # only count wins they had against other teams
            - 0.5 * team_records[team]["draws"] # ignore draws against the team being analyzed as well
        )
        opponents_points_against_other_teams[team] = (
            # ignore points against the team being analyzed when counting
            # points scored by other teams
            total_opponent_points - total_points_against_by_team[team]
        )
    
    opponents_opponents_wins_against_other_teams = {}
    for team in team_map.values():
        opponents_opponent_wins = 0
        for opponent in matchups_by_team[team]:
            for opponents_opponent in matchups_by_team[opponent]:
                opponents_opponent_wins += team_records[opponents_opponent]["wins"]
                opponents_opponent_wins += 0.5 * team_records[opponents_opponent]["draws"]
            opponents_opponent_wins = (
                opponents_opponent_wins
                - team_records[opponent]["losses"] # don't count wins against this opponent, we only want to know
                - 0.5 * team_records[opponent]["draws"] # how the team is against the field
            )
        opponents_opponents_wins_against_other_teams[team] = opponents_opponent_wins
    
    return match_results_by_team, team_points_for, team_points_against, opponents_wins_against_other_teams, opponents_opponents_wins_against_other_teams, opponents_points_against_other_teams

def build_weekly_tables(match_results_by_team, team_points_for, team_points_against, opponent_wins, opponents_opponent_wins, opponent_points):
    df_results = pd.DataFrame(match_results_by_team).T
    df_points_for = pd.DataFrame(team_points_for).astype(float).T
    df_points_for.columns = df_results.columns = [str(i) for i in range(1, WEEKS + 1)]
    df_points_against = pd.DataFrame(team_points_against).astype(float).T
    df_points_against.columns = df_results.columns = [str(i) for i in range(1, WEEKS + 1)]

    or_percent = { team: 0 for team in df_results.index }
    oor_percent = { team: 0 for team in df_results.index }
    for team in df_results.index:
        or_percent[team] = opponent_wins[team] / (WEEKS * (WEEKS - 1))
        oor_percent[team] = opponents_opponent_wins[team] / (WEEKS * WEEKS * (WEEKS - 1))

    df_bcs_sos = pd.DataFrame({
        "OR Win %": or_percent,
        "OOR Win %": oor_percent
    })
    df_bcs_sos['BCS SOS'] = (2 * df_bcs_sos["OR Win %"] + df_bcs_sos["OOR Win %"]) / 3

    df_op_points = pd.DataFrame({"Opponents Points": opponent_points}).astype(float)

    return df_results, df_points_for, df_points_against, df_bcs_sos, df_op_points

# ----- Main CLI Output -----
def main():
    print("Fetching league data...")
    users = get_users(LEAGUE_ID)
    rosters = get_rosters(LEAGUE_ID)
    team_map = build_team_lookup(users, rosters)

    match_results_by_team, team_points_for, team_points_against, opponent_wins, opponents_opponent_wins, opponent_points = build_totals(LEAGUE_ID, team_map)

    print("Building tables...")
    df_results, df_points_for, df_points_against, df_bcs_sos, df_op_points = build_weekly_tables(match_results_by_team, team_points_for, team_points_against, opponent_wins, opponents_opponent_wins, opponent_points)

    print("\nWin/Loss Results by Week:")
    print(tabulate(df_results, headers="keys", tablefmt="pretty"))

    print("\nPoints Scored by Team Each Week:")
    print(tabulate(df_points_for, headers="keys", tablefmt="pretty"))
    
    print("\nPoints Scored against Team Each Week:")
    print(tabulate(df_points_against, headers="keys", tablefmt="pretty"))

    print("\nBCS-Style Strength of Schedule (Normalized Win %):")
    print(tabulate(df_bcs_sos, headers="keys", tablefmt="pretty", floatfmt=".3f"))
    
    print("\nPoints Scored by Opponents against Other Teams:")
    print(tabulate(df_op_points, headers="keys", tablefmt="pretty"))

if __name__ == "__main__":
    main()
