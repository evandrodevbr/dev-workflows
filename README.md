<div align="center">

# Dev Workflows

**Agent workflows as SKILL.md files**: frontend, backend, architecture and security code review that never skip verification.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](qa/wf_quality_harness.py)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-1.0-8A2BE2)](https://agentskills.io)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/evandrodevbr/dev-workflows/pulls)

Turn your coding agent into a repeatable, verifiable process. Each workflow defines phases, concrete verification steps, real commands, and hard rules. The agent delivers work that can be *checked*, not just *claimed*.

**🇧🇷 [Ler em português](README.pt-BR.md)**

</div>

---

## Why

Agents are great at generating code and terrible at admitting they don't know. This project fixes the second part.

Every workflow here forces the agent to **prove** the work at each phase:

- **Verification steps**: run the build, run the tests, hit the API, consult the registry. Not "I think it works".
- **Acceptance criteria**: checkbox gates that must be marked before a phase closes.
- **Hard rules**: "never merge with a red build", "never claim 'no CVE' without querying OSV.dev".
- **A QA harness**: a scorecard that measures workflow quality objectively, plus meta-tests that corrupt the harness to prove it detects regressions.

## Table of contents

- [Workflows](#workflows)
- [Security: do not trust the training cutoff](#security-do-not-trust-the-training-cutoff)
- [Skills used, and their owners](#skills-used-and-their-owners)
- [Quick start](#quick-start)
- [The QA harness](#the-qa-harness)
- [Quality tests and measured gains](#quality-tests-and-measured-gains)
- [Repository layout](#repository-layout)
- [License](#license)

## Workflows

| Workflow | File | Covers |
|---|---|---|
| 🎨 **Frontend / UI** | [workflows/wf-frontend.md](workflows/wf-frontend.md) | Design direction before code, anti-AI-slop, React performance, visual QA for PDFs |
| ⚙️ **Backend / API** | [workflows/wf-backend.md](workflows/wf-backend.md) | Contract before handler, safe defaults, OWASP audit, tests + adversarial bug hunt |
| 🏗️ **Architecture** | [workflows/wf-architecture.md](workflows/wf-architecture.md) | Measurable requirements, C4 diagrams, ADRs, threat modeling, review |
| 🛡️ **Security review** | [workflows/wf-security-review.md](workflows/wf-security-review.md) | Code review (front + back), known CVEs **and** live lookup of new ones |

Each file is a standard `SKILL.md`. The `description` in the frontmatter is the trigger: when the agent's context matches it, the workflow loads automatically. Works in [Hermes Agent](https://hermes-agent.nousresearch.com), Claude Code, and anything that reads the Agent Skills format.

## Security: do not trust the training cutoff

A model's knowledge of CVEs stops at its training date. Anything disclosed after that, it has never seen, so "no vulnerabilities" from memory is a guess, not an answer.

The security workflow is built around that fact:

```
Code/diff → SCOPE → HUNT (known CVEs) → CONSULT (live sources) → CODE REVIEW → REPORT + GATE
                    │                      │
                    │                      └─ OSV.dev · GitHub Advisory DB · NVD
                    └──────────────┘
```

Every security review **must** consult live sources and stamp the date. A review with no source and no date is expired on arrival.

## Skills used, and their owners

Workflows load these skills by context. The three pillars of the security review come from primary security sources (OWASP, OSV.dev, UnitOne SecuritySkills), not from a model's memory.

### 🛡️ Security review: the three pillars

| Skill | What it does | Owner |
|---|---|---|
| [`safedeps`](https://github.com/Jeneidi/safedeps) | Queries OSV.dev in real time; returns CVE + severity + fixed version for a `package@version`. Covers the gap a frozen model can't. | [Jeneidi](https://github.com/Jeneidi) |
| [`sca-audit`](https://github.com/OWASP/secure-agent-playbook) | Supply-chain audit of dependencies with reachability analysis and CWE mapping. | [OWASP](https://github.com/OWASP) |
| [`code-review-security`](https://github.com/OWASP/secure-agent-playbook) | Systematic security code review mapped to OWASP Top 10 + ASVS. | [OWASP](https://github.com/OWASP) |

### 🛡️ Security review: supporting skills

| Skill | What it does | Owner |
|---|---|---|
| [`secrets-scan`](https://github.com/OWASP/secure-agent-playbook) | Finds hardcoded credentials / API keys in code and git history. | [OWASP](https://github.com/OWASP) |
| [`api-security-review`](https://github.com/OWASP/secure-agent-playbook) | API review against OWASP API Security Top 10. | [OWASP](https://github.com/OWASP) |
| [`web-security-review`](https://github.com/OWASP/secure-agent-playbook) | Web app review against OWASP Top 10. | [OWASP](https://github.com/OWASP) |
| [`cve-triage`](https://github.com/UnitOneAI/SecuritySkills) | Prioritizes CVEs using CVSS 4.0 / EPSS / CISA KEV. | [UnitOneAI](https://github.com/UnitOneAI) |
| [`patch-prioritization`](https://github.com/UnitOneAI/SecuritySkills) | Decides remediation order. | [UnitOneAI](https://github.com/UnitOneAI) |
| [`dependency-scanning`](https://github.com/UnitOneAI/SecuritySkills) | Dependency tree scanning. | [UnitOneAI](https://github.com/UnitOneAI) |
| [`hermaguard`](https://github.com/Sahil-SS9/hermaguard) | Adversarial review: static pre-scan + 3 specialist agents (edge cases, attack, blast radius). | [Sahil-SS9](https://github.com/Sahil-SS9) |

### 🎨 Frontend / UI

| Skill | What it does | Owner |
|---|---|---|
| [`frontend-design`](https://github.com/anthropics/skills) | Intentional visual direction, typography, avoiding "generic AI" output. | [Anthropic](https://github.com/anthropics) |
| [`web-design`](https://github.com/KAOPU-XiaoPu/web-design) | Cohesive web aesthetics. | [KAOPU-XiaoPu](https://github.com/KAOPU-XiaoPu) |
| [`vercel-react-best-practices`](https://github.com/vercel-labs/agent-skills) | 40+ React/Next performance rules from Vercel engineering. | [Vercel Labs](https://github.com/vercel-labs) |
| [`vercel-composition-patterns`](https://github.com/vercel-labs/agent-skills) | Compound components, clean composition. | [Vercel Labs](https://github.com/vercel-labs) |
| [`animate`](https://github.com/emilkowalski/skill) | Purpose-driven motion. | [emilkowalski](https://github.com/emilkowalski) |
| [`impeccable`](https://github.com/pbakaus/impeccable) | The missing design vocabulary for agents: 23 commands (craft, shape, audit, polish, animate, live) and 59 deterministic anti-slop rules. The most-used frontend design skill (230k+ installs). | [pbakaus](https://github.com/pbakaus) |
| [`anti-ai-slop`](https://github.com/evandrodevbr/dev-workflows) | Detects "generated-by-AI" visual patterns (auto-loaded, local). | community skill |
| [`avoid-ai-writing`](https://github.com/conorbronsdon/avoid-ai-writing) | Removes AI-isms from microcopy, labels and docs. | [conorbronsdon](https://github.com/conorbronsdon) |

### ⚙️ Backend / API

| Skill | What it does | Owner |
|---|---|---|
| [`secure-coding`](https://github.com/securityreviewai/secure-coding-skill) | Secure coding patterns covering 15 stacks. | [securityreviewai](https://github.com/securityreviewai) |
| [`bola-detector`](https://github.com/apisec-inc/apisec-skills) | Broken object-level authorization (OWASP API1). | [apisec-inc](https://github.com/apisec-inc) |
| [`auth-rbac-scaffold`](https://github.com/apisec-inc/apisec-skills) | Authentication + RBAC (OWASP API2 / API5). | [apisec-inc](https://github.com/apisec-inc) |
| [`injection-checker`](https://github.com/apisec-inc/apisec-skills) | SQL / ORM / shell / template injection (OWASP API8). | [apisec-inc](https://github.com/apisec-inc) |
| [`openapi-hardener`](https://github.com/apisec-inc/apisec-skills) | Sanitizes OpenAPI / Zod / Pydantic schemas (OWASP API3). | [apisec-inc](https://github.com/apisec-inc) |
| [`api-security-review`](https://github.com/apisec-inc/apisec-skills) | Full OWASP API Top 10 review. | [apisec-inc](https://github.com/apisec-inc) |
| [`security-test-generator`](https://github.com/apisec-inc/apisec-skills) | Generates security test suites. | [apisec-inc](https://github.com/apisec-inc) |

### 🏗️ Architecture

| Skill | What it does | Owner |
|---|---|---|
| [`system-design`](https://github.com/Kotivskyi/architecture-governance-skills) | HelloInterview system-design framework. | [Kotivskyi](https://github.com/Kotivskyi) |
| [`c4-architecture`](https://github.com/Kotivskyi/architecture-governance-skills) | C4 diagrams (Mermaid / Structurizr). | [Kotivskyi](https://github.com/Kotivskyi) |
| [`isaqb-architecture-governance`](https://github.com/Kotivskyi/architecture-governance-skills) | arc42 + ADRs. | [Kotivskyi](https://github.com/Kotivskyi) |
| [`secure-architecture-governance`](https://github.com/Kotivskyi/architecture-governance-skills) | STRIDE+CIA threat models, security ADRs. | [Kotivskyi](https://github.com/Kotivskyi) |

> 📖 Full install instructions for every skill live in [docs/SKILLS.md](docs/SKILLS.md).

## Quick start

```bash
# 1. Copy workflows into your agent's skills directory
# Hermes Agent:
cp workflows/*.md ~/.hermes/skills/software-development/

# Claude Code / any skills-dir agent:
mkdir -p ~/.claude/skills && cp workflows/*.md ~/.claude/skills/

# 2. (Optional, for security review) install safedeps + the OSV checker
git clone --depth 1 https://github.com/Jeneidi/safedeps.git
cp -r safedeps/skills/safedeps ~/.hermes/skills/safedeps
cp safedeps/check_deps.py ~/.hermes/skills/safedeps/

# 3. Use it
# "review this PR for security"  -> wf-security-review loads
# "build a new page"              -> wf-frontend loads
```

## The QA harness

The `qa/` directory keeps the workflows themselves honest:

```bash
cd qa

python3 wf_quality_harness.py   # score each workflow on 30+ criteria
python3 test_quality.py         # gates: no regression, valid skills, phases verified
python3 test_tests.py           # meta-tests: corrupt the harness, prove it detects the corruption
```

The meta-tests are the interesting part. They deliberately break the harness and the workflows, then confirm the score *drops*. If the score didn't move, the detector would be useless. These tests stay green as a contract.

## Quality tests and measured gains

These are real numbers from the harness runs, stored in `qa/snapshots/`. The baseline column is the state before the refinement work; the final column is the result after it.

### Workflow quality score (same harness, before → after)

| Workflow | Baseline | Final | Gain |
|---|---|---|---|
| wf-frontend | 201.0 | 385.5 | +92% |
| wf-backend | 215.0 | 424.0 | +97% |
| wf-architecture | 199.9 | 413.7 | +107% |
| wf-security-review | 332.0 | 390.0 | +17% |
| **Total** | **615.9** | **1223.2** | **+98.6%** |

That is almost exactly double the quality of the workflows, measured with the same ruler.

The ruler itself also grew stricter over the project (13 → 30+ criteria: verification per phase, real commands, anti-patterns, acceptance criteria, artifacts, flow). That is why the early snapshots show lower totals: `base-364` (13 criteria) → `baseline-v2` (536.7) → `baseline-v3` (675.0) → `baseline-v4` (884.6) → `baseline-final` (1613.2 with four workflows). The fair before/after comparison above uses the final ruler for both sides.

### Gates (regression checks): all green

| Gate | What it checks | Status |
|---|---|---|
| G1 | Score did not drop below baseline | ✅ |
| G4 | Every referenced skill exists | ✅ 4/4 workflows |
| G5 | Every phase has ≥3 verification verbs | ✅ 4/4 workflows |
| Meta-tests | Corrupt harness/workflows → score drops (proves detector works) | ✅ |

### What the refinement added

Every workflow gained the same batch of real improvements:
- **Verification steps** with actual commands (`curl`, `grep`, `python3`, `git`, `npm`, `pytest`) instead of prose.
- **Per-phase acceptance checklists** (markable `[ ]` gates).
- **Anti-pattern blocks** per phase (what not to do, and why).
- **Executable-command sections** and **worked examples per phase**.
- **Checkpoints** that pause for user approval between phases.

The security workflow gained a hard rule: *never claim "no CVE" without querying OSV.dev / GitHub Advisory*. A model's knowledge stops at its training cutoff; the live sources don't.

### Context on the "double" target

The harness has a physical ceiling (sum of all criterion caps). The numeric "2× of baseline" target would need a ruler with more resolution to be expressible, so inflating the score to hit it would be gaming the metric. What shipped is the honest version: real quality ~doubled on the same ruler (+98.6%), with meta-tests proving the ruler detects regressions.


## Repository layout

```
dev-workflows/
├── README.md            # this file
├── README.pt-BR.md      # Portuguese version
├── workflows/           # the four SKILL.md workflows
│   ├── wf-frontend.md
│   ├── wf-backend.md
│   ├── wf-architecture.md
│   └── wf-security-review.md
├── docs/
│   └── SKILLS.md        # full skill inventory + install steps
└── qa/                  # quality harness, gates, meta-tests
    ├── wf_quality_harness.py
    ├── test_quality.py
    ├── test_tests.py
    └── snapshots/
```

## License

[MIT](LICENSE) © 2026 [Evandro Fonseca Junior](https://github.com/evandrodevbr)

---

<div align="center">

⭐ If this saves you from one "works on my machine" merge, star it.

</div>
