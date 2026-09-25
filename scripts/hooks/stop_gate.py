#!/usr/bin/env python3
"""Stop hook: blocks "done" while uncommitted code changes lack a fresh, non-failing quality-gate report.

Claude Code: reads the hook JSON on stdin, prints {"decision": "block", ...} to keep the agent working.
opencode:    `stop_gate.py --check <dir>` prints the reason and exits 2 when it would block.
Disable with DW_GATE=off.
"""
import json, os, subprocess, sys

DOC_EXT = {".md", ".mdx", ".txt", ".rst", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GATE = os.path.join(PLUGIN_ROOT, "scripts", "quality-gate")


def pending_code_files(cwd):
    p = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        return None
    files = []
    for line in p.stdout.splitlines():
        path = line[3:].split(" -> ")[-1].strip('"')
        if line[:2].strip() == "D" or path.startswith(".dev-workflows/"):
            continue
        if os.path.splitext(path)[1].lower() not in DOC_EXT and os.path.isfile(os.path.join(cwd, path)):
            files.append(path)
    return files


def reason_to_block(cwd):
    if os.environ.get("DW_GATE") == "off":
        return None
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True)
    if top.returncode != 0:
        return None
    root = top.stdout.strip()
    files = pending_code_files(root)
    if not files:
        return None
    run = f'"{GATE}" --tier <nível do dev-router>'
    report = os.path.join(root, ".dev-workflows", "gate.json")
    if not os.path.isfile(report):
        return f"Há {len(files)} arquivo(s) de código alterados sem gate de qualidade. Rode {run} e trate o resultado antes de encerrar."
    newest = max(os.path.getmtime(os.path.join(root, f)) for f in files)
    if os.path.getmtime(report) < newest:
        return f"O código mudou depois do último gate. Rode de novo {run} antes de encerrar."
    data = json.load(open(report))
    if data.get("verdict") == "fail":
        failed = ", ".join(c["name"] for c in data.get("checks", []) if c.get("status") == "fail")
        return f"O gate falhou em: {failed}. Corrija (veja .dev-workflows/gate.json) ou explique ao usuário por que não dá para corrigir."
    return None


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--check":
        why = reason_to_block(sys.argv[2])
        if why:
            print(why)
            return 2
        return 0
    event = json.load(sys.stdin)
    if event.get("stop_hook_active"):
        return 0
    why = reason_to_block(event.get("cwd") or os.getcwd())
    if why:
        print(json.dumps({"decision": "block", "reason": why}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
