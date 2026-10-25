#!/usr/bin/env python3
"""Bazaar of Lies — Visualizations.

Generate:
- Merchant network graph (who votes for whom).
- Reputation timeline (line chart of reputation scores per cycle).
- Word clouds (most frequent words in statements per cycle).

Usage: uv run tools/visualize.py --match 1 --cycle 2
"""

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from wordcloud import WordCloud

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False


def load_ballots(match: int, cycle: int) -> dict:
    """Load ballots for a given match and cycle."""
    ballots = defaultdict(list)
    path = f"gameplay/village/ballot-c{cycle:03d}.md"
    if not os.path.exists(path):
        return ballots
    
    with open(path, "r") as f:
        for line in f:
            if not line.startswith("|") or "---" in line:
                continue
            cells = [c.strip() for c in line.split("|")]
            if len(cells) >= 3:
                voter, target = cells[1], cells[2]
                ballots[voter].append(target)
    return ballots


def generate_network_graph(match: int, cycle: int, output_dir: str):
    """Generate a merchant network graph using graphviz."""
    if not GRAPHVIZ_AVAILABLE:
        print("graphviz not installed. Skipping network graph.")
        return
    
    ballots = load_ballots(match, cycle)
    dot = graphviz.Digraph(comment=f"Match {match}, Cycle {cycle}")
    
    # Add nodes
    for voter in ballots:
        dot.node(voter, voter)
    
    # Add edges
    for voter, targets in ballots.items():
        for target in targets:
            dot.edge(voter, target)
    
    # Render
    output_path = f"{output_dir}/network-c{cycle:03d}.png"
    dot.render(filename=output_path, format="png", cleanup=True)
    print(f"Network graph saved to {output_path}")


def generate_reputation_timeline(match: int, output_dir: str):
    """Generate a reputation timeline (placeholder)."""
    # TODO: Implement when reputation system is added
    print("Reputation timeline not yet implemented (requires reputation system).")


def generate_word_cloud(match: int, cycle: int, output_dir: str):
    """Generate a word cloud from statements."""
    statements_dir = f"gameplay/village/statements"
    text = ""
    
    for file in os.listdir(statements_dir):
        if not file.startswith(f"c{cycle:03d}-"):
            continue
        with open(f"{statements_dir}/{file}", "r") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    text += record.get("text", "") + " "
                except json.JSONDecodeError:
                    continue
    
    if not text:
        print(f"No statements found for cycle {cycle}.")
        return
    
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)
    output_path = f"{output_dir}/wordcloud-c{cycle:03d}.png"
    wordcloud.to_file(output_path)
    print(f"Word cloud saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Bazaar of Lies — Visualizations")
    parser.add_argument("--match", type=int, required=True, help="Match number")
    parser.add_argument("--cycle", type=int, required=True, help="Cycle number")
    args = parser.parse_args()
    
    output_dir = f"gameplay/visualizations/match-{args.match:02d}"
    os.makedirs(output_dir, exist_ok=True)
    
    generate_network_graph(args.match, args.cycle, output_dir)
    generate_reputation_timeline(args.match, output_dir)
    generate_word_cloud(args.match, args.cycle, output_dir)


if __name__ == "__main__":
    main()