<div align="center">

# Dev Workflows

**A Claude Code plugin (also for opencode and Hermes Agent) that sizes the process to the request**: a router picks the tier, least-privilege agents do the work, and a deterministic quality gate decides when it is done.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-1.0-8A2BE2)](https://agentskills.io)
[![CI](https://github.com/evandrodevbr/dev-workflows/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)

**🇧🇷 [Ler em português](README.pt-BR.md)**

</div>

---

## Why

Agents write code fast and are bad at two things: knowing when a task deserves more process, and
admitting what they did not verify. This plugin handles both:

- **Process proportional to the request.** A typo does not get a design review; an auth change does.
- **Proof, not claims.** "Done" requires a quality-gate report on the current diff. A tool that is not installed shows up as *unverified*, never as passed.
- **Least code.** Reuse before writing, delete before adding, no dependency without a reason.
- **Security from live sources.** A model's CVE knowledge stops at its training cutoff, so reviews query OSV.dev and stamp the date.

## How it works

`dev-router` loads first and declares a tier:

| Tier | When | What runs |
|---|---|---|
| 0, trivial | nothing changes behavior | the change + gate tier 0 |
| 1, small | 1–3 files, no new public surface | `wf-bugfix` or `wf-refactor`, regression test, gate tier 1 |
| 2, feature | new endpoint/screen, contract change, new dependency | explore, short plan, TDD, independent review, gate tier 2 |
| 3, large/risky | several modules, existing data, architecture, release | EARS spec + ADR approved by you, reviews, security audit, gate tier 3 |

Security triggers raise the tier at any point: auth, money, personal data, uploads, raw SQL,
shell/exec, deserialization, schema migrations, new dependencies, features that call an LLM.

## What is inside

| Kind | Items |
|---|---|
| Router and rules | `dev-router`, `lean-code` |
| Workflows | `wf-bugfix`, `wf-refactor`, `wf-frontend`, `wf-backend`, `wf-architecture`, `wf-security-review`, `wf-readme` |
| Agents | `explorer` (haiku, read-only), `planner` (opus, read-only), `implementer` (sonnet), `reviewer` (opus, read-only, sees only the diff), `security-auditor` (opus, read-only), `ui-critic` (sonnet, read-only), `verifier` (haiku, runs the gate) |
| Hooks | `Stop`: blocks "done" while code changed without a fresh passing gate · `PreToolUse`: denies `--no-verify` and force-push, asks before `reset --hard`, `clean -f`, `DROP TABLE` · `PostToolUse`: formats edited files with the project's own formatter |
| Quality gate | [`scripts/quality-gate`](scripts/quality-gate): lint, typecheck, tests, gitleaks (tier 0); diff coverage, semgrep, dead code (tier 1); build, mutation testing, osv-scanner, architecture rules, duplication (tier 2); trivy, requirement→test traceability (tier 3) |
| Vendored skills | security pillar (OWASP secure-agent-playbook, UnitOneAI SecuritySkills, safedeps, hermaguard) and taste-skill for frontend. Origin and license: [`skills/NOTICE.md`](skills/NOTICE.md) |

The gate runs only the checks of the requested tier, only on the diff, and needs no AI: it is
plain tooling. Checks that need the app running (Lighthouse CI budgets, Playwright + axe, schemathesis,
k6) are added per project in `.dev-workflows.toml`. Reference:
[`skills/dev-router/references/quality-gate.md`](skills/dev-router/references/quality-gate.md).

## Install

```bash
git clone https://github.com/evandrodevbr/dev-workflows && cd dev-workflows

python3 scripts/install.py claude     # plugin: skills + agents + hooks
python3 scripts/install.py opencode   # skills, agents and a plugin in ~/.config/opencode
python3 scripts/install.py hermes     # skills only, in ~/.hermes/skills
```

Claude Code without cloning:

```text
/plugin marketplace add evandrodevbr/dev-workflows
/plugin install dev-workflows@dev-workflows
```

Differences between agents:

- **opencode** cannot block the end of a turn, so a missing or failing gate is logged instead of blocking. Agents are converted to opencode subagents with the same permissions.
- **Hermes** gets the skills only; run the gate yourself.
- For opencode and Hermes the copies point at your checkout, so keep it in place (or re-run the install after moving it).

Turn the `Stop` hook off for one session with `DW_GATE=off`.

## External skills (optional)

Workflows use these when installed and fall back to their own rules when not. Install commands:
[`docs/SKILLS.md`](docs/SKILLS.md).

| Area | Skills |
|---|---|
| Frontend | `frontend-design` (Anthropic), `impeccable` (pbakaus), `vercel-react-best-practices`, `vercel-composition-patterns` (Vercel Labs), `animate` (emilkowalski), `web-design`, `avoid-ai-writing` |
| Backend | `secure-coding`, `bola-detector`, `auth-rbac-scaffold`, `injection-checker`, `openapi-hardener`, `security-test-generator` (apisec-inc) |
| Architecture | `system-design`, `c4-architecture`, `isaqb-architecture-governance`, `secure-architecture-governance` (Kotivskyi) |
| README | `readme-crafter`, `good-readme`, `curating-readme` |

## Quality of this repository

```bash
python3 qa/lint_skills.py      # frontmatter, size limits, references, links, machine-specific paths
python3 qa/test_gate.py        # quality gate and hooks on a throwaway repo
python3 qa/check_upstream.py   # vendored skills behind their upstream
claude plugin validate --strict .claude-plugin/plugin.json
```

CI runs the first two on every PR; the upstream check runs monthly.

**Not measured yet:** whether the kit improves the code an agent produces. Public studies
([SkillsBench](https://arxiv.org/abs/2602.12670), [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401))
show skills can also make results worse, so the next step is an A/B benchmark (with vs. without the
kit) on [Harbor](https://github.com/harbor-framework/harbor) with hidden tests, mutation score and
security checks.

## Layout

```
.claude-plugin/     plugin.json, marketplace.json
skills/             dev-router, lean-code, wf-* workflows, vendored skills (NOTICE.md)
agents/             explorer, planner, implementer, reviewer, security-auditor, ui-critic, verifier
hooks/hooks.json    Stop, PreToolUse, PostToolUse
scripts/            quality-gate, install.py, hooks/*.py
adapters/opencode/  opencode plugin
qa/                 lint, gate tests, upstream check
docs/SKILLS.md      skill inventory and install commands
```

## License

[MIT](LICENSE) © 2026 [Evandro Fonseca Junior](https://github.com/evandrodevbr). Vendored skills keep their own licenses ([`skills/NOTICE.md`](skills/NOTICE.md)).
