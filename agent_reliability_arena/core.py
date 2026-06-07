from __future__ import annotations

import html
import json
import os
import re
import statistics
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


PASS = "pass"
WARN = "warn"
FAIL = "fail"


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _contains_any(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return [term for term in terms if str(term).lower() in low]


def _complete_reply_check(response: str) -> CheckResult:
    text = response.strip()
    incomplete = re.search(
        r"(let me check|one sec|i'?ll continue|continue below|to be continued|\.\.\.)\s*$",
        text,
        re.IGNORECASE,
    )
    if incomplete:
        return CheckResult("complete_reply", WARN, "Response ends like an unfinished thought.")
    if not text:
        return CheckResult("complete_reply", FAIL, "Response is empty.")
    return CheckResult("complete_reply", PASS, "Response appears complete.")


def _decision_transparency_check(response: str) -> CheckResult:
    low = response.lower()
    signals = ["reasoning", "trade-off", "tradeoff", "risk", "confidence", "recommendation", "decider"]
    hits = [signal for signal in signals if signal in low]
    if len(hits) >= 2:
        return CheckResult("decision_transparency", PASS, f"Reasoning signals present: {', '.join(hits[:4])}.")
    return CheckResult("decision_transparency", WARN, "Complex recommendation lacks a visible reasoning framework.")


def _tool_honesty_check(response: str) -> CheckResult:
    low = response.lower()
    claims_live = any(
        phrase in low
        for phrase in [
            "i searched",
            "live result",
            "latest from",
            "according to the web",
            "current web",
            "real-time",
        ]
    )
    admits_limits = any(
        phrase in low
        for phrase in [
            "i do not have",
            "i don't have",
            "cannot access",
            "need to verify",
            "if web access is available",
            "based on available context",
        ]
    )
    if claims_live and not admits_limits:
        return CheckResult("tool_honesty", WARN, "Response implies live capability without visible evidence or caveat.")
    return CheckResult("tool_honesty", PASS, "No unsupported live-tool claim detected.")


def _current_truth_override_check(response: str, check: dict[str, Any]) -> CheckResult:
    current_truth = [str(x) for x in check.get("current_truth", [])]
    stale_terms = [str(x) for x in check.get("stale_terms", [])]
    missing_truth = [term for term in current_truth if term.lower() not in response.lower()]
    stale_hits = _contains_any(response, stale_terms)
    if stale_hits:
        return CheckResult("current_truth_override", FAIL, f"Stale term(s) surfaced: {', '.join(stale_hits)}.")
    if missing_truth:
        return CheckResult("current_truth_override", WARN, f"Current truth missing: {', '.join(missing_truth)}.")
    return CheckResult("current_truth_override", PASS, "Current truth is present and stale terms are absent.")


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    response = _norm(case.get("response", ""))
    results: list[CheckResult] = []

    for check in case.get("checks", []):
        ctype = str(check.get("type", "")).strip()
        if ctype == "must_include":
            terms = [str(x) for x in check.get("terms", [])]
            hits = _contains_any(response, terms)
            missing = [term for term in terms if term not in hits]
            status = PASS if not missing else FAIL
            detail = "All required terms found." if not missing else f"Missing: {', '.join(missing)}."
            results.append(CheckResult("must_include", status, detail))
        elif ctype == "must_not_include":
            terms = [str(x) for x in check.get("terms", [])]
            hits = _contains_any(response, terms)
            status = PASS if not hits else FAIL
            detail = "Forbidden terms absent." if not hits else f"Forbidden terms found: {', '.join(hits)}."
            results.append(CheckResult("must_not_include", status, detail))
        elif ctype == "max_chars":
            limit = int(check.get("limit", 1200))
            status = PASS if len(response) <= limit else WARN
            results.append(CheckResult("max_chars", status, f"{len(response)} chars; limit {limit}."))
        elif ctype == "complete_reply":
            results.append(_complete_reply_check(response))
        elif ctype == "decision_transparency":
            results.append(_decision_transparency_check(response))
        elif ctype == "tool_honesty":
            results.append(_tool_honesty_check(response))
        elif ctype == "current_truth_override":
            results.append(_current_truth_override_check(response, check))
        else:
            results.append(CheckResult(ctype or "unknown_check", WARN, "Unknown check type."))

    status = _rollup_status(results)
    return {
        "name": case.get("name", "unnamed case"),
        "input": case.get("input", ""),
        "status": status,
        "checks": [asdict(result) for result in results],
    }


def _rollup_status(results: list[CheckResult]) -> str:
    statuses = [r.status for r in results]
    if FAIL in statuses:
        return FAIL
    if WARN in statuses:
        return WARN
    return PASS


def _load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.get("cases", []))
    if isinstance(data, list):
        return data
    raise ValueError("Cases file must be a JSON list or an object with a 'cases' list.")


def _load_transcript(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def evaluate_transcript(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "status": WARN,
            "checks": [asdict(CheckResult("transcript_present", WARN, "No transcript provided."))],
            "metrics": {},
        }

    user_rows = [r for r in rows if str(r.get("role", "")).lower() == "user"]
    assistant_rows = [r for r in rows if str(r.get("role", "")).lower() == "assistant"]
    assistant_lengths = [len(_norm(r.get("content", ""))) for r in assistant_rows]
    avg_len = round(statistics.mean(assistant_lengths)) if assistant_lengths else 0
    overlong = [x for x in assistant_lengths if x > 2400]
    incomplete = [
        r for r in assistant_rows
        if _complete_reply_check(_norm(r.get("content", ""))).status != PASS
    ]
    stale_countdowns = [
        r for r in rows
        if re.search(
            r"\b\d{1,4}\s+days?\s+(to|until|out|left|remaining)\b.*\bindia\b|\bindia\b.*\b\d{1,4}\s+days?\s+(to|until|out|left|remaining)\b",
            _norm(r.get("content", "")),
            re.IGNORECASE,
        )
    ]
    tool_warnings = [
        r for r in assistant_rows
        if _tool_honesty_check(_norm(r.get("content", ""))).status != PASS
    ]

    checks = [
        CheckResult("role_balance", PASS if user_rows and assistant_rows else WARN, f"{len(user_rows)} user / {len(assistant_rows)} assistant turns."),
        CheckResult("avg_length", PASS if avg_len <= 1600 else WARN, f"Average assistant length {avg_len} chars."),
        CheckResult("incomplete_replies", PASS if not incomplete else WARN, f"{len(incomplete)} incomplete-looking assistant replies."),
        CheckResult("stale_countdown_scan", PASS if not stale_countdowns else WARN, f"{len(stale_countdowns)} countdown-like India references."),
        CheckResult("tool_honesty_scan", PASS if not tool_warnings else WARN, f"{len(tool_warnings)} possible unsupported live-tool claims."),
    ]
    status = _rollup_status(checks)
    return {
        "status": status,
        "checks": [asdict(result) for result in checks],
        "metrics": {
            "entries": len(rows),
            "user_entries": len(user_rows),
            "assistant_entries": len(assistant_rows),
            "avg_assistant_chars": avg_len,
            "overlong_assistant": len(overlong),
            "incomplete_assistant": len(incomplete),
            "stale_countdown_mentions": len(stale_countdowns),
            "tool_honesty_warnings": len(tool_warnings),
        },
    }


def _summary(case_results: list[dict[str, Any]], transcript: dict[str, Any]) -> dict[str, Any]:
    statuses = [case["status"] for case in case_results]
    if transcript:
        statuses.append(transcript.get("status", WARN))
    passed = statuses.count(PASS)
    warned = statuses.count(WARN)
    failed = statuses.count(FAIL)
    total = max(1, len(statuses))
    quality = round(((passed + warned * 0.5) / total) * 100)
    verdict = "ship" if failed == 0 and warned <= 1 else "watch" if failed == 0 else "patch"
    return {
        "pass": passed,
        "warn": warned,
        "fail": failed,
        "total": len(statuses),
        "quality_score": quality,
        "verdict": verdict,
    }


def run_arena(cases_path: Path, transcript_path: Path | None = None) -> dict[str, Any]:
    cases = _load_cases(cases_path)
    case_results = [evaluate_case(case) for case in cases]
    transcript_rows = _load_transcript(transcript_path)
    transcript = evaluate_transcript(transcript_rows) if transcript_path else {}
    return {
        "run_id": str(uuid.uuid4()),
        "generated_at": _now_iso(),
        "cases_path": str(cases_path),
        "transcript_path": str(transcript_path) if transcript_path else "",
        "summary": _summary(case_results, transcript),
        "cases": case_results,
        "transcript": transcript,
    }


def _checks_from_markdown_report(report: str) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for raw in str(report or "").splitlines():
        line = _norm(raw)
        if not line or not any(word in line for word in ["PASS", "WARN", "FAIL"]):
            continue
        status = PASS if "PASS" in line else WARN if "WARN" in line else FAIL
        match = re.search(r"\*\*(.*?)\*\*", line)
        name = match.group(1) if match else status
        detail = line
        if " - " in detail:
            detail = detail.split(" - ", 1)[1]
        elif "—" in detail:
            detail = detail.split("—", 1)[1].strip()
        checks.append({"name": name, "status": status, "detail": detail})
    return checks


def _case_from_checks(name: str, checks: list[dict[str, Any]], input_text: str = "") -> dict[str, Any]:
    converted = [
        CheckResult(
            name=str(check.get("name", "check")),
            status=str(check.get("status", WARN)).lower(),
            detail=str(check.get("detail", "")),
        )
        for check in checks
    ]
    return {
        "name": name,
        "input": input_text,
        "status": _rollup_status(converted),
        "checks": [asdict(result) for result in converted],
    }


def report_from_maxima_payload(payload: dict[str, Any], source_url: str = "") -> dict[str, Any]:
    """Normalize Maxima Eval Lab JSON into an Arena report."""
    core_checks = _checks_from_markdown_report(str(payload.get("eval_lab", "")))
    canary_checks = _checks_from_markdown_report(str(payload.get("canary", "")))
    transcript = payload.get("transcript", {}) or {}
    transcript_checks = transcript.get("checks", []) or []
    cases = [
        _case_from_checks("Maxima core eval suite", core_checks, "Imported from Maxima Eval Lab"),
        _case_from_checks("Maxima canary stability", canary_checks, "Imported from Maxima Canary"),
    ]
    transcript_report = {
        "status": _case_from_checks("Maxima live transcript", transcript_checks).get("status", WARN),
        "checks": [
            asdict(CheckResult(
                name=str(check.get("name", "check")),
                status=str(check.get("status", WARN)).lower(),
                detail=str(check.get("detail", "")),
            ))
            for check in transcript_checks
        ],
        "metrics": transcript.get("metrics", {}),
    }
    report = {
        "run_id": str(uuid.uuid4()),
        "generated_at": _now_iso(),
        "cases_path": "maxima-live-import",
        "transcript_path": "maxima-live-import",
        "summary": _summary(cases, transcript_report),
        "cases": cases,
        "transcript": transcript_report,
        "source": {
            "type": "maxima_eval_lab_json",
            "url": source_url.split("?", 1)[0] if source_url else "",
            "snapshot": payload.get("snapshot", {}),
            "history": payload.get("history", {}),
        },
    }
    snapshot = payload.get("snapshot", {}) or {}
    if snapshot.get("quality") is not None:
        report["summary"]["source_quality_score"] = snapshot.get("quality")
    return report


def _build_maxima_url(base_url: str, token: str) -> str:
    base = str(base_url or "").rstrip("/")
    if not base:
        raise ValueError("Missing Maxima base URL.")
    if base.endswith(".json") or "/eval-lab.json" in base:
        separator = "&" if "?" in base else "?"
        return base if "token=" in base else base + separator + urlencode({"token": token})
    return f"{base}/eval-lab.json?{urlencode({'token': token})}"


def import_maxima_report(
    *,
    url: str = "",
    base_url: str = "https://maxima-v3-production.up.railway.app",
    token: str = "",
    token_env: str = "SYNC_SECRET",
    timeout: int = 60,
) -> dict[str, Any]:
    """Fetch Maxima's private Eval Lab JSON and normalize it as an Arena report."""
    secret = token or os.getenv(token_env, "")
    if not secret and not url:
        raise ValueError(f"Missing token. Set {token_env} or pass --token/--url.")
    target = url or _build_maxima_url(base_url, secret)
    with urlopen(target, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return report_from_maxima_payload(payload, source_url=target)


def trend_entry_from_report(report: dict[str, Any]) -> dict[str, Any]:
    """Extract a compact, public-safe daily trend row from an Arena report."""
    summary = report.get("summary", {}) or {}
    source = report.get("source", {}) or {}
    snapshot = source.get("snapshot", {}) or {}
    return {
        "run_id": str(report.get("run_id", "")),
        "generated_at": str(report.get("generated_at", "")),
        "quality_score": summary.get("quality_score"),
        "source_quality_score": summary.get("source_quality_score"),
        "verdict": summary.get("verdict", "unknown"),
        "pass": summary.get("pass", 0),
        "warn": summary.get("warn", 0),
        "fail": summary.get("fail", 0),
        "source_type": source.get("type", ""),
        "source_url": source.get("url", ""),
        "source_status": snapshot.get("status", ""),
        "source_quality": snapshot.get("quality"),
    }


def _trend_sort_key(row: dict[str, Any]) -> str:
    return str(row.get("generated_at") or row.get("run_id") or "")


def load_trend(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"generated_at": _now_iso(), "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"generated_at": _now_iso(), "entries": data}
    if isinstance(data, dict):
        data.setdefault("entries", [])
        return data
    raise ValueError("Trend file must be a JSON object or list.")


def append_trend(report: dict[str, Any], trend_path: Path) -> dict[str, Any]:
    """Append a report summary to a trend file, deduping by run_id."""
    trend = load_trend(trend_path)
    entry = trend_entry_from_report(report)
    entries = [row for row in trend.get("entries", []) if row.get("run_id") != entry.get("run_id")]
    entries.append(entry)
    entries.sort(key=_trend_sort_key)
    trend["generated_at"] = _now_iso()
    trend["entries"] = entries
    trend_path.parent.mkdir(parents=True, exist_ok=True)
    trend_path.write_text(json.dumps(trend, indent=2, ensure_ascii=False), encoding="utf-8")
    return trend


def _status_class(status: str) -> str:
    return status if status in {PASS, WARN, FAIL} else WARN


def generate_dashboard(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    source_quality = summary.get("source_quality_score")
    quality_label = "Arena Quality" if source_quality is not None else "Quality"
    second_metric_value = source_quality if source_quality is not None else summary.get("pass", 0)
    second_metric_label = "Source Quality" if source_quality is not None else "Pass"
    case_cards = []
    for case in report.get("cases", []):
        checks = "".join(
            f"<li class='{_status_class(c.get('status', 'warn'))}'><strong>{html.escape(c.get('name', 'check'))}</strong>: {html.escape(c.get('detail', ''))}</li>"
            for c in case.get("checks", [])
        )
        case_cards.append(
            f"<section class='card {_status_class(case.get('status', 'warn'))}'>"
            f"<h3>{html.escape(case.get('name', 'Unnamed case'))}</h3>"
            f"<p>{html.escape(case.get('input', ''))}</p>"
            f"<ul>{checks}</ul>"
            "</section>"
        )

    transcript = report.get("transcript", {}) or {}
    transcript_checks = "".join(
        f"<li class='{_status_class(c.get('status', 'warn'))}'><strong>{html.escape(c.get('name', 'check'))}</strong>: {html.escape(c.get('detail', ''))}</li>"
        for c in transcript.get("checks", [])
    ) or "<li>No transcript checks.</li>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Reliability Arena</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#071018;color:#f8fafc;font-family:Inter,Segoe UI,Arial,sans-serif}}main{{max-width:1120px;margin:0 auto;padding:38px 20px 60px}}.hero{{border-bottom:1px solid rgba(148,163,184,.24);padding-bottom:24px;margin-bottom:20px}}.eyebrow{{color:#22d3ee;text-transform:uppercase;letter-spacing:.16em;font-size:12px;font-weight:800}}h1{{font-size:clamp(38px,8vw,82px);line-height:.92;margin:10px 0 14px}}.lead{{color:#cbd5e1;font-size:18px;max-width:760px;line-height:1.6}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}}.metric{{background:#0f172a;border:1px solid rgba(148,163,184,.18);border-radius:12px;padding:16px}}.metric strong{{display:block;font-size:34px}}.metric span{{display:block;color:#94a3b8;text-transform:uppercase;letter-spacing:.1em;font-size:11px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.card{{background:#0b1220;border:1px solid rgba(148,163,184,.18);border-left-width:4px;border-radius:12px;padding:16px}}.card.pass{{border-left-color:#34d399}}.card.warn{{border-left-color:#fbbf24}}.card.fail{{border-left-color:#fb7185}}.card h3{{margin:0 0 8px}}.card p{{color:#94a3b8;margin:0 0 12px;line-height:1.5}}ul{{margin:0;padding-left:20px;color:#cbd5e1;line-height:1.7}}li.pass{{color:#86efac}}li.warn{{color:#fde68a}}li.fail{{color:#fda4af}}footer{{color:#64748b;text-align:center;margin-top:28px;font-size:12px}}@media(max-width:760px){{.metrics,.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<main>
<section class="hero">
<div class="eyebrow">Agent Reliability Arena</div>
<h1>Trust agents by testing them.</h1>
<p class="lead">A deterministic lab for memory drift, tool honesty, current-truth override, answer completeness, and transcript health.</p>
</section>
<section class="metrics">
<div class="metric"><strong>{summary.get('quality_score', 0)}</strong><span>{quality_label}</span></div>
<div class="metric"><strong>{second_metric_value}</strong><span>{second_metric_label}</span></div>
<div class="metric"><strong>{summary.get('warn', 0)}</strong><span>Warn</span></div>
<div class="metric"><strong>{summary.get('fail', 0)}</strong><span>Fail</span></div>
</section>
<section class="card {_status_class(transcript.get('status', 'warn'))}">
<h3>Transcript Health</h3>
<p>Conversation-level checks for long replies, incomplete thoughts, stale countdowns, and tool honesty.</p>
<ul>{transcript_checks}</ul>
</section>
<section class="grid" style="margin-top:14px">
{''.join(case_cards)}
</section>
<footer>Run {html.escape(report.get('run_id', ''))} generated {html.escape(report.get('generated_at', ''))}. Verdict: {html.escape(summary.get('verdict', 'unknown'))}.</footer>
</main>
</body>
</html>"""


def generate_trend_dashboard(trend: dict[str, Any]) -> str:
    entries = list(trend.get("entries", []) or [])
    latest = entries[-1] if entries else {}
    quality_values = [
        int(row.get("quality_score") or 0)
        for row in entries
        if row.get("quality_score") is not None
    ]
    avg_quality = round(statistics.mean(quality_values)) if quality_values else 0
    high_quality = max(quality_values) if quality_values else 0
    latest_quality = latest.get("quality_score", 0)
    rows = []
    points = []
    for idx, row in enumerate(entries):
        quality = int(row.get("quality_score") or 0)
        source_quality = row.get("source_quality_score")
        verdict = html.escape(str(row.get("verdict", "unknown")))
        status = "pass" if quality >= 90 else "warn" if quality >= 70 else "fail"
        generated = html.escape(str(row.get("generated_at", "")))
        rows.append(
            "<tr>"
            f"<td>{generated}</td>"
            f"<td><span class='pill {status}'>{quality}</span></td>"
            f"<td>{html.escape(str(source_quality if source_quality is not None else ''))}</td>"
            f"<td>{verdict}</td>"
            f"<td>{int(row.get('pass', 0))}</td>"
            f"<td>{int(row.get('warn', 0))}</td>"
            f"<td>{int(row.get('fail', 0))}</td>"
            "</tr>"
        )
        x = 6 + idx * (88 / max(1, len(entries) - 1))
        y = 94 - quality * 0.82
        points.append(f"{x:.2f},{y:.2f}")
    polyline = " ".join(points)
    empty_note = "" if entries else "<p class='lead'>No trend entries yet. Run import-maxima with --trend-out to start the daily record.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Maxima Reliability Trend</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#071018;color:#f8fafc;font-family:Inter,Segoe UI,Arial,sans-serif}}main{{max-width:1100px;margin:0 auto;padding:38px 20px 60px}}.eyebrow{{color:#22d3ee;text-transform:uppercase;letter-spacing:.16em;font-size:12px;font-weight:800}}h1{{font-size:clamp(34px,7vw,72px);line-height:.96;margin:10px 0 14px}}.lead{{color:#cbd5e1;font-size:18px;max-width:760px;line-height:1.6}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}}.metric{{background:#0f172a;border:1px solid rgba(148,163,184,.18);border-radius:12px;padding:16px}}.metric strong{{display:block;font-size:34px}}.metric span{{display:block;color:#94a3b8;text-transform:uppercase;letter-spacing:.1em;font-size:11px}}.panel{{background:#0b1220;border:1px solid rgba(148,163,184,.18);border-radius:12px;padding:18px;margin-top:14px}}svg{{width:100%;height:260px;background:#08111d;border-radius:10px;border:1px solid rgba(148,163,184,.18)}}polyline{{fill:none;stroke:#34d399;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}}.gridline{{stroke:rgba(148,163,184,.22);stroke-width:.6}}table{{width:100%;border-collapse:collapse;margin-top:10px;font-size:14px}}th,td{{border-bottom:1px solid rgba(148,163,184,.18);padding:10px;text-align:left}}th{{color:#94a3b8;text-transform:uppercase;letter-spacing:.1em;font-size:11px}}.pill{{display:inline-block;min-width:48px;text-align:center;border-radius:999px;padding:4px 8px;font-weight:800}}.pill.pass{{background:#064e3b;color:#86efac}}.pill.warn{{background:#713f12;color:#fde68a}}.pill.fail{{background:#7f1d1d;color:#fca5a5}}footer{{color:#64748b;text-align:center;margin-top:28px;font-size:12px}}@media(max-width:760px){{.metrics{{grid-template-columns:1fr 1fr}}table{{font-size:12px}}}}
</style>
</head>
<body>
<main>
<section>
<div class="eyebrow">Project Maxima</div>
<h1>Daily Reliability Trend</h1>
<p class="lead">A compact history of Maxima's Arena score, source quality, warnings, and failures. This makes drift visible before it turns into a user-visible bug.</p>
</section>
<section class="metrics">
<div class="metric"><strong>{latest_quality}</strong><span>Latest</span></div>
<div class="metric"><strong>{avg_quality}</strong><span>Average</span></div>
<div class="metric"><strong>{high_quality}</strong><span>Best</span></div>
<div class="metric"><strong>{len(entries)}</strong><span>Runs</span></div>
</section>
<section class="panel">
<h2>Quality Over Time</h2>
{empty_note}
<svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Maxima reliability quality trend">
<line class="gridline" x1="0" y1="12" x2="100" y2="12"></line>
<line class="gridline" x1="0" y1="53" x2="100" y2="53"></line>
<line class="gridline" x1="0" y1="94" x2="100" y2="94"></line>
<polyline points="{html.escape(polyline)}"></polyline>
</svg>
</section>
<section class="panel">
<h2>Runs</h2>
<table>
<thead><tr><th>Generated</th><th>Arena</th><th>Source</th><th>Verdict</th><th>Pass</th><th>Warn</th><th>Fail</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</section>
<footer>Trend generated {html.escape(str(trend.get('generated_at', '')))}. Public-safe rows only; no sync tokens are stored.</footer>
</main>
</body>
</html>"""
