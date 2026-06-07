import json
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.core import evaluate_case, generate_dashboard, report_from_maxima_payload, run_arena


class CoreTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
