# sleeper-season-analysis/main.py

import pandas as pd
from tabulate import tabulate
from sleeper_stats import build_team_lookup, get_all_team_matchups, get_season_stats_by_team
from stat_outputs import generate_matchup_table, inject_tables

LEAGUE_ID = "1127468541545930752"
WEEKS = 14

def main():
    print("Fetching team data...")
    team_map = build_team_lookup(LEAGUE_ID)
    matchups_by_team = get_all_team_matchups(LEAGUE_ID, team_map, WEEKS)

    html = generate_matchup_table(matchups_by_team)
    inject_tables("web/index.html", html)

    season_stats = get_season_stats_by_team(matchups_by_team)

    df_stats = pd.DataFrame(season_stats).T
    df_stats = df_stats.sort_values(by="wins", ascending=False)
    # print(tabulate(df_stats, headers="keys", tablefmt="pretty", floatfmt=".2f"))

    avg_row = df_stats.mean(numeric_only=True)
    avg_row.name = "League Average"
    df_stats_with_avg = pd.concat([df_stats, pd.DataFrame([avg_row])])
    df_stats_with_avg = df_stats_with_avg.round(4)

    df_stats_with_avg.index = df_stats_with_avg.index.astype(str)
    df_view = df_stats_with_avg[["points_for", "points_against", "opp_points", "points_for_normalized", "points_against_normalized", "opp_points_normalized", "luck_factor"]]
    df_view = df_view.rename(columns={
        "points_for": "Points For", 
        "points_against": "Points Against", 
        "opp_points": "Opponents' Points Against Other Teams", 
        "points_for_normalized": "PF Normalized", 
        "points_against_normalized": "PA Normalized", 
        "opp_points_normalized": "Op Pts Normalized", 
        "luck_factor": "Luck Factor (PA nmlzd - Op Pts nmlzd)"
    })
    print("\nSeason Summary:")
    print(tabulate(df_view, headers="keys", tablefmt="pretty", floatfmt=".2f"))

if __name__ == "__main__":
    main()
