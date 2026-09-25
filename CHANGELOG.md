# Changelog

## 2.0.0 (2026-09-24)

### Added
- Claude Code plugin packaging (`.claude-plugin/plugin.json`, `marketplace.json`); workflows moved to `skills/<name>/SKILL.md`.
- `dev-router`: tiers 0 to 3 with security triggers that raise the tier, so small requests skip heavy phases.
- `lean-code`: reuse ladder, dependency justification, diff budget per tier.
- `wf-bugfix` and `wf-refactor`.
- Agents: `explorer`, `planner`, `implementer`, `reviewer`, `security-auditor`, `ui-critic`, `verifier`, each with only the tools its role needs.
- `scripts/quality-gate`: deterministic checks per tier, scoped to the diff; missing tools reported as unverified; new dependencies listed.
- Hooks: `Stop` gate, shell command guard, formatter after edits.
- opencode adapter and `scripts/install.py` for Claude Code, opencode and Hermes Agent.
- taste-skill (`design-taste-frontend`, `redesign-existing-projects`) vendored for `wf-frontend`.
- `qa/lint_skills.py`, `qa/test_gate.py`, `qa/check_upstream.py` and CI.

### Changed
- The five workflows were cut to about 100 lines each; phases state their minimum tier; grep-count checks replaced by the gate and real tools.
- Security references moved to OWASP Top 10:2025, ASVS 5.0 and OWASP LLM Top 10 (2025).
- Machine-specific paths (`~/.hermes/...`, `vision_analyze`) and references to skills that do not exist publicly removed.

### Removed
- The keyword-count quality harness (`qa/wf_quality_harness.py`, `test_quality.py`, `test_tests.py`, snapshots). It scored occurrences of words like `VERIFICAR` and `NUNCA`, so its "+98.6%" measured wording, not quality; it also failed on a fresh clone because it looked for skills in `~/.hermes`.
- apisec-inc's `api-security-review` from `wf-backend` (name collision with the vendored OWASP skill).
