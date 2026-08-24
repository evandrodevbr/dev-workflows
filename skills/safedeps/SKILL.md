---
name: safedeps
description: >
  Grounds dependency decisions in live OSV.dev vulnerability data instead of a
  model's frozen training-cutoff knowledge. Trigger whenever you are about to
  add a dependency, bump/upgrade a package version, choose between package
  versions, answer "is <package> safe / vulnerable", or review a manifest or
  lockfile (requirements.txt, package.json, package-lock.json, go.mod) for
  security issues. Also trigger on requests like "check my dependencies for
  vulnerabilities" or "what version of X should I use".
---

# safedeps

Your training data has a cutoff. CVEs published after it are invisible to
you, and a vulnerable package version doesn't error at runtime -- it just
runs, quietly exploitable. Don't guess. Ask OSV.dev.

## When to run this

Before you write a version number into a manifest, or when asked to review
one, run the checker and use its real output instead of your own
recollection of which versions are safe.

```bash
python3 <skill_dir>/../../check_deps.py <package>@<version>:<ecosystem>
python3 <skill_dir>/../../check_deps.py path/to/requirements.txt
```

(`<skill_dir>` is this file's directory; the script lives at the repo/plugin
root as `check_deps.py`. Ecosystems: `npm`, `PyPI`, `Go`, `crates.io`,
`Maven`, etc. -- omit `:ecosystem` and it defaults to `npm`.)

The script prints one of two things per package, straight from OSV.dev:

```
OK    npm:left-pad@1.3.0 -- no known advisories
VULN  npm:lodash@4.17.21 -- 2 advisory(ies):
  - CVE-2026-4800 [HIGH] lodash vulnerable to Code Injection via `_.template` imports key names
      fix: upgrade to 4.18.0
```

## What to do with the output

1. If a package you're about to add/bump shows `VULN`, do not use that
   version. Use the version named in `fix:` instead (or newer).
2. If no fixed version is listed, tell the user there's an open advisory
   with no patch yet -- let them decide.
3. Always surface the advisory IDs and severities to the user; don't
   silently swap versions without saying why.
4. If the script reports OSV.dev is unreachable, say so plainly and fall
   back to your own knowledge with a caveat that it may be stale -- don't
   pretend you checked.

## Examples

**Adding a dependency**: user asks to add `flask` to a Python project.
Run `check_deps.py flask@3.0.0:PyPI` (the version you were about to pick)
before writing it to `requirements.txt`. If it's clean, proceed. If not,
check the `fix:` version and use that instead.

**Reviewing a project**: user asks "are my dependencies safe?" Run
`check_deps.py requirements.txt` (or `package.json`) in their project root
and report every `VULN` line with its fix version.
