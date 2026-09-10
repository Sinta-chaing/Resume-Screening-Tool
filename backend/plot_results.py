"""
Plot benchmark results from benchmark_results.json.

Usage:
    python plot_results.py                        # default benchmark_results.json
    python plot_results.py path/to/results.json   # custom file
    python plot_results.py --save results.png     # save to file
"""

import json
import sys
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


def load_results(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def shorten(name: str) -> str:
    return name


def plot_all(results: list[dict], save_path: str | None = None):
    ok = [r for r in results if r["status"] == "ok"]
    if not ok:
        print("No successful results to plot.")
        return

    labels = [f"{shorten(r['embed'])}\n+ {shorten(r['chat'])}" for r in ok]
    scores = [r["score"] for r in ok]
    skill_ov = [r["skill_overlap"] for r in ok]
    embed_sim = [r["embed_sim"] for r in ok]
    times = [r["time_total"] for r in ok]
    embed_times = [r["time_embed"] for r in ok]
    narrative_times = [r["time_narrative"] for r in ok]

    colors = plt.cm.Set2(np.linspace(0, 1, len(ok)))
    x = np.arange(len(ok))
    width = 0.55

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Resume Screening Model Benchmark", fontsize=16, fontweight="bold")

    # --- 1. Score comparison ---
    ax = axes[0, 0]
    bars = ax.bar(x, scores, width, color=colors, edgecolor="#333", linewidth=0.5)
    ax.set_ylabel("Score")
    ax.set_title("Overall Score")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, 105)
    for bar, val in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                str(val), ha="center", va="bottom", fontweight="bold", fontsize=10)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(20))

    # --- 2. Score breakdown ---
    ax = axes[0, 1]
    bar_w = 0.35
    ax.bar(x - bar_w / 2, skill_ov, bar_w, label="Skill Overlap", color="#4C72B0", edgecolor="#333", linewidth=0.5)
    ax.bar(x + bar_w / 2, embed_sim, bar_w, label="Embed Similarity", color="#55A868", edgecolor="#333", linewidth=0.5)
    ax.set_ylabel("Percentage (%)")
    ax.set_title("Score Breakdown")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, 105)
    ax.legend(fontsize=9)

    # --- 3. Timing breakdown ---
    ax = axes[1, 0]
    other_times = [t - e - n for t, e, n in zip(times, embed_times, narrative_times)]
    ax.bar(x, embed_times, width, label="Embedding", color="#4C72B0", edgecolor="#333", linewidth=0.5)
    ax.bar(x, narrative_times, width, bottom=embed_times, label="Narrative", color="#C44E52", edgecolor="#333", linewidth=0.5)
    bottom2 = [e + n for e, n in zip(embed_times, narrative_times)]
    ax.bar(x, other_times, width, bottom=bottom2, label="Scoring + Other", color="#8172B2", edgecolor="#333", linewidth=0.5)
    ax.set_ylabel("Time (seconds)")
    ax.set_title("Timing Breakdown")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.legend(fontsize=9)

    # --- 4. Score vs Time scatter ---
    ax = axes[1, 1]
    scatter = ax.scatter(times, scores, c=colors, s=150, edgecolors="#333", linewidths=0.8, zorder=5)
    for i, label in enumerate(labels):
        ax.annotate(label.replace("\n", " "), (times[i], scores[i]),
                    textcoords="offset points", xytext=(8, 5), fontsize=7.5)
    ax.set_xlabel("Total Time (seconds)")
    ax.set_ylabel("Score")
    ax.set_title("Score vs Speed")
    ax.set_ylim(0, 105)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(20))
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved to {save_path}")
    else:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_chart.png")
        plt.savefig(out, dpi=150, bbox_inches="tight")
        print(f"Saved to {out}")

    plt.close()


def main():
    path = "benchmark_results.json"
    save_path = None
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--save" and i + 1 < len(args):
            save_path = args[i + 1]
        elif not arg.startswith("--"):
            path = arg

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(path):
        path = os.path.join(script_dir, path)

    if not os.path.exists(path):
        print(f"File not found: {path}")
        print("Run 'python benchmark.py' first to generate results.")
        return

    results = load_results(path)
    plot_all(results, save_path)


if __name__ == "__main__":
    main()
