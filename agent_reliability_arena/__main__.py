from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import generate_dashboard, import_maxima_report, run_arena


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

    dash = sub.add_parser("dashboard", help="Generate static HTML dashboard from a report.")
    dash.add_argument("--report", required=True, help="Report JSON path.")
    dash.add_argument("--out", required=True, help="Output dashboard HTML path.")

    maxima = sub.add_parser("import-maxima", help="Import Maxima Eval Lab JSON into an Arena report.")
    maxima.add_argument("--url", help="Full /eval-lab.json URL. Avoid committing URLs with tokens.")
    maxima.add_argument("--base-url", default="https://maxima-v3-production.up.railway.app", help="Maxima service base URL.")
    maxima.add_argument("--token", help="Sync token. Prefer --token-env for privacy.")
    maxima.add_argument("--token-env", default="SYNC_SECRET", help="Environment variable containing the sync token.")
    maxima.add_argument("--out", required=True, help="Output Arena report JSON path.")

    return parser


def main() -> None:
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
        return

    if args.command == "dashboard":
        report_path = Path(args.report)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        html = generate_dashboard(report)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"Dashboard written to {out}")
        return

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
        summary = report["summary"]
        print(
            "Imported Maxima Eval Lab: "
            f"{summary['pass']} pass / {summary['warn']} warn / {summary['fail']} fail "
            f"- quality {summary['quality_score']}/100"
        )
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
