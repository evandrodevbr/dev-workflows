<div align="center">

# Dev Workflows

**A proportional development workflow for coding agents.**

Claude Code plugin · OpenCode and OMP adapters · Hermes skills-only installation

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-1.0-8A2BE2)](https://agentskills.io)
[![CI](https://github.com/evandrodevbr/dev-workflows/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)

[Português (Brasil)](README.pt-BR.md)

[Overview](#overview) · [Install](#install) · [Daily workflow](#daily-workflow) ·
[Goal loop](#optional-goal-driven-loop) · [Model routing](#model-catalog-and-routing) ·
[Safety](#safety-and-limitations)

</div>

## Overview

Agents can write code quickly; deciding **how much process a change needs** and **whether it was actually verified** is harder. Dev Workflows supplies a small workflow router, least-privilege agents, and a deterministic quality gate. Two separate command-line tools add model discovery and goal-driven iteration when you explicitly use them.

| Capability | What it does | How it starts |
|---|---|---|
| **Development workflow** | Chooses a tier (0–3), loads relevant skills/agents, and checks the current diff. | Install the plugin or skills. |
| **Model catalog** | Shows exact provider IDs, account eligibility, evidence, scores, and reference prices without invoking a model. | Run `scripts/model_catalog.py`. |
| **Goal loop** | Measures an application goal, tests isolated changes, and retains only verified improvements. | Configure the project and explicitly run `scripts/goal_loop.py`. |

**Installing the plugin does not start the goal loop, buy model access, or alter your project.** The model's coding-benchmark score and your application's goal score are different measurements.

## Install

Clone the repository, then choose the runtime you use:

```bash
git clone https://github.com/evandrodevbr/dev-workflows
cd dev-workflows

python3 scripts/install.py claude     # Claude Code: plugin, agents, skills, hooks
python3 scripts/install.py opencode   # OpenCode: plugin, agents, skills
python3 scripts/install.py omp        # OMP: native package, agents, skills
python3 scripts/install.py hermes     # Hermes Agent: skills only
```

For Claude Code, you can instead install from its marketplace without cloning:

```text
/plugin marketplace add evandrodevbr/dev-workflows
/plugin install dev-workflows@dev-workflows
```

| Runtime | Installation result | Gate behavior |
|---|---|---|
| Claude Code | Plugin with seven agents, skills, and Claude hooks | `Stop` hook blocks an unverified completion. |
| OpenCode | Plugin and deny-by-default subagents | Its end-of-turn hook warns; the external goal loop enforces the gate itself. |
| OMP | Linked native plugin with seven agents and skills | No copied Claude hooks; the external goal loop enforces the gate. |
| Hermes Agent | Skills only | Run the gate manually; there is no Hermes goal-loop executor. |

OpenCode and Hermes copies refer to this checkout; keep it in place or reinstall after moving it. The generated OMP package is self-contained. See the [skill inventory](docs/SKILLS.md) for vendored sources and optional external skills.

## Daily workflow

The `dev-router` skill selects a tier and `lean-code` favors reuse, deletion, and the smallest justified change. Higher-risk work raises the tier; authentication, money, personal data, uploads, raw SQL, shell execution, schema migrations, new dependencies, and LLM integrations are explicit triggers.

| Tier | Typical change | Minimum workflow |
|---|---|---|
| **0 — trivial** | No behavior change | Make the change; run the tier-0 gate. |
| **1 — small** | Localized behavior change, no new public surface | Reproduce or characterize behavior, test the change, run tier 1. |
| **2 — feature** | New endpoint/screen, contract change, or cross-file feature | Plan briefly, test, review independently, run tier 2. |
| **3 — high risk** | Architecture, existing data, migration, or release | Approve a spec/ADR, review and audit, run tier 3. |

The [quality gate](scripts/quality-gate) runs ordinary project tools against the current diff, including the checks required for the chosen tier. **`pass` is evidence; missing tools are `incomplete`, not silently green.** Project-specific commands and checks live in `.dev-workflows.toml`; see the [gate reference](skills/dev-router/references/quality-gate.md). Claude's `Stop`, `PreToolUse`, and `PostToolUse` hooks preserve gate, dangerous-command, and formatting behavior. `DW_GATE=off` disables Claude's `Stop` hook for one session; it does **not** override the external goal loop's gate.

Optional frontend, backend, architecture, security, and documentation skills are listed with their origins and installation instructions in [docs/SKILLS.md](docs/SKILLS.md). Workflows can operate without those external skills.

## Optional goal-driven loop

The loop is an **external controller**, not an agent promise to keep trying. It runs only on a clean Git checkout, measures a baseline, and commits each candidate inside a detached attempt worktree. The gate and evaluator run in separate fresh worktrees made from that exact candidate commit, so agent-created ignored files cannot inflate the accepted score. It stops at the target or an explicit iteration, time, stagnation, or authorization limit. Your original branch is not merged, reset, or published.

### 1. Prepare the project

You need Python 3.11+, Git, Linux `bubblewrap`, the selected agent CLI and its account, the project's gate tools, and an evaluator maintained **outside** the editable checkout. The evaluator must write JSON to stdout with `schema_version: 1`, the configured metric/value/unit/direction, passing `checks`, and evidence files under `DW_REPORT_DIR`. Its approved SHA-256 is checked before execution. See the [evaluator contract](docs/goal-loop-model-routing-spec.md#4-contratos-de-dados-e-interface-proposta).

Keep your project's existing gate `[commands]` and add the following to its `.dev-workflows.toml`. This example uses an explicitly chosen, **unranked** Claude subscription alias; it does not invent an Artificial Analysis score or a per-token subscription price.

```toml
[loop]
enabled = false # set true only when you authorize a run
harness = "claude"
tier = 1       # localized change; raise the tier for larger/riskier work
max_iterations = 3
max_minutes = 30
max_stagnant = 2
min_improvement = 1
max_paid_usd = 0

[loop.goal]
name = "app_quality"
unit = "points"
direction = "maximize"
target = 80

[loop.evaluator]
argv = ["python3", "/absolute/outside/checkout/evaluate.py"]
trusted_sha256 = "<paste the evaluator's 64-character SHA-256>"
required_checks = ["test", "lint"]

[models.roles.implementer]
model_key = "sonnet"
billing_mode = "claude_subscription"
manual_unranked_approval = true
```

Replace the path, digest, goal, and limits with values you have reviewed. Confirm the digest with `sha256sum /absolute/outside/checkout/evaluate.py`; required checks must be configured and available in the app. A higher tier can require additional agent roles and gate tools. **The example is not ready to run until its placeholders are replaced and `enabled` is set deliberately.**

### 2. Plan, run, inspect

From the **app checkout** (not this repository), set `DW` to this repository's absolute path:

```bash
DW=/absolute/path/to/dev-workflows
python3 "$DW/scripts/goal_loop.py" plan --config .dev-workflows.toml

# Review the plan; then set enabled = true and commit the app config.
python3 "$DW/scripts/goal_loop.py" run --config .dev-workflows.toml

# Copy run_id from the run's JSON output into RUN_ID.
RUN_ID=your-run-id
python3 "$DW/scripts/goal_loop.py" status --config .dev-workflows.toml --run "$RUN_ID"
python3 "$DW/scripts/goal_loop.py" resume --config .dev-workflows.toml --run "$RUN_ID"
python3 "$DW/scripts/goal_loop.py" stop --config .dev-workflows.toml --run "$RUN_ID"
```

`plan` preflights the evaluator, isolation, gate, and routes without calling an agent. `run` evaluates the same goal from baseline through each attempt; a current `pass` gate and required checks must precede acceptance. `status` reports baseline, best score, target, attempts, gate and evidence. `resume` rechecks the configuration, evaluator, gate, base, and model route; a paid call with unreported usage cannot be resumed automatically. `stop` prevents subsequent attempts rather than killing an in-flight call.

State and evidence live outside the app at `$XDG_STATE_HOME/dev-workflows` (by default `~/.local/state/dev-workflows`). Inspect the winning worktree and commit before **you** decide whether to apply its diff. The controller never applies or publishes it for you.

## Model catalog and routing

Catalog commands inspect sources and local account evidence; they **do not dispatch models**:

```bash
# Run these from the dev-workflows repository.
python3 scripts/model_catalog.py sync --tool opencode --providers opencode,opencode-go
python3 scripts/model_catalog.py list --tool opencode --show-missing --format csv
python3 scripts/model_catalog.py route --tool opencode --role planner \
  --providers opencode,opencode-go --explain

# For configured OMP providers, discover their local models instead:
python3 scripts/model_catalog.py sync --tool omp --providers your-provider
```

| Evidence | Source | Meaning |
|---|---|---|
| Model IDs and variants | Public [Zen](https://opencode.ai/zen/v1/models) and [Go](https://opencode.ai/zen/go/v1/models) catalogs; local tool discovery | A public listing or local login alone **does not prove** entitlement. Zen and Go are distinct billing routes. |
| Comparative prices | [OpenRouter Models API](https://openrouter.ai/api/v1/models) | USD/token, displayed in USD/1M for matched IDs; published long-context overrides affect reference costs. These are **not** Zen, Go, or Claude billing. Missing cache components are `n/d`, never zero. |
| Coding scores | Authorized, attributed [Artificial Analysis Coding Agent Index](https://artificialanalysis.ai/agents/coding-agents) v1.5 snapshot | Manual audited import only; exact scores require a matching runtime harness and model effort. Cross-harness scores require explicit proxy approval. No automatic scraping or borrowed Intelligence Index scores. |
| Eligibility and native cost | Your audited account evidence, native tariffs, balances, and Go quotas | Required for paid/eligible routing; missing or stale evidence blocks automatic selection. |

Fixed coding-score bands are **light `[10,20)`**, **medium `[20,50)`**, and **high `[50,100]`**. The router filters by tool, provider, account, evidence, role, and budget, then compares real native cost inside the best-score plateau; OpenRouter prices remain reference only. An empty band stays empty rather than acquiring a fabricated score. A manually fixed Claude alias is labeled `unranked`.

To supply your own authorized data, `sync` accepts `--aa-snapshot`, `--availability-snapshot`, and `--price-overrides` (including `native_tariffs`). See the [validated input contracts](docs/goal-loop-model-routing-spec.md#4-contratos-de-dados-e-interface-proposta). A paid `route` also needs a task token profile (`--tokens`), explicit providers, and an appropriate `--budget-usd`; routing alone never makes a paid call.

### Reproducible public snapshot

The [captured CSV](docs/model-catalog-zen-go-2026-09-25.csv) contains **122 public models** from 2026-09-25 07:18:38 UTC: 80 Zen, 42 Go, eight curated OpenRouter price matches, **0/122 licensed AA scores imported**, and no locally confirmed account eligibility. It is a catalog, **not** a recommendation or invoice. Reproduce its exact bytes offline from the [archived normalized JSON snapshot](docs/model-catalog-snapshot-2026-09-25/catalog-opencode.json):

```bash
python3 scripts/model_catalog.py list --tool opencode --show-missing --format csv \
  --cache-dir docs/model-catalog-snapshot-2026-09-25 \
  --as-of-utc 2026-09-25T07:18:38Z
```

The CSV output SHA-256 is `80e2930877b20e5c47d4fd18f394c17a4683b257ca715496e91c63520d528230`; the archived JSON SHA-256 is `a5a1ec44587976a9fe96399bb275662ccdf90e1d8149ac7857f03ae05bb83dcc`. A new `sync` obtains **current** catalogs and may yield different rows or prices. With no authorized benchmark or confirmed account evidence, `route` reports no eligible scored model rather than pretending one is available.

## Safety and limitations

- **No implicit spending.** Zen and pay-as-you-go routes require an explicit task budget; dispatch needs recent audited balance and native prices, a nonzero cap, a task estimate, and interactive authorization before each call. Go checks the three per-model quota windows (5h, weekly, monthly) and does not silently fall back to paid Zen balance. Unknown real usage pauses the loop and blocks automatic resume; an estimate is **not a hard billing limit**. Claude subscriptions are not converted into fictional USD/token costs.
- **Isolation has boundaries.** The evaluator and quality gate run under Linux `bubblewrap` without network access. The agent CLI can edit its isolated worktree but its `.git` pointer is mounted read-only and rechecked before Git writes; it retains network access for providers and can read host files. This is **not** provider-only egress isolation. Add stronger isolation before using sensitive code or data.
- **Evidence beats agent output.** Missing tools, failed or stale gates, invalid evaluator results, changed protected files, and unavailable models do not count as success. No install, merge, publish, destructive Git operation, or cleanup of winning worktrees is performed by the loop.
- **No measured quality uplift claim.** The CLI was exercised on a disposable app with a fake Claude CLI and fake scanner: the app score moved from **0 to 2 in two gate-approved iterations**, without paid inference or a real account entitlement check. Whether the kit improves agent-produced code across projects still needs an A/B benchmark; public [SkillsBench](https://arxiv.org/abs/2602.12670) and [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) results show skills are not automatically beneficial.

## Verify this repository

```bash
python3 qa/lint_skills.py
python3 qa/test_gate.py
python3 -m unittest discover -s qa -p 'test_*.py' -q
claude plugin validate --strict .claude-plugin/plugin.json
```

CI runs skill lint, gate/hook tests, and the behavioral suite on every PR. `python3 qa/check_upstream.py` checks vendored skills against upstream separately each month. See the [changelog](CHANGELOG.md) and the [full goal-loop specification](docs/goal-loop-model-routing-spec.md) for contracts, requirements, and limitations.

## Repository map

| Path | Purpose |
|---|---|
| `skills/`, `agents/`, `hooks/` | Canonical workflows, least-privilege agents, Claude hooks |
| `scripts/quality-gate`, `scripts/install.py` | Deterministic verification and installation |
| `scripts/model_catalog.py`, `scripts/model_router.py` | Provenance-aware inventory and per-role selection |
| `scripts/goal_loop.py`, `scripts/harness_runner.py` | External controller and runtime invocation |
| `adapters/opencode/`, `adapters/omp/` | Native integration packages |
| `qa/`, `docs/` | Behavioral tests, source inventory, specification, captured data |

## License

[MIT](LICENSE) © 2026 [Evandro Fonseca Junior](https://github.com/evandrodevbr). Vendored skills retain their own licenses; see [`skills/NOTICE.md`](skills/NOTICE.md).
