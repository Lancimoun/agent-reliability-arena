import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "reliability-gate.yml"
ENGINE_SHA = "aa1f1a220171559afa3e67363891afce9284faeb"


class ReusableWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_is_call_only_and_least_privilege(self):
        self.assertRegex(self.workflow, r"(?m)^on:\s*\n\s+workflow_call:")
        self.assertNotIn("\n  push:", self.workflow)
        self.assertNotIn("\n  pull_request:", self.workflow)
        self.assertRegex(
            self.workflow,
            r"(?m)^permissions:\s*\n\s+contents: read$",
        )
        self.assertNotIn("secrets:", self.workflow)
        self.assertNotIn("${{ secrets.", self.workflow)

    def test_workflow_exposes_bounded_reliability_inputs(self):
        for input_name in (
            "cases_path",
            "transcript_path",
            "report_path",
            "python_version",
            "min_quality",
            "max_fail",
            "max_warn",
        ):
            with self.subTest(input_name=input_name):
                self.assertRegex(
                    self.workflow,
                    rf"(?m)^\s{{6}}{input_name}:$",
                )

        self.assertIn('default: "3.12"', self.workflow)
        self.assertIn("default: 90", self.workflow)
        self.assertGreaterEqual(self.workflow.count("default: 0"), 2)

    def test_workflow_pins_engine_and_runs_report_gate(self):
        self.assertIn("repository: Lancimoun/agent-reliability-arena", self.workflow)
        self.assertIn(f"ref: {ENGINE_SHA}", self.workflow)
        self.assertIn("path: .arena-engine", self.workflow)
        self.assertIn("python -m pip install ./.arena-engine", self.workflow)
        self.assertIn("python -m agent_reliability_arena run", self.workflow)
        self.assertIn("python -m agent_reliability_arena gate", self.workflow)
        self.assertIn("actions/upload-artifact@v4", self.workflow)
        self.assertNotRegex(
            self.workflow,
            r"Lancimoun/agent-reliability-arena(?:\.git)?@(?:main|master)",
        )


if __name__ == "__main__":
    unittest.main()
