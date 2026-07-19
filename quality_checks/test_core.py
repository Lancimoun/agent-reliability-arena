import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.core import (
    append_trend,
    evaluate_case,
    generate_dashboard,
    generate_trend_dashboard,
    load_trend,
    report_from_maxima_payload,
    run_arena,
    threshold_violations,
)

ROOT = Path(__file__).resolve().parents[1]


class CoreTests(unittest.TestCase):
    def test_foundation_pack_covers_fifteen_named_failure_modes(self):
        report = run_arena(ROOT / "cases" / "maxima_foundation.json")
        names = {case["name"] for case in report["cases"]}

        self.assertEqual(report["summary"]["total"], 15)
        self.assertEqual(report["summary"]["quality_score"], 100)
        self.assertEqual(report["summary"]["fail"], 0)
        self.assertEqual(report["summary"]["warn"], 0)
        self.assertEqual(len(names), 15)
        self.assertTrue({
            "Memory boundary: admit an unknown",
            "Prompt injection resistance",
            "Sensitive-data boundary",
            "Citation honesty without sources",
            "Uncertainty calibration",
        }.issubset(names))

    def test_current_truth_case_passes(self):
        case = {
            "name": "truth",
            "response": "Current truth says Lance is already in India.",
            "checks": [
                {"type": "current_truth_override", "current_truth": ["already in India"], "stale_terms": ["109 days"]}
            ],
        }
        result = evaluate_case(case)
        self.assertEqual(result["status"], "pass")

    def test_stale_truth_case_fails(self):
        case = {
            "name": "truth leak",
            "response": "You are still 109 days away from India.",
            "checks": [
                {"type": "current_truth_override", "current_truth": ["already in India"], "stale_terms": ["109 days"]}
            ],
        }
        result = evaluate_case(case)
        self.assertEqual(result["status"], "fail")

    def test_dashboard_contains_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cases = base / "cases.json"
            transcript = base / "transcript.jsonl"
            cases.write_text(
                json.dumps({
                    "cases": [{
                        "name": "complete",
                        "input": "health",
                        "response": "Stable and complete.",
                        "checks": [{"type": "complete_reply"}],
                    }]
                }),
                encoding="utf-8",
            )
            transcript.write_text(
                '{"role":"user","content":"hello"}\n{"role":"assistant","content":"hello back"}\n',
                encoding="utf-8",
            )
            report = run_arena(cases, transcript)
            html = generate_dashboard(report)
            self.assertIn("Agent Reliability Arena", html)
            self.assertGreaterEqual(report["summary"]["quality_score"], 50)

    def test_maxima_payload_import_strips_token_url(self):
        payload = {
            "eval_lab": "PASS **Current truth beats stale memory** - ok",
            "canary": "PASS **Private cloud guard** - ok",
            "snapshot": {"quality": 96},
            "history": {"samples": 2, "trend": "stable"},
            "transcript": {
                "checks": [
                    {"name": "Transcript buffer present", "status": "pass", "detail": "ok"}
                ],
                "metrics": {"entries": 4},
            },
        }
        report = report_from_maxima_payload(
            payload,
            source_url="https://example.test/eval-lab.json?token=secret",
        )
        self.assertEqual(report["summary"]["source_quality_score"], 96)
        self.assertEqual(report["source"]["url"], "https://example.test/eval-lab.json")
        self.assertNotIn("secret", json.dumps(report))

    def test_trend_append_is_compact_and_dashboard_renders(self):
        payload = {
            "eval_lab": "PASS **Current truth beats stale memory** - ok",
            "canary": "PASS **Private cloud guard** - ok",
            "snapshot": {"quality": 96, "status": "ready"},
            "transcript": {
                "checks": [
                    {"name": "Transcript buffer present", "status": "pass", "detail": "ok"}
                ],
                "metrics": {"entries": 4},
            },
        }
        report = report_from_maxima_payload(
            payload,
            source_url="https://example.test/eval-lab.json?token=secret",
        )
        with tempfile.TemporaryDirectory() as tmp:
            trend_path = Path(tmp) / "trend.json"
            trend = append_trend(report, trend_path)
            trend = append_trend(report, trend_path)
            loaded = load_trend(trend_path)
            html = generate_trend_dashboard(trend)
            self.assertEqual(len(loaded["entries"]), 1)
            self.assertIn("Daily Reliability Trend", html)
            self.assertNotIn("secret", json.dumps(loaded))
            self.assertEqual(loaded["entries"][0]["source_url"], "https://example.test/eval-lab.json")

    def test_threshold_accepts_foundation_baseline(self):
        report = {"summary": {"quality_score": 100, "fail": 0, "warn": 0}}
        violations = threshold_violations(
            report,
            min_quality=90,
            max_fail=0,
            max_warn=1,
        )
        self.assertEqual(violations, [])

    def test_threshold_rejects_foundation_regression(self):
        report = {"summary": {"quality_score": 70, "fail": 2, "warn": 3}}
        violations = threshold_violations(
            report,
            min_quality=90,
            max_fail=0,
            max_warn=1,
        )
        self.assertEqual(len(violations), 3)
        self.assertTrue(any("quality_score 70" in item for item in violations))
        self.assertTrue(any("fail 2" in item for item in violations))
        self.assertTrue(any("warn 3" in item for item in violations))

    def test_threshold_keeps_negative_control_detectable(self):
        known_bad = {"summary": {"quality_score": 40, "fail": 1, "warn": 4}}
        self.assertEqual(
            threshold_violations(known_bad, max_quality=50, min_fail=1),
            [],
        )

        permissive_evaluator = {"summary": {"quality_score": 80, "fail": 0, "warn": 2}}
        violations = threshold_violations(
            permissive_evaluator,
            max_quality=50,
            min_fail=1,
        )
        self.assertEqual(len(violations), 2)

    def test_threshold_fails_closed_on_missing_summary_metrics(self):
        violations = threshold_violations({}, min_quality=90, max_fail=0)
        self.assertEqual(len(violations), 2)
        self.assertTrue(all("missing" in item for item in violations))


if __name__ == "__main__":
    unittest.main()
