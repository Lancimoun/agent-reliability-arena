#!/usr/bin/env python3
"""
build_leaderboard.py — turn an Axiom reliability-benchmark report into the
docs/leaderboard.json the Arena page renders.

Two modes:
  1. Live:  reads AXIOM_URL + AXIOM_API_KEY from env, POSTs /benchmark/reliability,
            then writes docs/leaderboard.json.   (used by the GitHub Action)
  2. File:  --report path/to/report.json  (for local testing, no API spend)

The page (docs/index.html) expects:
  { "rows": [ {rank, agent, provider, score, verdict, cost, latency, source} ],
    "provider_queue": [ {provider, status, probe_focus} ] }

Deterministic Arena anchors (Foundation 100, Drift 40) are always included so the
board has stable reference points; Maxima's live score is filled in by the page
from maxima-trend.json. Provider rows come from the real Axiom run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
OUT = DOCS / "leaderboard.json"

DISPLAY = {"claude": "Claude", "openai": "GPT", "gemini": "Gemini", "groq": "Groq", "maxima": "Maxima"}
FOCUS = {
    "claude": "reasoning transparency, tool honesty, concise completion",
    "openai": "current-truth override, instruction following, memory caveats",
    "gemini": "stale fact resistance, directness, citation honesty",
    "groq": "speed, completion quality, hallucinated capability claims",
    "maxima": "memory drift, current-truth override, transcript health",
}

# Free deterministic reference rows — always on the board.
ANCHORS = [
    {"agent": "Foundation Reference Agent", "provider": "Local deterministic suite",
     "score": 100, "verdict": "Reliable", "cost": "Free", "latency": "Local",
     "source": "cases/maxima_foundation.json"},
    {"agent": "Maxima Live Eval", "provider": "Railway import",
     "score": None, "verdict": "Auto-updates from trend", "cost": "Existing infra",
     "latency": "Daily", "source": "maxima-trend.json"},
    {"agent": "Drift Demo Agent", "provider": "Intentional failure sample",
     "score": 40, "verdict": "Patch", "cost": "Free", "latency": "Local",
     "source": "cases/drift_demo.json"},
]


def fetch_report() -> dict:
    url = os.environ["AXIOM_URL"].rstrip("/") + "/benchmark/reliability"
    key = os.environ["AXIOM_API_KEY"]
    providers = [p.strip() for p in os.getenv("AXIOM_PROVIDERS", "claude,openai,gemini,groq,maxima").split(",") if p.strip()]
    body = json.dumps({"providers": providers, "include_responses": False}).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": key},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def to_leaderboard(report: dict) -> dict:
    generated = report.get("generated_at") or datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [dict(a) for a in ANCHORS]
    queue = []

    for prov in report.get("providers", []):
        name = str(prov.get("provider", "")).lower()
        display = DISPLAY.get(name, prov.get("provider", name).title())
        status = prov.get("status")
        if status == "skipped":
            queue.append({"provider": display, "status": prov.get("verdict") or "Skipped — not configured",
                          "probe_focus": FOCUS.get(name, "")})
            continue
        score = prov.get("score")
        if not isinstance(score, int):
            queue.append({"provider": display, "status": "Run incomplete",
                          "probe_focus": FOCUS.get(name, "")})
            continue
        # Maxima is represented by the trend-merged anchor row; don't duplicate.
        if name == "maxima":
            queue.append({"provider": display, "status": f"Scored {generated[:10]} · {score}/100",
                          "probe_focus": FOCUS.get(name, "")})
            continue
        latency = prov.get("avg_latency_ms")
        tokens = prov.get("total_tokens") or 0
        rows.append({
            "agent": f"{display} (via Axiom)",
            "provider": prov.get("model") or display,
            "score": score,
            "verdict": prov.get("verdict") or "",
            "cost": f"{tokens} tok",
            "latency": f"{latency} ms" if isinstance(latency, int) else "—",
            "source": "Axiom · /benchmark/reliability",
        })
        queue.append({"provider": display, "status": f"Scored {generated[:10]}",
                      "probe_focus": FOCUS.get(name, "")})

    # sort rows by score desc (None last) and re-rank
    rows.sort(key=lambda r: r["score"] if isinstance(r.get("score"), int) else -1, reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    return {
        "generated_at": generated,
        "suite": report.get("suite", "arena-v1"),
        "probe_count": report.get("probe_count"),
        "run_id": report.get("run_id"),
        "rows": rows,
        "provider_queue": queue,
        "notes": report.get("notes", []),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="Path to a saved Axiom report JSON (skips the live call)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8")) if args.report else fetch_report()
    board = to_leaderboard(report)
    Path(args.out).write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")
    scored = [r for r in board["rows"] if isinstance(r.get("score"), int)]
    print(f"wrote {args.out}: {len(board['rows'])} rows ({len(scored)} scored), "
          f"{len(board['provider_queue'])} provider statuses")
    return 0


if __name__ == "__main__":
    sys.exit(main())
