def generate_matchup_table(matchups_by_team):
    html = ['<section class="mt-16 overflow-x-auto">']
    html.append('<h2 class="text-xl font-bold mb-4">📊 Weekly Win/Loss Results</h2>')
    html.append('<table class="table-auto border-collapse w-full text-sm">')

    html.append('<thead><tr><th class="border px-2 py-1 text-left">Team</th>')
    weeks = len(next(iter(matchups_by_team.values())))
    for week in range(1, weeks + 1):
        html.append(f'<th class="border px-2 py-1">{week}</th>')
    html.append('</tr></thead><tbody>')

    # Assign color per matchup per week
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

    for team, matchups in matchups_by_team.items():
        html.append(f'<tr><td class="border px-2 py-1">{team}</td>')
        for week_idx, matchup in enumerate(matchups):
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
            html.append(f'<td class="border px-2 py-1 {color} {bg}">{result}</td>')
        html.append('</tr>')

    html.append('</tbody></table></section>')
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

