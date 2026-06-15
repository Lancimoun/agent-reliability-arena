#!/usr/bin/env python3
"""
build_leaderboard.py — run the Axiom reliability benchmark N times and turn the
aggregate into the docs/leaderboard.json the Arena page renders.

Why multi-run: agents are non-deterministic. A single run is noisy (we watched
Gemini swing 31–91). Running each provider several times and reporting the MEAN
plus the RANGE makes the board trustworthy — and surfaces who is consistent vs
who rolls the dice.

Modes:
  Live:    AXIOM_URL + AXIOM_API_KEY env, POSTs /benchmark/reliability AXIOM_RUNS times
           (default 3).                                       (used by the GitHub Action)
  File:    --report r.json            single saved report (testing)
           --reports a.json b.json …  several saved reports  (testing multi-run)

Page contract (docs/index.html):
  { "rows": [ {rank, agent, provider, score, verdict, cost, latency, source} ],
    "provider_queue": [ {provider, status, probe_focus} ] }
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
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
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _first_error(prov: dict) -> str:
    for pr in prov.get("probes", []):
        if pr.get("error"):
            return str(pr["error"])
        for c in pr.get("checks", []):
            if c.get("name") == "provider_call" and c.get("status") == "fail":
                return str(c.get("detail", ""))
    return ""


def _first_error_any(runs: list[dict]) -> str:
    for prov in runs:
        e = _first_error(prov)
        if e:
            return e
    return ""


def _clean(reason: str) -> str:
    return re.sub(r"^\d{3}:\s*", "", str(reason or "")).strip()


def _verdict_for(score: int) -> str:
    if score >= 90:
        return "Reliable"
    if score >= 70:
        return "Watch"
    if score >= 50:
        return "Patch"
    return "High risk"


def aggregate(reports: list[dict]) -> dict:
    n = len(reports)
    generated = reports[-1].get("generated_at") or datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [dict(a) for a in ANCHORS]
    queue = []

    grouped: dict[str, list[dict]] = {}
    order: list[str] = []
    for rep in reports:
        for prov in rep.get("providers", []):
            name = str(prov.get("provider", "")).lower()
            if name not in grouped:
                grouped[name] = []
                order.append(name)
            grouped[name].append(prov)

    for name in order:
        runs = grouped[name]
        display = DISPLAY.get(name, name.title())
        focus = FOCUS.get(name, "")
        scored = [r.get("score") for r in runs if r.get("completed_probes") and isinstance(r.get("score"), int)]

        if name == "maxima":
            if scored:
                m = round(statistics.mean(scored))
                queue.append({"provider": display, "status": f"Scored · mean {m}/100 ({len(scored)}/{n} runs)", "probe_focus": focus})
            else:
                queue.append({"provider": display, "status": _clean(_first_error_any(runs) or runs[0].get("verdict") or "skipped")[:140], "probe_focus": focus})
            continue

        if not scored:
            queue.append({"provider": display, "status": _clean(_first_error_any(runs) or runs[0].get("verdict") or "All runs failed")[:140], "probe_focus": focus})
            continue

        m, lo, hi = round(statistics.mean(scored)), min(scored), max(scored)
        verdict = _verdict_for(m) if lo == hi else f"{_verdict_for(m)} · {lo}–{hi}"
        lats = [r.get("avg_latency_ms") for r in runs if isinstance(r.get("avg_latency_ms"), int)]
        avglat = round(statistics.mean(lats)) if lats else None
        model = next((r.get("model") for r in runs if r.get("model")), display)
        rows.append({
            "agent": f"{display} (via Axiom)",
            "provider": model,
            "score": m,
            "verdict": verdict,
            "cost": f"{len(scored)}× runs",
            "latency": f"{avglat} ms" if avglat else "—",
            "source": "Axiom · /benchmark/reliability",
        })
        spread = "consistent" if lo == hi else f"range {lo}–{hi}"
        queue.append({"provider": display, "status": f"Scored · mean {m}, {spread} ({len(scored)}/{n} runs)", "probe_focus": focus})

    rows.sort(key=lambda r: r["score"] if isinstance(r.get("score"), int) else -1, reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    return {
        "generated_at": generated,
        "suite": reports[-1].get("suite", "arena-v1"),
        "probe_count": reports[-1].get("probe_count"),
        "runs": n,
        "rows": rows,
        "provider_queue": queue,
        "notes": [
            f"Each provider was run {n}× through the same probe suite; score is the mean, with the range shown when it varied.",
            "Deterministic heuristic checks — not subjective model-grade claims.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="Single saved Axiom report JSON (testing)")
    ap.add_argument("--reports", nargs="*", help="Several saved report JSONs (testing multi-run)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    if args.reports:
        reports = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.reports]
    elif args.report:
        reports = [json.loads(Path(args.report).read_text(encoding="utf-8"))]
    else:
        n = max(1, min(int(os.getenv("AXIOM_RUNS", "3") or 3), 5))
        print(f"running benchmark {n}× ...")
        reports = [fetch_report() for _ in range(n)]

    # Diagnostics: surface the first real error per failing provider, per run.
    for i, rep in enumerate(reports, 1):
        for prov in rep.get("providers", []):
            err = _first_error(prov)
            if err:
                print(f"[diag] run{i} {prov.get('provider')}: {err[:300]}")

    board = aggregate(reports)
    Path(args.out).write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")
    scored = [r for r in board["rows"] if isinstance(r.get("score"), int)]
    print(f"wrote {args.out}: {board['runs']} run(s), {len(board['rows'])} rows "
          f"({len(scored)} scored), {len(board['provider_queue'])} provider statuses")
    return 0


if __name__ == "__main__":
    sys.exit(main())
