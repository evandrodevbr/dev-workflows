#!/usr/bin/env python3
"""Compares each vendored skill's recorded commit (skills/NOTICE.md) with its upstream HEAD. Exit 1 if any moved.

python3 qa/check_upstream.py
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    notice = open(os.path.join(ROOT, "skills", "NOTICE.md"), encoding="utf-8").read()
    repos = {}
    for row in re.findall(r"^\|\s*`[\w-]+`\s*\|(.+)$", notice, re.M):
        cols = [c.strip() for c in row.split("|")]
        repo = re.search(r"([\w.-]+/[\w.-]+)", cols[0])
        sha = re.search(r"`([0-9a-f]{7,40})`", cols[1])
        if repo and sha:
            repos[repo.group(1)] = sha.group(1)
    moved = 0
    for repo, sha in sorted(repos.items()):
        p = subprocess.run(["git", "ls-remote", f"https://github.com/{repo}", "HEAD"], capture_output=True, text=True, timeout=60)
        head = p.stdout.split()[0] if p.returncode == 0 and p.stdout else None
        if head is None:
            print(f"?  {repo}: não consegui consultar")
        elif head.startswith(sha):
            print(f"ok {repo} {sha}")
        else:
            moved += 1
            print(f"-> {repo}: vendorizado {sha}, upstream {head[:7]}  (https://github.com/{repo}/compare/{sha}...{head[:7]})")
    return 1 if moved else 0


if __name__ == "__main__":
    sys.exit(main())
