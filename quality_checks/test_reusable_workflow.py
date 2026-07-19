import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "reliability-gate.yml"
ENGINE_SHA = "aa1f1a220171559afa3e67363891afce9284faeb"
CALLER_EXAMPLE = ROOT / "examples" / "github-actions" / "reliability-gate.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
WORKFLOW_RELEASE_SHA = "5f7ccac2d6d6c82ec6f3b8d3724a510692ab3cf8"


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
        self.assertGreaterEqual(self.workflow.count("PYTHONPATH: .arena-engine"), 2)
        self.assertNotIn("pip install", self.workflow)
        self.assertIn("python -m agent_reliability_arena run", self.workflow)
        self.assertIn("python -m agent_reliability_arena gate", self.workflow)
        self.assertIn("actions/upload-artifact@v4", self.workflow)
        self.assertNotRegex(
            self.workflow,
            r"Lancimoun/agent-reliability-arena(?:\.git)?@(?:main|master)",
        )


class ReusableWorkflowExampleTests(unittest.TestCase):
    def test_repository_ci_executes_reusable_workflow_end_to_end(self):
        ci_workflow = CI_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("uses: ./.github/workflows/reliability-gate.yml", ci_workflow)
        self.assertIn("cases_path: cases/maxima_foundation.json", ci_workflow)
        self.assertIn(
            "transcript_path: examples/maxima_transcript_sample.jsonl",
            ci_workflow,
        )
        self.assertIn("min_quality: 90", ci_workflow)
        self.assertIn("max_fail: 0", ci_workflow)
        self.assertIn("max_warn: 1", ci_workflow)

    def test_copyable_caller_is_pinned_documented_and_secret_free(self):
        caller = CALLER_EXAMPLE.read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        reusable_ref = (
            "uses: Lancimoun/agent-reliability-arena/"
            ".github/workflows/reliability-gate.yml@"
            f"{WORKFLOW_RELEASE_SHA}"
        )

        self.assertRegex(caller, r"(?m)^  (?:push|pull_request):")
        self.assertIn("  pull_request:", caller)
        self.assertIn(reusable_ref, caller)
        self.assertRegex(caller, r"(?m)reliability-gate\.yml@[0-9a-f]{40}$")
        self.assertNotIn("secrets: inherit", caller)
        self.assertNotIn("secrets:", caller)
        for setting in (
            "cases_path:",
            "transcript_path:",
            "min_quality:",
            "max_fail:",
            "max_warn:",
        ):
            with self.subTest(setting=setting):
                self.assertIn(setting, caller)

        self.assertIn("examples/github-actions/reliability-gate.yml", readme)
        self.assertIn("reliability/cases.json", readme)
        self.assertIn("reliability/transcript.jsonl", readme)
        self.assertIn(reusable_ref, readme)
        self.assertRegex(
            roadmap,
            r"Sample CI config for agent repos\. .*✅",
        )


if __name__ == "__main__":
    unittest.main()
