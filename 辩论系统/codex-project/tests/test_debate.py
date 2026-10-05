"""Synthetic software tests, not real Codex, model-quality, or security tests."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("debate", PROJECT / "scripts/debate.py")
debate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(debate)


class DebateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        shutil.copytree(PROJECT, self.root, ignore=shutil.ignore_patterns("debates", ".smoke", "__pycache__", ".git"))
        self.set_topic("测试：需求不确定时应先做原型吗？")

    def set_topic(self, topic):
        (self.root / "PROMPT.md").write_text("【辩题输入】" + topic + "\n固定指令\n", encoding="utf-8")

    def save(self, run, data):
        (run / "run.json").write_text(debate.encoded(data), encoding="utf-8")

    def fixture(self, smoke=True, n=2):
        run = debate.prepare(self.root, smoke=smoke)
        d = debate.read_json(run / "run.json")
        d.update(status="adjudicated", rounds_completed=n, evidence_version=1,
                 stop_reason="smoke_completed" if smoke else "converged")
        d["agents"] = [{"role": r, "thread_id": "SYNTHETIC-" + r,
                        "tool_event_ref": "SYNTHETIC-EVENT-" + r} for r in sorted(debate.ROLES)]
        d["evidence"] = [{"id": "E1", "locator": "synthetic fixture", "acquisition": "user_supplied"}]
        d["claims"] = [{"id": "C1", "text": "单元测试的合成前提，不是外部事实。",
                        "kind": "empirical", "decisive": True, "evidence_ids": ["E1"],
                        "depends_on": [], "assessment": "supported", "review_version": 1,
                        "review_note": "Synthetic fixture, not an actual fact check."}]
        for i in range(1, n + 1):
            art = {}
            for role in ("affirmative", "negative", "moderator"):
                rel = f"rounds/{i:03d}-{role}.md"
                (run / rel).write_text("SYNTHETIC TEST ONLY\n", encoding="utf-8")
                art[role] = rel
            d["rounds"].append({"number": i, "phase": "smoke" if smoke else "deep_clash",
                                "input_evidence_version": 1, "artifacts": art,
                                "progress_note": "Synthetic test only", "changed_claim_ids": [],
                                "changed_evidence_ids": [], "decision_changed": False,
                                "conditions_changed": False})
        for rel in ("checks/final_check.md", "checks/verdict.md", "final.md", "full_transcript.md"):
            (run / rel).write_text("SYNTHETIC TEST ONLY\n", encoding="utf-8")
        d["final_gate"] = {"evidence_version": 1, "checker_thread_id": "SYNTHETIC-checker",
                           "report_path": "checks/final_check.md"}
        d["verdict"] = {"kind": "recommendation", "evidence_version": 1,
                        "judge_thread_id": "SYNTHETIC-judge", "report_path": "checks/verdict.md",
                        "summary": "Synthetic test only", "relied_claim_ids": ["C1"],
                        "blocking_claim_ids": [], "conditions": []}
        d["coverage"] = [{"dimension": "synthetic", "status": "covered"}]
        d["convergence"] = {"coverage_complete": True, "key_facts_checked": True,
                            "strongest_objections_addressed": True, "reverse_case_done": True,
                            "no_high_value_next_step": True, "stable_rounds": 4}
        self.save(run, d)
        return run, d

    def rejected(self, change):
        run, d = self.fixture()
        change(d)
        self.save(run, d)
        self.assertTrue(debate.validate_run(run))

    def test_01_defaults(self):
        c = debate.load_config(self.root)
        self.assertEqual((c["planned_rounds"], c["max_rounds"]), (30, 60))

    def test_02_plan_30(self):
        self.assertEqual([r["end"] for r in debate.phase_plan(30, [10, 20, 30, 30, 10])], [3, 9, 18, 27, 30])

    def test_03_plan_50(self):
        self.assertEqual([r["end"] for r in debate.phase_plan(50, [10, 20, 30, 30, 10])], [5, 15, 30, 45, 50])

    def test_04_plan_invariants(self):
        for total in range(5, 101):
            plan = debate.phase_plan(total, [10, 20, 30, 30, 10])
            self.assertEqual(plan[-1]["end"], total)
            self.assertTrue(all(p["start"] <= p["end"] for p in plan))
            self.assertEqual([p["start"] for p in plan[1:]], [p["end"] + 1 for p in plan[:-1]])

    def test_05_invalid_plan(self):
        for total, weights in [(4, [1]*5), (30, [1, 2]), (30, [True, 1, 1, 1, 1]), (30, [0, 1, 1, 1, 1])]:
            with self.assertRaises(ValueError):
                debate.phase_plan(total, weights)

    def test_06_placeholder(self):
        with self.assertRaises(ValueError):
            debate.parse_topic("【辩题输入】在此填写本次辩题\n")

    def test_07_first_line(self):
        with self.assertRaises(ValueError):
            debate.parse_topic("# Header\n【辩题输入】内容")

    def test_08_unicode_and_whitespace(self):
        self.assertEqual(debate.topic_identity("e\u0301  topic"), debate.topic_identity("é topic"))

    def test_09_safe_topic_path(self):
        _, key = debate.topic_identity('../../CON:*?$(touch marker)')
        self.assertNotIn("/", key)
        self.assertNotIn(":", key)
        self.assertTrue(key.startswith("t-"))

    def test_10_same_topic_new_run(self):
        a = debate.prepare(self.root)
        before = (a / "manifest.json").read_bytes()
        b = debate.prepare(self.root)
        self.assertEqual(a.parent, b.parent)
        self.assertNotEqual(a, b)
        self.assertEqual(before, (a / "manifest.json").read_bytes())

    def test_11_different_topic(self):
        a = debate.prepare(self.root)
        self.set_topic("另一个测试辩题")
        b = debate.prepare(self.root)
        self.assertNotEqual(a.parent.parent, b.parent.parent)

    def test_12_input_snapshot(self):
        a = debate.prepare(self.root)
        old = (a / "inputs/PROMPT.md").read_bytes()
        self.set_topic("新题目")
        self.assertEqual(old, (a / "inputs/PROMPT.md").read_bytes())

    def test_13_traversal_rejected(self):
        with self.assertRaises(ValueError):
            debate.prepare(self.root, "../PROMPT.md")

    def test_14_symlink_input_rejected(self):
        target = Path(self.temp.name) / "outside.md"
        target.write_text("【辩题输入】外部题目", encoding="utf-8")
        link = self.root / "link.md"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("Host does not permit symlink creation")
        with self.assertRaises(ValueError):
            debate.prepare(self.root, "link.md")

    def test_15_smoke_separate(self):
        run = debate.prepare(self.root, smoke=True)
        self.assertEqual(run.parent.name, ".smoke")
        self.assertEqual(debate.read_json(run / "manifest.json")["config"]["max_rounds"], 2)
        self.assertEqual(debate.load_config(self.root)["max_rounds"], 60)

    def test_16_prepared_not_final(self):
        self.assertTrue(debate.validate_run(debate.prepare(self.root)))

    def test_17_valid_synthetic_final(self):
        run, _ = self.fixture()
        self.assertEqual(debate.validate_run(run), [])

    def test_18_missing_role(self):
        self.rejected(lambda d: d["agents"].pop())

    def test_19_shared_role_thread(self):
        self.rejected(lambda d: d["agents"][1].update(thread_id=d["agents"][0]["thread_id"]))

    def test_20_stale_verdict(self):
        self.rejected(lambda d: d["verdict"].update(evidence_version=0))

    def test_21_missing_artifact(self):
        run, _ = self.fixture()
        (run / "rounds/001-negative.md").unlink()
        self.assertTrue(debate.validate_run(run))

    def test_22_escaping_artifact(self):
        self.rejected(lambda d: d["rounds"][0]["artifacts"].update(negative="../other-run/final.md"))

    def test_23_stale_claim(self):
        self.rejected(lambda d: d["claims"][0].update(review_version=0))

    def test_24_unknown_reference(self):
        self.rejected(lambda d: d["claims"][0].update(evidence_ids=["E999"]))

    def test_25_dependency_cycle(self):
        self.rejected(lambda d: d["claims"][0].update(depends_on=["C1"]))

    def test_26_contradicted_premise(self):
        self.rejected(lambda d: d["claims"][0].update(assessment="contradicted"))

    def test_27_unconditional_blocker(self):
        self.rejected(lambda d: d["verdict"].update(blocking_claim_ids=["C1"]))

    def test_28_explicit_conditional(self):
        run, d = self.fixture()
        d["claims"][0]["assessment"] = "unverified"
        d["verdict"].update(kind="conditional", blocking_claim_ids=["C1"], conditions=["仅在合成前提成立时"])
        self.save(run, d)
        self.assertEqual(debate.validate_run(run), [])

    def test_29_unobserved_support(self):
        self.rejected(lambda d: d["evidence"][0].update(acquisition="unobserved"))

    def test_30_modified_frozen_system(self):
        run, _ = self.fixture()
        (run / "inputs/system/PROTOCOL.md").write_text("tampered", encoding="utf-8")
        self.assertTrue(debate.validate_run(run))

    def test_31_early_convergence(self):
        run, _ = self.fixture(smoke=False, n=2)
        self.assertTrue(debate.validate_run(run))

    def test_32_normal_convergence(self):
        run, _ = self.fixture(smoke=False, n=12)
        self.assertEqual(debate.validate_run(run), [])

    def test_33_exception_without_evidence(self):
        self.rejected(lambda d: d.update(stop_reason="exception_proven", exception_note="synthetic", exception_evidence_ids=[]))

    def test_34_fresh_launch_not_resume_last(self):
        run = debate.prepare(self.root)
        with patch.object(debate.shutil, "which", return_value="/fake/codex"):
            with patch.object(debate.subprocess, "call", return_value=0) as call:
                self.assertEqual(debate.launch(self.root, run), 0)
        argv = call.call_args.args[0]
        self.assertEqual(argv[:2], ["/fake/codex", "--cd"])
        self.assertNotIn("resume", argv)
        self.assertNotIn("--last", argv)

    def test_35_missing_cli(self):
        run = debate.prepare(self.root)
        with patch.object(debate.shutil, "which", return_value=None):
            with self.assertRaises(ValueError):
                debate.launch(self.root, run)
        self.assertTrue(run.exists())

    def test_36_resume_config_drift(self):
        run = debate.prepare(self.root)
        (self.root / "PROTOCOL.md").write_text("changed", encoding="utf-8")
        with patch.object(debate.shutil, "which", return_value="/fake/codex"):
            with self.assertRaises(ValueError):
                debate.launch(self.root, run, resume=True)


if __name__ == "__main__":
    unittest.main()
