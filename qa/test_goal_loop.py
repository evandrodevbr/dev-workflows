#!/usr/bin/env python3
"""End-to-end controller tests on disposable repositories, using the real gate/evaluator."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import goal_loop as loop


def git(repo, *args):
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if p.returncode:
        raise AssertionError(p.stderr)
    return p.stdout.strip()


class GoalLoopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = root / "app"
        self.repo.mkdir()
        self.state = root / "state"
        self.bin = root / "bin"
        self.bin.mkdir()
        scanner = self.bin / "gitleaks"
        scanner.write_text("#!/bin/sh\nexit 0\n")
        scanner.chmod(0o755)
        self.env = patch.dict(os.environ, {"DW_STATE_HOME": str(self.state),
                                           "PATH": str(self.bin) + os.pathsep + os.environ["PATH"]})
        self.env.start()
        self.addCleanup(self.env.stop)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "test")
        git(self.repo, "config", "user.email", "test@example.test")
        (self.repo / "calc.py").write_text("VALUE = 0\n")
        (self.repo / "verify.py").write_text("import runpy\nassert runpy.run_path('calc.py')['VALUE'] >= 0\n")
        self.evaluator = root / "evaluator.py"
        self.evaluator.write_text(
            "import json, os, pathlib, runpy\n"
            "value = runpy.run_path('calc.py')['VALUE']\n"
            "folder = pathlib.Path(os.environ['DW_REPORT_DIR'])\n"
            "evidence = folder / 'result.json'\n"
            "evidence.write_text(json.dumps({'measured': value}))\n"
            "print(json.dumps({'schema_version': 1, 'metric': 'quality', 'value': value, "
            "'unit': 'points', 'direction': 'maximize', 'checks': {'regression': 'pass'}, "
            "'evidence': [str(evidence)]}))\n")
        self.config = self.repo / ".dev-workflows.toml"
        self.write_config()
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "baseline")
        self.original = git(self.repo, "rev-parse", "HEAD")

    def write_config(self, target=2, iterations=4, stagnant=2, tier=0, billing="claude_subscription"):
        checksum = hashlib.sha256(self.evaluator.read_bytes()).hexdigest()
        self.config.write_text(
            f"[commands]\ntest = \"python3 verify.py\"\nlint = \"true\"\ntypecheck = \"true\"\n"
            f"[loop]\nenabled = true\nharness = \"claude\"\ntier = {tier}\n"
            f"max_iterations = {iterations}\nmax_minutes = 5\nmax_stagnant = {stagnant}\n"
            "min_improvement = 1\nmax_paid_usd = 0\n"
            f"[loop.goal]\nname = \"quality\"\nunit = \"points\"\ndirection = \"maximize\"\ntarget = {target}\n"
            "[loop.evaluator]\n"
            f"argv = [\"python3\", \"{self.evaluator}\"]\n"
            f"trusted_sha256 = \"{checksum}\"\nrequired_checks = [\"test\", \"lint\"]\n"
            "[models.roles.implementer]\n"
            f"model_key = \"sonnet\"\nbilling_mode = \"{billing}\"\nmanual_unranked_approval = true\n")
        if tier >= 2:
            with self.config.open("a") as config:
                for role in ("planner", "reviewer"):
                    config.write(f"[models.roles.{role}]\nmodel_key = \"opus\"\n"
                                 "billing_mode = \"claude_subscription\"\nmanual_unranked_approval = true\n")
                if tier >= 3:
                    config.write("[models.roles.security-auditor]\nmodel_key = \"opus\"\n"
                                 "billing_mode = \"claude_subscription\"\nmanual_unranked_approval = true\n")

    def runner(self, behavior):
        def invoke(tool, role, prompt, cwd, model_key, timeout=900, env=None):
            if role in ("planner", "reviewer", "security-auditor"):
                return {"returncode": 0, "output": '{"verdict":"pass","findings":[]}', "usage": {}}
            value = int((Path(cwd) / "calc.py").read_text().split("=")[1].strip())
            next_value = behavior(value, cwd)
            (Path(cwd) / "calc.py").write_text(f"VALUE = {next_value}\n")
            return {"returncode": 0, "output": "changed one behavior", "usage": {}}
        return patch.dict(sys.modules, {"harness_runner": types.SimpleNamespace(invoke=invoke)})

    def test_plan_does_not_create_worktree_or_invoke_agent(self):
        before = git(self.repo, "worktree", "list", "--porcelain")
        result = loop.plan(self.config)
        self.assertEqual(result["baseline"], "not_run")
        self.assertEqual(result["gate_preflight"]["test"], "run")
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain"), before)
        self.assertFalse(self.state.exists())

    def test_two_measured_changes_reach_target_without_touching_user_branch(self):
        with self.runner(lambda value, _: value + 1):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual([a["result"] for a in result["attempts"]], ["accepted", "accepted"])
        self.assertEqual(result["best_score"], "2")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), self.original)
        self.assertEqual((self.repo / "calc.py").read_text(), "VALUE = 0\n")
        self.assertEqual((Path(result["best_worktree"]) / "calc.py").read_text(), "VALUE = 2\n")
        self.assertNotIn(".dev-workflows/gate.json", git(Path(result["best_worktree"]), "ls-files"))
        self.assertEqual(result["attempts"][1]["gate"]["checks"]["test"], "pass")

    def test_limit_preserves_best_improvement_without_claiming_target(self):
        self.write_config(target=3, iterations=2)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "target-three")
        with self.runner(lambda value, _: value + 1):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "exhausted", result)
        self.assertEqual(result["best_score"], "2")
        self.assertEqual([a["result"] for a in result["attempts"]], ["accepted", "accepted"])
        self.assertEqual((self.repo / "calc.py").read_text(), "VALUE = 0\n")

    def test_measured_improvement_can_remove_obsolete_code(self):
        (self.repo / "legacy.py").write_text("OLD = True\n")
        self.evaluator.write_text(self.evaluator.read_text().replace(
            "value = runpy.run_path('calc.py')['VALUE']",
            "value = runpy.run_path('calc.py')['VALUE'] + int(not pathlib.Path('legacy.py').exists())"))
        self.write_config(target=1, iterations=1)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "legacy-baseline")
        def invoke(tool, role, prompt, cwd, model_key, timeout=900, env=None):
            (Path(cwd) / "legacy.py").unlink()
            return {"returncode": 0, "output": "removed legacy", "usage": {}}
        with patch.dict(sys.modules, {"harness_runner": types.SimpleNamespace(invoke=invoke)}):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "success", result)
        self.assertFalse((Path(result["best_worktree"]) / "legacy.py").exists())
        self.assertTrue((self.repo / "legacy.py").exists())


    def test_baseline_at_target_exits_without_editing(self):
        self.write_config(target=0)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "zero-target")
        with self.runner(lambda _value, _cwd: self.fail("agente não deveria ser chamado")):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["iteration"], 0)
        self.assertEqual(result["attempts"], [])

    def test_evaluator_cannot_modify_original_checkout(self):
        self.evaluator.write_text(
            self.evaluator.read_text() +
            f"open({str(self.repo / 'calc.py')!r}, 'w').write('VALUE = 999\\n')\n")
        self.write_config(target=1)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "protected-evaluator")
        with self.runner(lambda value, _: value + 1):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "error", result)
        self.assertIn("avaliador", result["error"])
        self.assertEqual((self.repo / "calc.py").read_text(), "VALUE = 0\n")


    def test_gate_failure_rejects_regression_without_replacing_best(self):
        calls = 0
        def changes(value, _):
            nonlocal calls
            calls += 1
            return -1 if calls == 1 else 1
        self.write_config(target=1)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "target-one")
        with self.runner(changes):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual([a["result"] for a in result["attempts"]], ["rejected", "accepted"])
        self.assertIn("quality gate", result["attempts"][0]["reason"])
        self.assertEqual(result["best_score"], "1")
        self.assertEqual((self.repo / "calc.py").read_text(), "VALUE = 0\n")

    def test_incomplete_gate_never_counts_as_success(self):
        self.write_config(target=1, iterations=1)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "one-iteration")
        # No gitleaks in PATH: a security check is unverified, not green.
        with patch.dict(os.environ, {"PATH": os.environ["PATH"].replace(str(self.bin) + os.pathsep, "")}), \
                self.runner(lambda value, _: 1):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "exhausted", result)
        self.assertEqual(result["best_score"], "0")
        self.assertIn("quality gate", result["attempts"][0]["reason"])

    def test_tampered_config_in_candidate_is_rejected(self):
        self.write_config(target=1, iterations=1)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "one-iteration")
        def tamper(value, cwd):
            with (Path(cwd) / ".dev-workflows.toml").open("a") as f:
                f.write("\n# altered by agent\n")
            return 1
        with self.runner(tamper):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "exhausted", result)
        self.assertEqual(result["attempts"][0]["result"], "rejected")
        self.assertIn("protegido", result["attempts"][0]["reason"])


    def test_redirected_git_pointer_cannot_stage_on_original_branch(self):
        self.write_config(target=1, iterations=1)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "one-iteration")
        original = git(self.repo, "rev-parse", "HEAD")

        def redirect(_value, cwd):
            (Path(cwd) / ".git").write_text(f"gitdir: {self.repo / '.git'}\n")
            return 1

        with self.runner(redirect):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "exhausted", result)
        self.assertEqual(result["attempts"][0]["result"], "rejected")
        self.assertIn("ponteiro .git", result["attempts"][0]["reason"])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), original)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertEqual((self.repo / "calc.py").read_text(), "VALUE = 0\n")

    def test_ignored_agent_file_cannot_inflate_accepted_score(self):
        (self.repo / ".gitignore").write_text("score.txt\n")
        self.evaluator.write_text(self.evaluator.read_text().replace(
            "value = runpy.run_path('calc.py')['VALUE']",
            "value = int(pathlib.Path('score.txt').read_text()) if pathlib.Path('score.txt').exists() else 0"))
        self.write_config(target=2, iterations=1)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "ignore-uncommitted-score")

        def inflate(_value, cwd):
            (Path(cwd) / "score.txt").write_text("2\n")
            return 1

        with self.runner(inflate):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "exhausted", result)
        self.assertEqual(result["best_score"], "0")
        self.assertEqual(result["attempts"][0]["result"], "rejected")
        self.assertIn("score 0", result["attempts"][0]["reason"])
        self.assertEqual((self.repo / "calc.py").read_text(), "VALUE = 0\n")

    def test_missing_evidence_cannot_claim_improvement(self):
        self.evaluator.write_text(self.evaluator.read_text().replace(
            "'evidence': [str(evidence)]", "'evidence': [str(evidence)] if value == 0 else []"))
        self.write_config(target=1, iterations=1)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "evidence-required")
        with self.runner(lambda _value, _cwd: 1):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "paused", result)
        self.assertEqual(result["best_score"], "0")
        self.assertEqual(result["attempts"][0]["result"], "paused")
        self.assertIn("evidência", result["attempts"][0]["reason"])

    def test_dirty_tree_is_refused_and_preserved(self):
        (self.repo / "calc.py").write_text("VALUE = 99\n")
        with self.assertRaisesRegex(loop.LoopError, "alterações"):
            loop.new_run(self.config)
        self.assertFalse(self.state.exists())
        self.assertEqual((self.repo / "calc.py").read_text(), "VALUE = 99\n")

    def test_status_and_stop_work_after_unrelated_user_edit(self):
        self.write_config(iterations=1)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "one-iteration")
        with self.runner(lambda value, _: value + 1):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "exhausted")
        (self.repo / "calc.py").write_text("VALUE = 99\n")
        run_id = result["run_id"]
        for action in ("status", "stop"):
            with patch("sys.stdout", new_callable=io.StringIO) as captured:
                exit_code = loop.main([action, "--config", str(self.config), "--run", run_id])
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(captured.getvalue())["best_score"], "1")
        self.assertTrue((loop.state_root(self.repo) / run_id / "stop.requested").is_file())
        self.assertEqual((self.repo / "calc.py").read_text(), "VALUE = 99\n")

    def test_independent_review_failure_rejects_measured_gain(self):
        self.write_config(target=1, tier=2, iterations=1)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "review-required")
        def invoke(tool, role, prompt, cwd, model_key, timeout=900, env=None):
            if role == "implementer":
                (Path(cwd) / "calc.py").write_text("VALUE = 1\n")
                return {"returncode": 0, "output": "changed behavior", "usage": {}}
            return {"returncode": 0, "output": '{"verdict":"fail","findings":["regression"]}'
                    if role == "reviewer" else "plan", "usage": {}}
        actual_gate = loop.gate_result
        # Keep a real passing gate; tier-2 scanners are not installed in the disposable app.
        def gate_with_available_checks(repo, base, tier, required, changes, deadline=None):
            return actual_gate(repo, base, 0, required, changes, deadline)
        with (patch.dict(sys.modules, {"harness_runner": types.SimpleNamespace(invoke=invoke)}),
              patch.object(loop, "gate_result", side_effect=gate_with_available_checks)):
            result = loop.new_run(self.config)
        self.assertEqual(result["status"], "exhausted", result)
        self.assertEqual(result["best_score"], "0")
        self.assertEqual(result["attempts"][0]["gate"]["checks"]["test"], "pass")
        self.assertIn("reviewer", result["attempts"][0]["reason"])


    def test_resume_after_interrupted_attempt_does_not_repeat_it(self):
        self.write_config(target=1)
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "target-one")
        def interrupt(_, __):
            raise KeyboardInterrupt
        with self.runner(interrupt), self.assertRaises(KeyboardInterrupt):
            loop.new_run(self.config)
        home = loop.state_root(self.repo)
        folder = next(p for p in home.iterdir() if p.is_dir())
        with self.runner(lambda value, _: 1):
            result = loop.resume_run(self.config, folder.name)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual([a["result"] for a in result["attempts"]], ["interrupted", "accepted"])
        self.assertEqual(result["attempts"][-1]["iteration"], 2)

    def test_fixed_zen_model_cannot_bypass_account_catalog(self):
        self.write_config(target=1, billing="zen")
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "zen-config")
        with self.runner(lambda value, _: 1), self.assertRaisesRegex(loop.LoopError, "OpenCode ou OMP"):
            loop.new_run(self.config)

    def test_unknown_paid_usage_blocks_resume_without_reauthorizing(self):
        self.write_config(target=1, iterations=1)
        self.config.write_text(self.config.read_text().replace("max_paid_usd = 0", "max_paid_usd = 1"))
        git(self.repo, "add", ".dev-workflows.toml")
        git(self.repo, "commit", "-qm", "paid-budget")
        selected = {"model_key": "opencode/test", "billing_mode": "zen",
                    "balance_confirmed": True, "estimated_native_usd": "0.1"}
        calls = 0

        def invoke(_tool, _role, _prompt, cwd, _model_key, timeout=900, env=None):
            nonlocal calls
            calls += 1
            (Path(cwd) / "calc.py").write_text("VALUE = 1\n")
            return {"returncode": 0, "output": "changed behavior", "usage": None}

        with (patch.object(loop, "role_model", return_value=selected),
              patch.object(loop, "authorize"),
              patch.dict(sys.modules, {"harness_runner": types.SimpleNamespace(invoke=invoke)})):
            result = loop.new_run(self.config)
            self.assertEqual(result["status"], "paused", result)
            self.assertEqual(result["spent_paid_usd"], "0")
            state = json.loads((loop.state_root(self.repo) / result["run_id"] / "state.json").read_text())
            self.assertTrue(state["unreconciled_paid_call"])
            with self.assertRaisesRegex(loop.LoopError, "concilie"):
                loop.resume_run(self.config, result["run_id"])
        self.assertEqual(calls, 1)

    def test_go_requires_all_three_windows_and_disables_balance_fallback(self):
        config = {"loop": {"max_paid_usd": 0}}
        row = {"billing_mode": "go", "quota_window_remaining": {"5h": "1", "weekly": "1", "monthly": "1"},
               "quota_window_debit": {"5h": "0.2", "weekly": "0.2", "monthly": "0.2"},
               "use_balance_fallback": True}
        with self.assertRaisesRegex(loop.SafetyPause, "fallback"):
            loop.authorize(config, row, loop.Decimal(0))
        row["use_balance_fallback"] = False
        row["quota_window_remaining"]["weekly"] = "0"
        with self.assertRaisesRegex(loop.SafetyPause, "três janelas"):
            loop.authorize(config, row, loop.Decimal(0))
        row["quota_window_remaining"]["weekly"] = "1"
        loop.authorize(config, row, loop.Decimal(0))

    def test_zen_needs_live_interactive_consent_not_stdin_yes(self):
        config = {"loop": {"max_paid_usd": 1}}
        row = {"billing_mode": "zen", "model_key": "opencode/test",
               "estimated_native_usd": "0.2", "balance_confirmed": True}
        with patch("sys.stdin", io.StringIO("SIM\n")), self.assertRaisesRegex(loop.SafetyPause, "interativa"):
            loop.authorize(config, row, loop.Decimal(0))



if __name__ == "__main__":
    unittest.main(verbosity=2)
