#!/usr/bin/env python3
"""PostToolUse: formats the edited file with the formatter the project already uses. Never fails the edit.

Claude Code: reads tool_input.file_path from the hook JSON on stdin.
opencode:    `post_edit.py --file <path>`.
"""
import json, os, shutil, subprocess, sys

PRETTIER_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json", ".css", ".scss", ".html", ".vue", ".svelte", ".md", ".yaml", ".yml"}


def project_root(path):
    d = os.path.dirname(os.path.abspath(path))
    while d != os.path.dirname(d):
        if any(os.path.exists(os.path.join(d, m)) for m in ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", ".git")):
            return d
        d = os.path.dirname(d)
    return None


def uses_ruff(root):
    if os.path.exists(os.path.join(root, "ruff.toml")) or os.path.exists(os.path.join(root, ".ruff.toml")):
        return True
    pyproject = os.path.join(root, "pyproject.toml")
    return os.path.exists(pyproject) and "[tool.ruff" in open(pyproject).read()


def formatter(path, root):
    ext = os.path.splitext(path)[1].lower()
    prettier = os.path.join(root, "node_modules", ".bin", "prettier")
    if ext in PRETTIER_EXT and os.path.exists(prettier):
        return [prettier, "--write", "--log-level", "warn", path]
    if ext == ".py" and shutil.which("ruff") and uses_ruff(root):
        return ["ruff", "format", "--quiet", path]
    if ext == ".go" and shutil.which("gofmt"):
        return ["gofmt", "-w", path]
    if ext == ".rs" and shutil.which("rustfmt"):
        return ["rustfmt", path]
    return None


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--file":
        path = sys.argv[2]
    else:
        path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
    root = project_root(path) if path and os.path.isfile(path) else None
    cmd = formatter(path, root) if root else None
    if cmd:
        try:
            subprocess.run(cmd, cwd=root, capture_output=True, timeout=30)
        except (subprocess.TimeoutExpired, OSError):
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
