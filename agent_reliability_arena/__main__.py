from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import (
    append_trend,
    generate_dashboard,
    generate_trend_dashboard,
    import_maxima_report,
    load_trend,
    run_arena,
    threshold_violations,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-reliability-arena",
        description="Evaluate AI agent reliability cases and transcript health.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run reliability evals.")
    run.add_argument("--cases", required=True, help="Path to eval cases JSON.")
    run.add_argument("--transcript", help="Optional transcript JSONL path.")
    run.add_argument("--out", required=True, help="Output report JSON path.")

    gate = sub.add_parser("gate", help="Fail when a report crosses reliability thresholds.")
    gate.add_argument("--report", required=True, help="Arena report JSON path.")
    gate.add_argument("--min-quality", type=int, help="Minimum allowed quality score (0-100).")
    gate.add_argument("--max-quality", type=int, help="Maximum allowed quality score (0-100).")
    gate.add_argument("--min-fail", type=int, help="Minimum required hard-failure count.")
    gate.add_argument("--max-fail", type=int, help="Maximum allowed hard-failure count.")
    gate.add_argument("--max-warn", type=int, help="Maximum allowed warning count.")

    dash = sub.add_parser("dashboard", help="Generate static HTML dashboard from a report.")
    dash.add_argument("--report", required=True, help="Report JSON path.")
    dash.add_argument("--out", required=True, help="Output dashboard HTML path.")

    maxima = sub.add_parser("import-maxima", help="Import Maxima Eval Lab JSON into an Arena report.")
    maxima.add_argument("--url", help="Full /eval-lab.json URL. Avoid committing URLs with tokens.")
    maxima.add_argument("--base-url", default="https://maxima-v3-production.up.railway.app", help="Maxima service base URL.")
    maxima.add_argument("--token", help="Sync token. Prefer --token-env for privacy.")
    maxima.add_argument("--token-env", default="SYNC_SECRET", help="Environment variable containing the sync token.")
    maxima.add_argument("--out", required=True, help="Output Arena report JSON path.")
    maxima.add_argument("--trend-out", help="Optional trend JSON path to append a compact daily row.")

    trend = sub.add_parser("trend-dashboard", help="Generate static HTML dashboard from a trend JSON file.")
    trend.add_argument("--trend", required=True, help="Trend JSON path created by import-maxima --trend-out.")
    trend.add_argument("--out", required=True, help="Output trend dashboard HTML path.")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        report = run_arena(Path(args.cases), Path(args.transcript) if args.transcript else None)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        summary = report["summary"]
        print(
            "Agent Reliability Arena: "
            f"{summary['pass']} pass / {summary['warn']} warn / {summary['fail']} fail "
            f"- quality {summary['quality_score']}/100"
        )
        return 0

    if args.command == "gate":
        limits = {
            "min_quality": args.min_quality,
            "max_quality": args.max_quality,
            "min_fail": args.min_fail,
            "max_fail": args.max_fail,
            "max_warn": args.max_warn,
        }
        if all(value is None for value in limits.values()):
            parser.error("gate requires at least one threshold")
        for name in ("min_quality", "max_quality"):
            value = limits[name]
            if value is not None and not 0 <= value <= 100:
                parser.error(f"--{name.replace('_', '-')} must be between 0 and 100")
        for name in ("min_fail", "max_fail", "max_warn"):
            value = limits[name]
            if value is not None and value < 0:
                parser.error(f"--{name.replace('_', '-')} must be non-negative")

        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        violations = threshold_violations(report, **limits)
        summary = report.get("summary", {})
        measured = (
            f"quality {summary.get('quality_score', 'missing')}/100, "
            f"fail {summary.get('fail', 'missing')}, warn {summary.get('warn', 'missing')}"
        )
        if violations:
            print(f"Reliability gate FAILED: {measured}")
            for violation in violations:
                print(f"- {violation}")
            return 1
        print(f"Reliability gate passed: {measured}")
        return 0

    if args.command == "dashboard":
        report_path = Path(args.report)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        html = generate_dashboard(report)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"Dashboard written to {out}")
        return 0

    if args.command == "import-maxima":
        report = import_maxima_report(
            url=args.url or "",
            base_url=args.base_url,
            token=args.token or "",
            token_env=args.token_env,
        )
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        if args.trend_out:
            append_trend(report, Path(args.trend_out))
        summary = report["summary"]
        print(
            "Imported Maxima Eval Lab: "
            f"{summary['pass']} pass / {summary['warn']} warn / {summary['fail']} fail "
            f"- quality {summary['quality_score']}/100"
        )
        if args.trend_out:
            print(f"Trend updated at {args.trend_out}")
        return 0

    if args.command == "trend-dashboard":
        trend = load_trend(Path(args.trend))
        html = generate_trend_dashboard(trend)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"Trend dashboard written to {out}")
        return 0

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
