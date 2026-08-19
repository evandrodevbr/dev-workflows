# Contributing

Thanks for taking the time to contribute. This project is small, so keep it simple: open an issue to discuss first, then send a PR.

## What to improve

Workflows, skills, or the QA harness. All changes should keep the same rules the workflows themselves enforce:

1. **Grounded.** Every claim in a workflow or README must trace back to a real repository fact. No fabricated commands, examples, or badges.
2. **Verifiable phases.** A phase is not done until it has a verification step (a command that proves the work). Add one if you touch a workflow.
3. **No AI-isms.** Docs and workflows must pass the avoid-ai-writing check (no em-dash runs, no "robust/seamless/leverage" filler).

## What not to change

- The QA harness must keep its meta-tests green. If you change scoring, re-run `qa/test_tests.py` and update `qa/snapshots/baseline-final.json`.
- Do not remove skills referenced by workflows without updating the workflows and `docs/SKILLS.md` together.

## Local checks before a PR

```bash
cd qa
python3 wf_quality_harness.py    # score must not drop below baseline
python3 test_quality.py          # gates green
python3 test_tests.py            # meta-tests green
```

## Process

1. Fork the repo.
2. Create a branch: `git checkout -b feat/your-change`.
3. Make the change. Keep it small and focused.
4. Run the qa checks above.
5. Commit with a clear message.
6. Open a PR describing what changed and why.

Questions or ideas: open an issue.
