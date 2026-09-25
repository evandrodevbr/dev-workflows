#!/usr/bin/env python3
"""Smoke tests for scripts/quality-gate and the hook scripts, on a throwaway git repo. Stdlib only.

python3 qa/test_gate.py
"""
import importlib.util, json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "scripts", "quality-gate")
STOP = os.path.join(ROOT, "scripts", "hooks", "stop_gate.py")
spec = importlib.util.spec_from_file_location("bash_guard", os.path.join(ROOT, "scripts", "hooks", "bash_guard.py"))
bash_guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bash_guard)


def run(cmd, cwd, stdin=None):
    return subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True)


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        for c in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"], ["git", "config", "user.name", "t"]):
            run(c, self.repo)
        self.write("calc.py", "def add(a, b):\n    return a + b\n")
        self.write("check.py", "from calc import add\nassert add(1, 2) == 3\n")
        self.write(".dev-workflows.toml", '[commands]\ntest = "python3 check.py"\nlint = "true"\ntypecheck = "true"\n')
        self.write("package.json", '{"dependencies": {"left-pad": "1"}}')
        run(["git", "add", "-A"], self.repo)
        run(["git", "commit", "-qm", "init"], self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        open(os.path.join(self.repo, name), "w").write(text)

    def gate(self, tier=0):
        p = run([sys.executable, GATE, "--tier", str(tier)], self.repo)
        return p.returncode, json.load(open(os.path.join(self.repo, ".dev-workflows", "gate.json")))

    def stop(self):
        out = run([sys.executable, STOP], self.repo, json.dumps({"cwd": self.repo})).stdout
        return json.loads(out)["reason"] if out.strip() else None

    def status(self, report, name):
        return next(c["status"] for c in report["checks"] if c["name"] == name)

    def test_clean_tree_does_not_block(self):
        self.assertIsNone(self.stop())

    def test_change_without_gate_blocks_then_passing_gate_allows(self):
        self.write("calc.py", "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n")
        self.assertIn("sem gate", self.stop())
        code, report = self.gate()
        self.assertEqual(code, 0)
        self.assertEqual(self.status(report, "test"), "pass")
        self.assertIsNone(self.stop())

    def test_failing_test_fails_gate_and_blocks(self):
        self.write("calc.py", "def add(a, b):\n    return a - b\n")
        code, report = self.gate()
        self.assertEqual((code, report["verdict"]), (1, "fail"))
        self.assertIn("test", self.stop())

    def test_missing_tool_is_unverified_not_passed(self):
        self.write(".dev-workflows.toml", '[commands]\ntest = "definitely-not-a-tool-xyz"\n')
        self.write("calc.py", "def add(a, b):\n    return b + a\n")
        code, report = self.gate()
        self.assertEqual(self.status(report, "test"), "unverified")
        self.assertEqual(report["verdict"], "incomplete")

    def test_new_dependency_is_reported(self):
        self.write("package.json", '{"dependencies": {"left-pad": "1", "is-odd": "3"}}')
        self.write("calc.py", "def add(a, b):\n    return a + b  # touched\n")
        _, report = self.gate()
        self.assertEqual(report["new_dependencies"], ["npm:is-odd"])

    def test_stale_gate_blocks(self):
        self.write("calc.py", "def add(a, b):\n    return a + b  # v2\n")
        self.gate()
        os.utime(os.path.join(self.repo, ".dev-workflows", "gate.json"), (1, 1))
        self.assertIn("mudou depois", self.stop())


class GuardTest(unittest.TestCase):
    def test_decisions(self):
        cases = {"git commit --no-verify -m x": "deny", "git push -f origin main": "deny",
                 "git push --force-with-lease": None, "rm -rf /": "deny", "rm -rf node_modules": None,
                 "git reset --hard": "ask", "npm test": None}
        for cmd, expected in cases.items():
            self.assertEqual(bash_guard.decide(cmd)[0], expected, cmd)


if __name__ == "__main__":
    unittest.main(verbosity=1)
