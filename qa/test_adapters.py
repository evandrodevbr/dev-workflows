#!/usr/bin/env python3
"""Adapter and headless-runner behavior tests; fake CLIs never contact providers."""
import importlib.util
import json
import os
import pathlib
import sys
import shutil
import unittest
import tempfile
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
REAL_WHICH = shutil.which


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load_module("dev_workflows_install", ROOT / "scripts" / "install.py")
harness = load_module("dev_workflows_harness", ROOT / "scripts" / "harness_runner.py")


class AdapterTest(unittest.TestCase):
    def test_omp_install_preserves_unowned_destination_and_skips_link(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp) / ".omp"
            dest = base / "plugins" / "dev-workflows"
            dest.mkdir(parents=True)
            (dest / "user-data").write_text("preserve", encoding="utf-8")
            runner = mock.Mock()
            with self.assertRaises(SystemExit):
                installer.install_omp(base=str(base), runner=runner)
            runner.assert_not_called()
            self.assertEqual((dest / "user-data").read_text(encoding="utf-8"), "preserve")

    def test_omp_install_keeps_package_for_recovery_if_link_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp) / ".omp"
            runner = mock.Mock(return_value=mock.Mock(returncode=7))
            with self.assertRaisesRegex(SystemExit, "falhou com código 7"):
                installer.install_omp(base=str(base), runner=runner)
            self.assertTrue((base / "plugins" / "dev-workflows" / ".dev-workflows-omp-package").is_file())



class HarnessRunnerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.cwd = self.root / "state" / "project" / "run" / "worktrees" / "iteration-001"
        self.cwd.mkdir(parents=True)
        gitdir = self.root / "project" / ".git" / "worktrees" / "iteration-001"
        gitdir.mkdir(parents=True)
        (self.cwd / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.trace = self.root / "calls.jsonl"
        self.cache = self.root / "catalog"
        self.cache.mkdir()
        self._fake_cli()

    def tearDown(self):
        self.temp.cleanup()

    def _fake_cli(self):
        executable = self.bin / "fake-cli"
        executable.write_text(
            "#!" + sys.executable + "\n"
            "import json, os, pathlib, sys\n"
            "name = pathlib.Path(sys.argv[0]).name\n"
            "args = sys.argv[1:]\n"
            "with open(os.environ['DW_TRACE'], 'a', encoding='utf-8') as out:\n"
            "    out.write(json.dumps({'name': name, 'args': args, 'cwd': os.getcwd(), 'marker': os.getenv('DW_MARKER')}) + '\\n')\n"
            "if name == 'claude' and args[:3] == ['auth', 'status', '--json']:\n"
            "    print(os.environ.get('DW_CLAUDE_AUTH', '{\\\"loggedIn\\\": true}'))\n"
            "elif name == 'opencode' and args[:1] == ['models']:\n"
            "    print(os.environ.get('DW_MODELS', ''))\n"
            "elif name == 'omp' and args[:2] == ['models', args[1] if len(args) > 1 else '']:\n"
            "    print(os.environ.get('DW_MODELS_JSON', '[]'))\n"
            "else:\n"
            "    print('fake response')\n"
            "    print('sk-secret-must-not-escape', file=sys.stderr)\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        for name in ("claude", "opencode", "omp"):
            (self.bin / name).symlink_to(executable)

    def _env(self, **extra):
        value = os.environ.copy()
        value.update({
            "PATH": str(self.bin) + os.pathsep + value.get("PATH", ""),
            "DEV_WORKFLOWS_MODEL_CACHE": str(self.cache),
            "DW_TRACE": str(self.trace),
            "DW_MARKER": "test-env",
        })
        value.update(extra)
        return value

    def _snapshot(self, tool, model_key, *, entitled=True, variant=None, provider=None, model_id=None):
        row = {
            "tool": tool,
            "model_key": model_key,
            "availability": {
                "local_listed": True,
                "authenticated": True,
                "entitled": entitled,
                "source": "manual_audited",
                "verified_at": "2026-09-25T12:00:00Z",
            },
        }
        if variant is not None:
            row.update({"variant": variant, "provider": provider, "model_id": model_id})
        (self.cache / f"catalog-{tool}.json").write_text(
            json.dumps({"schema_version": 1, "tool": tool, "models": [row]}), encoding="utf-8"
        )

    def _calls(self):
        if not self.trace.exists():
            return []
        return [json.loads(line) for line in self.trace.read_text(encoding="utf-8").splitlines()]

    def _fake_bwrap(self):
        trace = self.root / "bwrap.jsonl"
        executable = self.bin / "bwrap"
        executable.write_text(
            "#!" + sys.executable + "\n"
            "import json, os, pathlib, sys\n"
            "args = sys.argv[1:]\n"
            "with open(os.environ['DW_BWRAP_TRACE'], 'a', encoding='utf-8') as out:\n"
            "    out.write(json.dumps(args) + '\\n')\n"
            "command = args[args.index('--') + 1:]\n"
            "tool = pathlib.Path(command[0]).name\n"
            "if tool == 'omp' and 'models' in command:\n"
            "    print(os.environ.get('DW_MODELS_JSON', '[]'))\n"
            "elif tool == 'opencode' and 'models' in command:\n"
            "    print(os.environ.get('DW_MODELS', ''))\n"
            "elif tool == 'claude' and command[1:3] == ['auth', 'status']:\n"
            "    print(os.environ.get('DW_CLAUDE_AUTH', '{\\\"loggedIn\\\": true}'))\n"
            "else:\n"
            "    print('fake wrapped response')\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        return trace

    def _invoke_with_fake_bwrap(self, *args, **kwargs):
        def find_executable(name, path=None):
            if name == "bwrap":
                return str(self.bin / "bwrap")
            return REAL_WHICH(name, path=path)

        with mock.patch.object(harness.shutil, "which", side_effect=find_executable):
            return harness.invoke(*args, **kwargs)

    def test_claude_alias_and_dontask_preserve_default_permission_gate(self):
        result = harness.invoke("claude", "reviewer", "Review safely", str(self.cwd), "opus", env=self._env())
        self.assertEqual(result["returncode"], 0)
        calls = self._calls()
        self.assertEqual(calls[0]["args"], ["auth", "status", "--json"])
        call = calls[1]
        args = call["args"]
        self.assertIn("--permission-mode", args)
        self.assertEqual(args[args.index("--permission-mode") + 1], "dontAsk")
        self.assertIn("--agent", args)
        self.assertIn("reviewer", args)
        self.assertEqual(args[args.index("--model") + 1], "opus")
        self.assertNotIn("--dangerously-skip-permissions", args)
        self.assertEqual(call["cwd"], str(self.cwd))
        self.assertEqual(call["marker"], "test-env")
        self.assertIsNone(result["usage"])
        self.assertNotIn("sk-secret", result["output"])

    def test_claude_inherit_keeps_role_alias_without_model_override(self):
        result = harness.invoke("claude", "explorer", "Map the project", str(self.cwd), "inherit", env=self._env())
        self.assertEqual(result["returncode"], 0)
        calls = self._calls()
        self.assertEqual(calls[0]["args"], ["auth", "status", "--json"])
        args = calls[1]["args"]
        self.assertIn("--agent", args)
        self.assertNotIn("--model", args)
        self.assertNotIn("--dangerously-skip-permissions", args)

    def test_sonnet_alias_is_passed_without_rewriting_the_plugin(self):
        harness.invoke("claude", "ui-critic", "Critique only", str(self.cwd), "sonnet", env=self._env())
        calls = self._calls()
        args = calls[1]["args"]
        self.assertEqual(args[args.index("--model") + 1], "sonnet")
        self.assertEqual(args[args.index("--agent") + 1], "ui-critic")

    def test_claude_alias_is_blocked_when_local_auth_status_is_negative(self):
        with self.assertRaisesRegex(harness.HarnessError, "auth status"):
            harness.invoke(
                "claude", "reviewer", "Review", str(self.cwd), "opus",
                env=self._env(DW_CLAUDE_AUTH='{"loggedIn": false}'),
            )
        calls = self._calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["args"], ["auth", "status", "--json"])

    def test_opencode_uses_exact_variant_and_role_agent_without_auto_approval(self):
        model_key = "openai/gpt-6-luna#high"
        self._snapshot("opencode", model_key)
        result = harness.invoke(
            "opencode", "planner", "Plan only", str(self.cwd), model_key,
            env=self._env(DW_MODELS="gpt-6-luna"),
        )
        self.assertEqual(result["returncode"], 0)
        calls = self._calls()
        self.assertEqual(calls[0]["args"], ["models", "openai"])
        args = calls[1]["args"]
        self.assertEqual(args[:3], ["run", "--agent", "planner"])
        self.assertEqual(args[args.index("--model") + 1], model_key)
        self.assertNotIn("--auto", args)
        self.assertEqual(calls[1]["cwd"], str(self.cwd))
        self.assertIn("stderr omitido por segurança", result["output"])
        self.assertNotIn("sk-secret", result["output"])

    def test_omp_runs_with_exact_tools_and_always_ask(self):
        model_key = "openai/gpt-6-luna#high"
        self._snapshot("omp", model_key, variant="high", provider="openai", model_id="gpt-6-luna")
        result = harness.invoke(
            "omp", "explorer", "Inspect only", str(self.cwd), model_key,
            env=self._env(DW_MODELS_JSON=json.dumps([{"provider": "openai", "id": "gpt-6-luna",
                                                      "thinking": ["low", "high"]}])),
        )
        self.assertEqual(result["returncode"], 0)
        calls = self._calls()
        self.assertEqual(calls[0]["args"], ["models", "openai", "--json"])
        args = calls[1]["args"]
        self.assertEqual(args[0], "-p")
        self.assertEqual(args[args.index("--model") + 1], "openai/gpt-6-luna")
        self.assertEqual(args[args.index("--thinking") + 1], "high")
        self.assertEqual(args[args.index("--approval-mode") + 1], "always-ask")
        self.assertNotIn("--auto-approve", args)
        self.assertEqual(args[args.index("--tools") + 1], "read,grep,glob")
        self.assertEqual(args[args.index("--cwd") + 1], str(self.cwd))

    def test_omp_unknown_thinking_variant_is_rejected_before_listing_or_dispatch(self):
        model_key = "openai/model#unsupported"
        self._snapshot("omp", model_key, variant="unsupported", provider="openai", model_id="model")
        with self.assertRaisesRegex(harness.HarnessError, "variante"):
            harness.invoke("omp", "explorer", "Inspect", str(self.cwd), model_key, env=self._env())
        self.assertEqual(self._calls(), [])

    def test_omp_rejects_thinking_not_supported_by_current_model_listing(self):
        model_key = "openai/gpt-6-luna#high"
        self._snapshot("omp", model_key, variant="high", provider="openai", model_id="gpt-6-luna")
        listed = {"models": [{"provider": "openai", "id": "gpt-6-luna", "thinking": ["low"]}]}
        with self.assertRaisesRegex(harness.HarnessError, "indisponível"):
            harness.invoke("omp", "explorer", "Inspect", str(self.cwd), model_key,
                           env=self._env(DW_MODELS_JSON=json.dumps(listed)))
        self.assertEqual([call["args"] for call in self._calls()], [["models", "openai", "--json"]])

    def test_omp_slash_model_id_keeps_provider_and_qualified_selector(self):
        model_key = "openrouter/anthropic/claude-sonnet-4.6"
        self._snapshot("omp", model_key)
        listed = {"models": [{"provider": "openrouter", "id": "anthropic/claude-sonnet-4.6",
                              "selector": model_key, "thinking": None}]}
        result = harness.invoke("omp", "explorer", "Inspect", str(self.cwd), model_key,
                                env=self._env(DW_MODELS_JSON=json.dumps(listed)))
        self.assertEqual(result["returncode"], 0)
        calls = self._calls()
        self.assertEqual(calls[0]["args"], ["models", "openrouter", "--json"])
        self.assertEqual(calls[1]["args"][calls[1]["args"].index("--model") + 1], model_key)


    def test_autonomous_omp_uses_bwrap_and_bounded_tools_with_auto_approval(self):
        model_key = "openai/gpt-6-luna#high"
        self._snapshot("omp", model_key, variant="high", provider="openai", model_id="gpt-6-luna")
        trace = self._fake_bwrap()
        result = self._invoke_with_fake_bwrap(
            "omp", "implementer", "Inspect only", str(self.cwd), model_key,
            env=self._env(
                DEV_WORKFLOWS_AUTONOMOUS="1",
                DW_BWRAP_TRACE=str(trace),
                DW_MODELS_JSON=json.dumps([{"provider": "openai", "id": "gpt-6-luna",
                                            "thinking": ["low", "high"]}]),
            ),
        )
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(self._calls(), [])
        calls = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(calls), 2)
        for args in calls:
            self.assertEqual(args[:6], ["--unshare-all", "--share-net", "--die-with-parent", "--ro-bind", "/", "/"])
            binds = [args[index + 1:index + 3] for index, value in enumerate(args) if value == "--bind"]
            self.assertIn([str(self.cwd), str(self.cwd)], binds)
            readonly = [args[index + 1:index + 3] for index, value in enumerate(args) if value == "--ro-bind"]
            self.assertIn([str(self.cwd / ".git"), str(self.cwd / ".git")], readonly)
        preflight = calls[0][calls[0].index("--") + 1:]
        self.assertEqual(pathlib.Path(preflight[0]).name, "omp")
        self.assertEqual(preflight[1:4], ["--no-extensions", "models", "openai"])
        command = calls[1][calls[1].index("--") + 1:]
        self.assertEqual(pathlib.Path(command[0]).name, "omp")
        self.assertEqual(command[1], "-p")
        for flag in ("--no-extensions", "--no-lsp", "--no-session", "--auto-approve"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--model") + 1], "openai/gpt-6-luna")
        self.assertEqual(command[command.index("--thinking") + 1], "high")
        self.assertEqual(command[command.index("--tools") + 1], "read,grep,glob,edit,write")
        self.assertNotIn("bash", command)
        self.assertNotIn("web_search", command)

    def test_autonomous_opencode_uses_pure_mode_and_synthetic_deny_agent(self):
        model_key = "openai/gpt-6-luna#high"
        self._snapshot("opencode", model_key)
        trace = self._fake_bwrap()
        meta, prompt = harness._agent("implementer")
        generated = harness._opencode_loop_agent(meta, prompt)
        self.assertIn('  "*": deny', generated)
        self.assertIn("  bash: deny", generated)
        self.assertIn("  edit: allow", generated)
        self.assertIn("  task: deny", generated)
        result = self._invoke_with_fake_bwrap(
            "opencode", "implementer", "Implement safely", str(self.cwd), model_key,
            env=self._env(DEV_WORKFLOWS_AUTONOMOUS="1", DW_BWRAP_TRACE=str(trace), DW_MODELS="gpt-6-luna"),
        )
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(self._calls(), [])
        calls = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(calls), 2)
        preflight = calls[0][calls[0].index("--") + 1:]
        self.assertEqual(pathlib.Path(preflight[0]).name, "opencode")
        self.assertEqual(preflight[1:3], ["--pure", "models"])
        command = calls[1][calls[1].index("--") + 1:]
        self.assertEqual(pathlib.Path(command[0]).name, "opencode")
        self.assertEqual(command[1:4], ["--pure", "run", "--agent"])
        agent_name = command[4]
        self.assertRegex(agent_name, r"\Adev-workflows-loop-implementer-[0-9a-f]{16}\Z")
        self.assertIn("--file", calls[1])

    def test_autonomous_claude_uses_bare_mode_and_declared_safe_tools(self):
        trace = self._fake_bwrap()
        result = self._invoke_with_fake_bwrap(
            "claude", "reviewer", "Review only", str(self.cwd), "opus",
            env=self._env(DEV_WORKFLOWS_AUTONOMOUS="1", DW_BWRAP_TRACE=str(trace)),
        )
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(self._calls(), [])
        calls = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(calls), 2)
        auth = calls[0][calls[0].index("--") + 1:]
        self.assertEqual(pathlib.Path(auth[0]).name, "claude")
        self.assertEqual(auth[1:], ["auth", "status", "--json"])
        command = calls[1][calls[1].index("--") + 1:]
        self.assertIn("--bare", command)
        self.assertIn("--no-session-persistence", command)
        self.assertEqual(command[command.index("--permission-mode") + 1], "dontAsk")
        agent_config = json.loads(command[command.index("--agents") + 1])
        self.assertEqual(agent_config["reviewer"]["tools"], ["Read", "Grep", "Glob"])
        self.assertEqual(command[command.index("--tools") + 1], "Read,Grep,Glob")
        self.assertNotIn("Bash", command)

    def test_autonomous_mode_fails_closed_without_bwrap(self):
        self._snapshot("omp", "openai/gpt-6-luna")
        def find_without_bwrap(name, path=None):
            return None if name == "bwrap" else REAL_WHICH(name, path=path)
        with mock.patch.object(harness.shutil, "which", side_effect=find_without_bwrap):
            with self.assertRaisesRegex(harness.HarnessError, "bwrap"):
                harness.invoke(
                    "omp", "explorer", "Inspect", str(self.cwd), "openai/gpt-6-luna",
                    env=self._env(PATH=str(self.bin), DEV_WORKFLOWS_AUTONOMOUS="1"),
                )
        self.assertEqual(self._calls(), [])

    def test_autonomous_rejects_non_worktree_cwd_before_dispatch(self):
        other = self.root / "ordinary-directory"
        other.mkdir()
        with self.assertRaisesRegex(harness.HarnessError, "worktree"):
            harness.invoke(
                "omp", "explorer", "Inspect", str(other), "openai/gpt-6-luna",
                env=self._env(DEV_WORKFLOWS_AUTONOMOUS="1"),
            )
        self.assertEqual(self._calls(), [])

    def test_autonomous_does_not_resolve_cli_from_writable_worktree(self):
        self._snapshot("opencode", "openai/gpt-6-luna")
        shadow = self.cwd / "opencode"
        shadow.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        shadow.chmod(0o755)
        with self.assertRaisesRegex(harness.HarnessError, "PATH seguro"):
            harness.invoke(
                "opencode", "planner", "Plan", str(self.cwd), "openai/gpt-6-luna",
                env=self._env(PATH=str(self.cwd), DEV_WORKFLOWS_AUTONOMOUS="1"),
            )
        self.assertEqual(self._calls(), [])

    def test_unentitled_model_is_blocked_before_cli_is_started(self):
        self._snapshot("opencode", "openai/gpt-6-luna", entitled=False)
        with self.assertRaisesRegex(harness.HarnessError, "autorização local"):
            harness.invoke(
                "opencode", "planner", "Plan", str(self.cwd), "openai/gpt-6-luna",
                env=self._env(DW_MODELS="gpt-6-luna"),
            )
        self.assertEqual(self._calls(), [])

    def test_model_absent_from_local_cli_is_blocked_before_agent_dispatch(self):
        self._snapshot("opencode", "openai/gpt-6-luna")
        with self.assertRaisesRegex(harness.HarnessError, "indisponível na CLI local"):
            harness.invoke(
                "opencode", "planner", "Plan", str(self.cwd), "openai/gpt-6-luna",
                env=self._env(DW_MODELS="openai/different-model"),
            )
        calls = self._calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["args"], ["models", "openai"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
