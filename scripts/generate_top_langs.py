#!/usr/bin/env python3
"""
Generate a simple top-langs SVG for a GitHub user.
Writes an SVG to the provided output path.
"""

import os
import sys
import argparse
import requests
from collections import Counter

GITHUB_API = "https://api.github.com"


def get_repos(username, session):
    repos = []
    page = 1
    while True:
        url = f"{GITHUB_API}/users/{username}/repos"
        params = {"per_page": 100, "page": page, "type": "owner", "sort": "pushed"}
        r = session.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def aggregate_languages(repos, session, include_forks=False):
    lang_counts = Counter()
    for repo in repos:
        if repo.get("fork") and not include_forks:
            continue
        langs_url = repo.get("languages_url")
        if not langs_url:
            continue
        r = session.get(langs_url)
        if r.status_code != 200:
            continue
        data = r.json()
        for lang, bytes_count in data.items():
            lang_counts[lang] += bytes_count
    return lang_counts


def make_svg(top_langs, username, width=600, bar_height=18, gap=8, padding=10):
    if not top_langs:
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="100" viewBox="0 0 {width} 100">
  <rect width="{width}" height="100" fill="#1a1b27"/>
  <text x="{width//2}" y="50" text-anchor="middle" fill="#c9d1d9" font-family="sans-serif" font-size="14">No language data available</text>
</svg>'''
        return svg

    labels_width = 150
    chart_width = width - labels_width - padding*2
    total = sum(v for _, v in top_langs)
    height = padding*2 + (bar_height + gap) * len(top_langs)

    rows = []
    rows.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    rows.append(f'  <rect width="{width}" height="{height}" fill="#1a1b27"/>')
    rows.append(f'  <text x="{padding}" y="{padding + 14}" fill="#c9d1d9" font-family="sans-serif" font-size="14" font-weight="bold">Top Languages</text>')
    
    y_offset = padding + 30
    colors = ["#3572A5", "#e34c26", "#f1e05a", "#178600", "#563d7c", "#89e051", "#b07219", "#555555"]
    
    for i, (lang, byte_count) in enumerate(top_langs):
        pct = (byte_count / total) * 100
        bar_width = (byte_count / total) * chart_width
        color = colors[i % len(colors)]
        
        # Language label
        rows.append(f'  <text x="{padding}" y="{y_offset + bar_height//2 + 4}" fill="#c9d1d9" font-family="sans-serif" font-size="12">{lang}</text>')
        
        # Bar
        bar_x = labels_width + padding
        rows.append(f'  <rect x="{bar_x}" y="{y_offset}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="3"/>')
        
        # Percentage
        pct_x = bar_x + bar_width + 5
        rows.append(f'  <text x="{pct_x}" y="{y_offset + bar_height//2 + 4}" fill="#c9d1d9" font-family="sans-serif" font-size="11">{pct:.1f}%</text>')
        
        y_offset += bar_height + gap
    
    rows.append('</svg>')
    return '\n'.join(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate top-langs SVG for a GitHub user")
    parser.add_argument("--username", required=True, help="GitHub username")
    parser.add_argument("--output", required=True, help="Output SVG path")
    parser.add_argument("--top", type=int, default=8, help="Number of top languages to display")
    parser.add_argument("--include-forks", action="store_true", help="Include forked repositories")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    session = requests.Session()
    if token:
        session.headers.update({"Authorization": f"token {token}"})
    session.headers.update({"Accept": "application/vnd.github.v3+json"})

    try:
        print(f"Fetching repositories for {args.username}...")
        repos = get_repos(args.username, session)
        print(f"Found {len(repos)} repositories")

        print("Aggregating language statistics...")
        lang_counts = aggregate_languages(repos, session, args.include_forks)
        
        if not lang_counts:
            print("No language data found")
            top_langs = []
        else:
            top_langs = lang_counts.most_common(args.top)
            print(f"Top languages: {', '.join(lang for lang, _ in top_langs)}")

        svg_content = make_svg(top_langs, args.username)
        
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w') as f:
            f.write(svg_content)
        
        print(f"SVG written to {args.output}")
        return 0

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
