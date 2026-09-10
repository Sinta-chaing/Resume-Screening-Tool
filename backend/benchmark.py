"""
Benchmark: compare embedding + chat model combinations for resume screening.

Usage:
    python benchmark.py                              # uses defaults
    python benchmark.py --resume path/to/resume.pdf --jd path/to/jd.txt
    python benchmark.py --embed mxbai-embed-large
    python benchmark.py --chat llama3.2,gemma2
"""

import argparse
import os
import sys
import time
import json

import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from screening.services.pdf_extractor import extract_text_from_file
from screening.services.chunking import chunk_text
from screening.services.ollama import embed, chat
from screening.services.scoring import compute_hybrid_score
from screening.services.ats import evaluate_resume
from screening.services.summary import summarize_resume

OLLAMA_BASE = "http://localhost:11434"


def _pull_check(model: str) -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=10)
        names = [m["name"] for m in r.json().get("models", [])]
        return model in names or f"{model}:latest" in names
    except Exception:
        return False


def _list_models() -> list[str]:
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=10)
        return [m["name"].replace(":latest", "") for m in r.json().get("models", [])]
    except Exception:
        return []


def run_one(resume_text: str, jd_text: str, embed_model: str, chat_model: str) -> dict:
    result = {
        "embed": embed_model,
        "chat": chat_model,
        "status": "ok",
        "score": 0,
        "skill_overlap": 0,
        "embed_sim": 0,
        "matched": 0,
        "missing": 0,
        "jd_requirements": 0,
        "strengths": 0,
        "gaps": 0,
        "suggestions": 0,
        "time_chunks": 0,
        "time_embed": 0,
        "time_score": 0,
        "time_narrative": 0,
        "time_summary": 0,
        "time_total": 0,
    }

    try:
        t0 = time.perf_counter()

        t1 = time.perf_counter()
        chunks = chunk_text(resume_text)
        result["time_chunks"] = time.perf_counter() - t1

        t1 = time.perf_counter()
        embeddings = []
        for chunk in chunks:
            old = django.conf.settings.EMBEDDING_MODEL
            django.conf.settings.EMBEDDING_MODEL = embed_model
            try:
                embeddings.append(embed(chunk))
            finally:
                django.conf.settings.EMBEDDING_MODEL = old
        result["time_embed"] = time.perf_counter() - t1

        t1 = time.perf_counter()
        old_chat = django.conf.settings.CHAT_MODEL
        django.conf.settings.CHAT_MODEL = chat_model
        try:
            hybrid = compute_hybrid_score(resume_text, jd_text, embeddings)
        finally:
            django.conf.settings.CHAT_MODEL = old_chat
        result["time_score"] = time.perf_counter() - t1

        bd = hybrid.get("scoreBreakdown", {})
        result["score"] = hybrid.get("score", 0)
        result["skill_overlap"] = bd.get("skillOverlap", 0)
        result["embed_sim"] = bd.get("embeddingSimilarity", 0)
        result["matched"] = len(bd.get("matchedSkills", []))
        result["missing"] = len(bd.get("missingSkills", []))
        result["jd_requirements"] = bd.get("jdSkillCount", 0)

        t1 = time.perf_counter()
        django.conf.settings.CHAT_MODEL = chat_model
        try:
            evaluation = evaluate_resume(resume_text, jd_text, embeddings)
        finally:
            django.conf.settings.CHAT_MODEL = old_chat
        result["time_narrative"] = time.perf_counter() - t1
        result["strengths"] = len(evaluation.get("strengths", []))
        result["gaps"] = len(evaluation.get("gaps", []))
        result["suggestions"] = len(evaluation.get("suggestions", []))

        t1 = time.perf_counter()
        django.conf.settings.CHAT_MODEL = chat_model
        try:
            summarize_resume(resume_text)
        finally:
            django.conf.settings.CHAT_MODEL = old_chat
        result["time_summary"] = time.perf_counter() - t1

        result["time_total"] = time.perf_counter() - t0

    except Exception as exc:
        result["status"] = f"error: {exc}"
        result["time_total"] = time.perf_counter() - t0

    return result


def _load_file(path: str) -> str:
    from pathlib import Path
    p = Path(path)
    class FakeFile:
        def __init__(self, path):
            self.name = path.name
            self._path = path
        def read(self):
            return self._path.read_bytes()
    return extract_text_from_file(FakeFile(p))


def print_table(results: list[dict]):
    cols = [
        ("Embed", 20), ("Chat", 12), ("Status", 7),
        ("Score", 5), ("SkillOv", 6), ("EmbSim", 5),
        ("Match", 5), ("Miss", 4),
        ("Strengths", 8), ("Gaps", 4), ("Sug", 3),
        ("Total(s)", 7),
    ]
    header = " | ".join(f"{n:>{w}}" for n, w in cols)
    sep = "-+-".join("-" * w for _, w in cols)
    print(header)
    print(sep)
    for r in results:
        status = "OK" if r["status"] == "ok" else "ERR"
        row = [
            f"{r['embed']:>20}", f"{r['chat']:>12}", f"{status:>7}",
            f"{r['score']:>5}", f"{r['skill_overlap']:>6}", f"{r['embed_sim']:>5}",
            f"{r['matched']:>5}", f"{r['missing']:>4}",
            f"{r['strengths']:>8}", f"{r['gaps']:>4}", f"{r['suggestions']:>3}",
            f"{r['time_total']:>7.1f}",
        ]
        print(" | ".join(row))


def print_detail(results: list[dict]):
    print("\n\nDetailed results:\n")
    for r in results:
        status = "OK" if r["status"] == "ok" else f"ERROR: {r['status']}"
        print(f"--- {r['embed']} + {r['chat']} [{status}] ---")
        print(f"  Score breakdown: {r['skill_overlap']}% skill overlap, {r['embed_sim']}% embed sim")
        print(f"  Requirements: {r['matched']} matched / {r['missing']} missing / {r['jd_requirements']} total")
        print(f"  Narrative: {r['strengths']} strengths, {r['gaps']} gaps, {r['suggestions']} suggestions")
        print(f"  Timing: chunks={r['time_chunks']:.3f}s  embed={r['time_embed']:.1f}s  "
              f"score={r['time_score']:.2f}s  narrative={r['time_narrative']:.1f}s  "
              f"summary={r['time_summary']:.1f}s  total={r['time_total']:.1f}s")
        print()


def analyze(results: list[dict]):
    ok = [r for r in results if r["status"] == "ok"]
    if not ok:
        print("No successful runs to analyze.")
        return

    best_score = max(ok, key=lambda r: r["score"])
    fastest = min(ok, key=lambda r: r["time_total"])
    best_balance = min(ok, key=lambda r: (100 - r["score"]) + r["time_total"] * 2)

    print("\n=== RECOMMENDATIONS ===\n")
    print(f"Highest score:   {best_score['embed']:20} + {best_score['chat']:12}  score={best_score['score']}")
    print(f"Fastest:         {fastest['embed']:20} + {fastest['chat']:12}  time={fastest['time_total']:.1f}s")
    print(f"Best balance:    {best_balance['embed']:20} + {best_balance['chat']:12}  "
          f"score={best_balance['score']} time={best_balance['time_total']:.1f}s")

    embed_groups: dict[str, list[dict]] = {}
    for r in ok:
        embed_groups.setdefault(r["embed"], []).append(r)

    print("\nEmbedding model averages:")
    for model, runs in sorted(embed_groups.items()):
        avg_score = sum(r["score"] for r in runs) / len(runs)
        avg_time = sum(r["time_embed"] for r in runs) / len(runs)
        print(f"  {model:25}  avg_score={avg_score:.0f}  avg_embed_time={avg_time:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Benchmark resume screening models")
    parser.add_argument("--resume", help="Path to resume file (PDF or TXT)")
    parser.add_argument("--jd", help="Path to job description file (PDF or TXT)")
    parser.add_argument("--embed", default="mxbai-embed-large",
                        help="Comma-separated embedding models to test")
    parser.add_argument("--chat", default="llama3.2",
                        help="Comma-separated chat models to test")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_dir = os.path.join(os.path.dirname(script_dir), "sample-data")
    resume_path = args.resume or os.path.join(sample_dir, "resume_sample.txt")
    jd_path = args.jd or os.path.join(sample_dir, "jd_sample.txt")

    print(f"Resume: {resume_path}")
    print(f"JD:     {jd_path}")

    resume_text = _load_file(resume_path)
    jd_text = _load_file(jd_path)
    print(f"Resume: {len(resume_text)} chars | JD: {len(jd_text)} chars\n")

    embed_models = [m.strip() for m in args.embed.split(",")]
    chat_models = [m.strip() for m in args.chat.split(",")]

    combos = []
    for em in embed_models:
        for cm in chat_models:
            if not _pull_check(em):
                print(f"SKIP {em}+{cm}: embedding model not available")
                continue
            if not _pull_check(cm):
                print(f"SKIP {em}+{cm}: chat model not available")
                continue
            combos.append((em, cm))

    if not combos:
        print("\nNo valid model combos.")
        print(f"Available locally: {', '.join(_list_models())}")
        print("Pull a model with: ollama pull <model>")
        return

    print(f"Testing {len(combos)} combinations:\n")

    results = []
    for i, (em, cm) in enumerate(combos):
        print(f"[{i+1}/{len(combos)}] {em} + {cm} ...", end=" ", flush=True)
        r = run_one(resume_text, jd_text, em, cm)
        status = "OK" if r["status"] == "ok" else "ERR"
        print(f"{status}  score={r['score']}  {r['time_total']:.1f}s")
        results.append(r)

    print("\n\n=== COMPARISON TABLE ===\n")
    print_table(results)
    analyze(results)

    out_path = os.path.join(script_dir, "benchmark_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nRaw results saved to {out_path}")
    print(f"Run 'python plot_results.py' to generate comparison charts.")


if __name__ == "__main__":
    main()