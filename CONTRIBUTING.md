# Contributing

Open an issue to discuss first, then send a small, focused PR.

## Rules

1. **Grounded.** Every command, path and claim in a skill or README traces to a real fact. No invented commands or badges.
2. **Short skills.** `SKILL.md` stays under 150 lines; details go to `references/` next to it.
3. **Proportional.** Each phase says from which tier it runs. Nothing is mandatory for every request unless it is cheap (the tier 0 gate).
4. **Checks are tools, not keyword counts.** A verification step runs something that can fail (tests, scanners, the gate). `grep -c` of a word proves nothing.
5. **No AI-isms** in docs and skills (no em-dash runs, no "robust/seamless/leverage").
6. **Vendored skills are copied 1:1** with their license, and recorded in `skills/NOTICE.md` (origin, commit, license).

## Local checks before a PR

```bash
python3 qa/lint_skills.py
python3 qa/test_gate.py
claude plugin validate --strict .claude-plugin/plugin.json
```

A new skill referenced by a workflow goes into its `metadata.dev-workflows.uses` (vendored) or
`external` (listed in `docs/SKILLS.md`); the lint checks both.

## Process

1. Fork and branch: `git checkout -b feat/your-change`.
2. Make the change and run the checks above.
3. Open a PR saying what changed and why.
