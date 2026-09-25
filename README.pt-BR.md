<div align="center">

# Dev Workflows

**Plugin do Claude Code (também para opencode e Hermes Agent) que ajusta o processo ao tamanho do pedido**: um roteador escolhe o nível, agentes com permissão mínima fazem o trabalho e um gate de qualidade determinístico decide quando terminou.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-1.0-8A2BE2)](https://agentskills.io)
[![CI](https://github.com/evandrodevbr/dev-workflows/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)

**🇺🇸 [Read in English](README.md)**

</div>

---

## Por quê

Agentes escrevem código rápido e erram em duas coisas: saber quando uma tarefa merece mais processo
e admitir o que não verificaram. Este plugin cuida das duas:

- **Processo proporcional ao pedido.** Typo não passa por revisão de design; mudança de auth passa.
- **Prova, não afirmação.** "Pronto" exige um relatório do gate sobre o diff atual. Ferramenta não instalada aparece como *não verificado*, nunca como aprovada.
- **Menos código.** Reaproveitar antes de escrever, apagar antes de somar, nenhuma dependência sem motivo.
- **Segurança com fontes ao vivo.** O conhecimento de CVEs de um modelo para na data de treino, então as revisões consultam o OSV.dev e registram a data.

## Como funciona

O `dev-router` carrega primeiro e declara um nível:

| Nível | Quando | O que roda |
|---|---|---|
| 0, trivial | nenhum comportamento muda | a mudança + gate nível 0 |
| 1, pequeno | 1 a 3 arquivos, sem superfície pública nova | `wf-bugfix` ou `wf-refactor`, teste de regressão, gate nível 1 |
| 2, feature | endpoint ou tela nova, contrato alterado, dependência nova | exploração, plano curto, TDD, revisão independente, gate nível 2 |
| 3, grande ou de risco | vários módulos, dados existentes, arquitetura, release | spec EARS + ADR aprovados por você, revisões, auditoria de segurança, gate nível 3 |

Gatilhos de segurança sobem o nível a qualquer momento: auth, dinheiro, dados pessoais, upload, SQL
montado à mão, shell/exec, desserialização, migração de schema, dependência nova, feature que chama LLM.

## O que tem dentro

| Tipo | Itens |
|---|---|
| Roteador e regras | `dev-router`, `lean-code` |
| Workflows | `wf-bugfix`, `wf-refactor`, `wf-frontend`, `wf-backend`, `wf-architecture`, `wf-security-review`, `wf-readme` |
| Agentes | `explorer` (haiku, só leitura), `planner` (opus, só leitura), `implementer` (sonnet), `reviewer` (opus, só leitura, vê só o diff), `security-auditor` (opus, só leitura), `ui-critic` (sonnet, só leitura), `verifier` (haiku, roda o gate) |
| Hooks | `Stop`: bloqueia o "pronto" enquanto houver código alterado sem gate atual aprovado · `PreToolUse`: nega `--no-verify` e force-push, pergunta antes de `reset --hard`, `clean -f`, `DROP TABLE` · `PostToolUse`: formata o arquivo editado com o formatter do próprio projeto |
| Gate de qualidade | [`scripts/quality-gate`](scripts/quality-gate): lint, typecheck, testes, gitleaks (nível 0); cobertura do diff, semgrep, código morto (nível 1); build, teste de mutação, osv-scanner, regras de arquitetura, duplicação (nível 2); trivy, rastreabilidade requisito→teste (nível 3) |
| Skills vendorizadas | pilar de segurança (OWASP secure-agent-playbook, UnitOneAI SecuritySkills, safedeps, hermaguard) e taste-skill para frontend. Origem e licença: [`skills/NOTICE.md`](skills/NOTICE.md) |

O gate roda só as checagens do nível pedido, só sobre o diff, e não usa IA: são ferramentas comuns.
Checagens que precisam do app de pé (orçamento do Lighthouse CI, Playwright + axe, schemathesis, k6)
entram por projeto no `.dev-workflows.toml`. Referência:
[`skills/dev-router/references/quality-gate.md`](skills/dev-router/references/quality-gate.md).

## Instalação

```bash
git clone https://github.com/evandrodevbr/dev-workflows && cd dev-workflows

python3 scripts/install.py claude     # plugin: skills + agentes + hooks
python3 scripts/install.py opencode   # skills, agentes e plugin em ~/.config/opencode
python3 scripts/install.py hermes     # só skills, em ~/.hermes/skills
```

Claude Code sem clonar:

```text
/plugin marketplace add evandrodevbr/dev-workflows
/plugin install dev-workflows@dev-workflows
```

Diferenças entre os agentes:

- **opencode** não consegue bloquear o fim do turno, então gate ausente ou falho vira aviso no log em vez de bloqueio. Os agentes viram subagentes do opencode com as mesmas permissões.
- **Hermes** recebe só as skills; rode o gate você mesmo.
- No opencode e no Hermes as cópias apontam para o seu clone: mantenha-o no lugar (ou rode a instalação de novo depois de mover).

Desligue o hook de `Stop` numa sessão com `DW_GATE=off`.

## Skills externas (opcionais)

Os workflows usam estas quando instaladas e seguem as próprias regras quando não. Comandos de
instalação: [`docs/SKILLS.md`](docs/SKILLS.md).

| Área | Skills |
|---|---|
| Frontend | `frontend-design` (Anthropic), `impeccable` (pbakaus), `vercel-react-best-practices`, `vercel-composition-patterns` (Vercel Labs), `animate` (emilkowalski), `web-design`, `avoid-ai-writing` |
| Backend | `secure-coding`, `bola-detector`, `auth-rbac-scaffold`, `injection-checker`, `openapi-hardener`, `security-test-generator` (apisec-inc) |
| Arquitetura | `system-design`, `c4-architecture`, `isaqb-architecture-governance`, `secure-architecture-governance` (Kotivskyi) |
| README | `readme-crafter`, `good-readme`, `curating-readme` |

## Qualidade deste repositório

```bash
python3 qa/lint_skills.py      # frontmatter, limites de tamanho, referências, links, caminhos de máquina
python3 qa/test_gate.py        # gate e hooks num repositório descartável
python3 qa/check_upstream.py   # skills vendorizadas atrás do upstream
claude plugin validate --strict .claude-plugin/plugin.json
```

O CI roda os dois primeiros em todo PR; a checagem de upstream roda todo mês.

**Ainda não medido:** se o kit melhora o código que um agente produz. Estudos públicos
([SkillsBench](https://arxiv.org/abs/2602.12670), [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401))
mostram que skills também podem piorar o resultado, então o próximo passo é um benchmark A/B (com e
sem o kit) no [Harbor](https://github.com/harbor-framework/harbor), com testes ocultos, score de
mutação e checagens de segurança.

## Estrutura

```
.claude-plugin/     plugin.json, marketplace.json
skills/             dev-router, lean-code, workflows wf-*, skills vendorizadas (NOTICE.md)
agents/             explorer, planner, implementer, reviewer, security-auditor, ui-critic, verifier
hooks/hooks.json    Stop, PreToolUse, PostToolUse
scripts/            quality-gate, install.py, hooks/*.py
adapters/opencode/  plugin do opencode
qa/                 lint, testes do gate, checagem de upstream
docs/SKILLS.md      inventário de skills e comandos de instalação
```

## Licença

[MIT](LICENSE) © 2026 [Evandro Fonseca Junior](https://github.com/evandrodevbr). As skills vendorizadas mantêm as próprias licenças ([`skills/NOTICE.md`](skills/NOTICE.md)).
