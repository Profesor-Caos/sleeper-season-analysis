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
        html = [f'<h2 class="text-xl font-bold mt-16 mb-4">{title}</h2>']
        html.append('<table class="table-auto border-collapse w-full text-sm">')
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

    html = ['<section class="mt-16 overflow-x-auto">']
    html.append(build_table("📊 Weekly Win/Loss Results", wl_cell))
    html.append(build_table("📈 Weekly Points Scored", points_cell))
    html.append('</section>')
    return '\n'.join(html)

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
