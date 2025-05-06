def generate_matchup_tables(matchups_by_team):
    weeks = len(next(iter(matchups_by_team.values())))

    bg_classes = [
        "bg-blue-900/30",
        "bg-amber-800/30",
        "bg-purple-800/30",
        "bg-lime-800/30",
        "bg-rose-800/30",
        "bg-cyan-800/30"
    ]

    matchup_colors_by_week = [{} for _ in range(weeks)]
    for week_idx in range(weeks):
        used_pairs = set()
        color_idx = 0
        for team, matchups in matchups_by_team.items():
            opp = matchups[week_idx]['opp']
            pair = tuple(sorted((team, opp)))
            if pair not in used_pairs:
                used_pairs.add(pair)
                matchup_colors_by_week[week_idx][pair] = bg_classes[color_idx % len(bg_classes)]
                color_idx += 1

    def build_table(title, cell_func):
        html = [f'<h2 class="text-xl font-bold mt-4 mb-4">{title}</h2>']
        html.append('<table class="table-auto border-collapse text-sm mb-16">')
        html.append('<thead><tr><th class="border px-2 py-1 text-left">Team</th>')
        for week in range(1, weeks + 1):
            html.append(f'<th class="border px-2 py-1">{week}</th>')
        html.append('</tr></thead><tbody>')

        for team, matchups in matchups_by_team.items():
            html.append(f'<tr><td class="border px-2 py-1">{team}</td>')
            for week_idx, matchup in enumerate(matchups):
                html.append(cell_func(team, week_idx, matchup))
            html.append('</tr>')

        html.append('</tbody></table>')
        return '\n'.join(html)

    def wl_cell(team, week_idx, matchup):
        result = matchup.get("result", "-")
        opp = matchup.get("opp", "")
        pair = tuple(sorted((team, opp)))
        bg = matchup_colors_by_week[week_idx].get(pair, "")
        color = {
            'W': 'text-green-400',
            'L': 'text-red-400',
            'D': 'text-yellow-400',
            '-': 'text-gray-400'
        }.get(result, '')
        return f'<td class="border px-2 py-1 {color} {bg}">{result}</td>'

    def points_cell(team, week_idx, matchup):
        points = matchup.get("points_for", 0)
        opp = matchup.get("opp", "")
        opp_points = matchup.get("points_against", 0)
        pair = tuple(sorted((team, opp)))
        bg = matchup_colors_by_week[week_idx].get(pair, "")
        color = ''
        if isinstance(points, (int, float)) and isinstance(opp_points, (int, float)):
            if points > opp_points:
                color = 'text-green-400'
            elif points < opp_points:
                color = 'text-red-400'
            else:
                color = 'text-yellow-400'
        return f'<td class="border px-2 py-1 {color} {bg}">{points}</td>'
    
    html = [
        '<div class="w-screen px-4 -ml-4">',
        '<section class="overflow-x-auto px-2">'
    ]
    html.append(build_table("📊 Weekly Win/Loss Results", wl_cell))
    html.append(build_table("📈 Weekly Points Scored", points_cell))
    html.append('</section></div>')
    return '\n'.join(html)

def generate_summary_tables(season_stats_by_team):
    general_keys = [
        "wins", "losses", "win %", "points_for", "points_for_normalized", 
        "points_against", "points_against_normalized"
    ]

    sos_keys = [
        "opp win %", "opp opp win %", "win % sos", "opp_points",
        "opp_points_normalized", "points_against_normalized", "luck_factor"
    ]

    key_name_mappings = {
        "wins": "Wins",
        "losses": "Losses",
        "win %": "Win %",
        "points_for": "Points For",
        "points_for_normalized": "PF Normalized",
        "points_against": "Points Against",
        "points_against_normalized": "PA Normalized",
        "opp win %": "Opponents' Win %",
        "opp opp win %": "Opps' Opps' Win %",
        "win % sos": "BCS Style SoS",
        "opp_points": "Opponents' Points",
        "opp_points_normalized": "OP Normalized",
        "luck_factor": "Luck Factor"
    }

    def build_table(title, keys):
        # Compute min/max for heatmap coloring
        min_max = {
            k: (min(stats.get(k, 0) for stats in season_stats_by_team.values()),
                max(stats.get(k, 0) for stats in season_stats_by_team.values()))
            for k in keys
        }

        color_classes = [
            "bg-red-900/40",
            "bg-orange-700/40",
            "bg-yellow-600/40",
            "bg-lime-600/40",
            "bg-green-500/40"
        ]

        html = [f'<h2 class="text-xl font-bold mt-4 mb-4">{title}</h2>']
        html.append('<table class="sortable table-auto border-collapse text-sm mb-16">')
        html.append('<thead><tr><th class="border px-2 py-1 text-left">Team</th>')
        for k in keys:
            html.append(f'<th class="border px-2 py-1 text-left">{key_name_mappings[k]}</th>')
        html.append('</tr></thead><tbody>')

        for team, stats in season_stats_by_team.items():
            html.append(f'<tr><td class="border px-2 py-1">{team}</td>')
            for k in keys:
                val = stats.get(k, 0)
                num = val
                if isinstance(val, float):
                    val = f"{val:.2f}"
                min_val, max_val = min_max[k]
                norm = 0 if max_val == min_val else (num - min_val) / (max_val - min_val)
                idx = min(int(norm * (len(color_classes) - 1)), len(color_classes) - 1)
                bg = color_classes[idx]
                html.append(f'<td class="border px-2 py-1 {bg}">{val}</td>')
            html.append('</tr>')

        html.append('</tbody></table>')
        return ''.join(html)

    html = [
        '<div class="w-screen px-4 -ml-4">',
        '<section class="overflow-x-auto px-2">'
    ]
    html.append(build_table("🧮 General Stats", general_keys))
    html.append(build_table("📅 Strength of Schedule Stats", sos_keys))
    html.append('</section></div>')
    return ''.join(html)


def inject_tables(index_path, table_html):
    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()

    start = html.find("<!-- MATCHUP_TABLES_START -->")
    end = html.find("<!-- MATCHUP_TABLES_END -->")

    if start == -1 or end == -1:
        raise ValueError("Could not find MATCHUP_TABLES markers in HTML")

    new_html = (
        html[:start + len("<!-- MATCHUP_TABLES_START -->")] +
        "\n" + table_html + "\n" +
        html[end:]
    )

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(new_html)
