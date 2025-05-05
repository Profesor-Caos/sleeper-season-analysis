import requests
import pandas as pd

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
def build_team_lookup(league_id):
    users = get_users(league_id)
    rosters = get_rosters(league_id)
    user_id_to_name = {u['user_id']: u['display_name'] for u in users}
    team_map = {}
    for r in rosters:
        owner_id = r['owner_id']
        team_id = r['roster_id']
        team_map[team_id] = user_id_to_name.get(owner_id, f"Team {team_id}")
    return team_map

def get_all_team_matchups(league_id, team_map, weeks):
    matchups_by_team = {team: [{}] * weeks for team in team_map.values()}
    for week in range(1, weeks + 1):
        match_id_to_teams_involved = {}
        matchups = get_matchups(league_id, week)
        
        for team in matchups:
            team_id = team_map.get(team['roster_id'], f"T{team['roster_id']}")
            matchup_id = team.get('matchup_id')
            points_scored = team.get('points', 0)
            if matchup_id is not None:
                match_id_to_teams_involved.setdefault(matchup_id, []).append((team_id, points_scored))

            
        for matchup in match_id_to_teams_involved.values():
            if len(matchup) == 2:
                (team1, pts1), (team2, pts2) = matchup
                matchups_by_team[team1][week-1] = {
                    "opp": team2,
                    "points_for": pts1,
                    "points_against": pts2,
                    "result": 'W' if pts1 > pts2 else 'L' if pts1 < pts2 else 'D'
                }
                matchups_by_team[team2][week-1] = {
                    "opp": team1,
                    "points_for": pts2,
                    "points_against": pts1,
                    "result": 'W' if pts2 > pts1 else 'L' if pts2 < pts1 else 'D'
                }
            else:
                for team, _ in matchup:
                    matchups_by_team[team][week-1] = {
                        "opp": None,
                        "points_for": 0,
                        "points_against": 0,
                        "result": None
                    }
    return matchups_by_team

def get_season_stats_by_team(matchups_by_team):
    weeks = len(next(iter(matchups_by_team.values())))
    season_stats_by_team = {team: {
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "points_for": 0,
        "points_against": 0,
    } for team in matchups_by_team}
    for team in matchups_by_team:
        for week in matchups_by_team[team]:
            if week["result"] == 'W':
                season_stats_by_team[team]["wins"] += 1
            elif week["result"] == 'L':
                season_stats_by_team[team]["losses"] += 1
            elif week["result"] == 'D':
                season_stats_by_team[team]["draws"] += 1
            season_stats_by_team[team]["points_for"] += week["points_for"]
            season_stats_by_team[team]["points_against"] += week["points_against"]

    for team in season_stats_by_team:
        stats = season_stats_by_team[team]
        stats["win %"] = 100 * (stats["wins"] + 0.5 * stats["draws"]) / len(matchups_by_team[team])

    for team in matchups_by_team:
        opp_wins = 0
        opp_points = 0
        opp_opp_wins = 0
        opp_opp_points = 0
        for week in matchups_by_team[team]:
            opp_wins += season_stats_by_team[week["opp"]]["wins"]
            opp_wins += 0.5 * season_stats_by_team[week["opp"]]["draws"]
            opp_points += season_stats_by_team[week["opp"]]["points_for"]
            for opp_week in matchups_by_team[week["opp"]]:
                opp_opp_wins += season_stats_by_team[opp_week["opp"]]["wins"]
                opp_opp_wins += 0.5 * season_stats_by_team[opp_week["opp"]]["draws"]
                opp_opp_points += season_stats_by_team[opp_week["opp"]]["points_for"]
            opp_opp_wins = (
                opp_opp_wins
                - season_stats_by_team[week["opp"]]["losses"]
                - 0.5 * season_stats_by_team[week["opp"]]["draws"]
            )
            opp_opp_points = (
                opp_opp_points
                - season_stats_by_team[week["opp"]]["points_against"]
            )
        season_stats_by_team[team]["opp_wins"] = (
            opp_wins # all the wins opp had
            - season_stats_by_team[team]["losses"] # only count wins they had against other teams
            - 0.5 * season_stats_by_team[team]["draws"] # ignore draws against the team being analyzed as well
        )
        season_stats_by_team[team]["opp_points"] = (
            # ignore points against the team being analyzed when counting
            # points scored by other teams
            opp_points - season_stats_by_team[team]["points_against"]
        )
        season_stats_by_team[team]["opp_opp_wins"] = opp_opp_wins
        season_stats_by_team[team]["opp_opp_points"] = opp_opp_points

    league_total_points = sum(stats["points_for"] for stats in season_stats_by_team.values()) 
    league_average_points = league_total_points / len(season_stats_by_team)

    for team in season_stats_by_team:
        stats = season_stats_by_team[team]
        stats["points_for_normalized"] = stats["points_for"] / league_average_points
        stats["points_against_normalized"] = stats["points_against"] / league_average_points
        stats["opp win %"] = 100 * stats["opp_wins"] / (weeks * (weeks - 1))
        stats["opp opp win %"] = 100 * stats["opp_opp_wins"] / (weeks * weeks * (weeks - 1))
        stats["opp_points_normalized"] = stats["opp_points"] / (league_average_points * (weeks - 1))
        stats["opp_opp_points_normalized"] = stats["opp_opp_points"] / (league_average_points * weeks * (weeks - 1))
        stats["luck_factor"] = stats["opp_points_normalized"] - stats["points_against_normalized"]

    return season_stats_by_team