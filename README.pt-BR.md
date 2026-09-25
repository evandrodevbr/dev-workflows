<div align="center">

# Dev Workflows

**Plugin do Claude Code (também para OpenCode e OMP; Hermes recebe só skills) que ajusta o processo ao tamanho do pedido**: um roteador escolhe o nível, agentes com permissão mínima fazem o trabalho e um gate de qualidade determinístico decide quando terminou.

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
python3 scripts/install.py omp        # pacote nativo OMP: skills + agentes (sem hooks Claude)
```

Claude Code sem clonar:

```text
/plugin marketplace add evandrodevbr/dev-workflows
/plugin install dev-workflows@dev-workflows
```

Diferenças entre os agentes:

- **OpenCode** não consegue bloquear o fim do turno, então gate ausente ou falho vira aviso no log. Seus subagentes têm ferramentas negadas por padrão; o controlador externo verifica o gate por conta própria.
- **OMP** usa plugin nativo com skills e sete agentes, sem hooks Claude. O controlador externo impõe o gate.
- **Hermes** recebe só as skills; rode o gate você mesmo. Não existe executor Hermes para o loop.
- No OpenCode e no Hermes as cópias apontam para o seu clone: mantenha-o no lugar (ou reinstale depois de mover). O pacote OMP é construído independentemente do clone.

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
python3 -m unittest discover -s qa -p 'test_*.py' -q  # catálogo, roteador, adapters, loop
python3 qa/check_upstream.py   # skills vendorizadas atrás do upstream
claude plugin validate --strict .claude-plugin/plugin.json
```

O CI roda lint, testes do gate/hooks e a suíte comportamental em todo PR; a checagem de upstream roda todo mês.

**Ainda não medido:** se o kit melhora o código que um agente produz. Estudos públicos
([SkillsBench](https://arxiv.org/abs/2602.12670), [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401))
mostram que skills também podem piorar o resultado, então o próximo passo é um benchmark A/B (com e
sem o kit) no [Harbor](https://github.com/harbor-framework/harbor), com testes ocultos, score de
mutação e checagens de segurança.

## Catálogo de modelos e loop de meta opt-in

A [spec de roteamento e loop](docs/goal-loop-model-routing-spec.md) está implementada em CLIs independentes; instalar um plugin **nunca inicia o loop**. Requisitos: Python 3.11+, Git, `bubblewrap` no Linux, CLI de agente suportada configurada, avaliador externo aprovado, checkout limpo e ferramentas do gate do projeto. Não rode em projetos sensíveis sem isolamento adicional: a CLI do agente pode acessar a rede e ler arquivos do host; **não** há sandbox de rede restrita só ao provider. Avaliador e gate rodam sem acesso à rede.

Para inspecionar modelos sem chamar nenhum deles (neste repositório):

```bash
python3 scripts/model_catalog.py sync --tool opencode --providers opencode,opencode-go
python3 scripts/model_catalog.py list --tool opencode --show-missing --format csv
python3 scripts/model_catalog.py route --tool opencode --role planner --providers opencode,opencode-go --explain
```

`sync` consulta fontes públicas [Zen](https://opencode.ai/zen/v1/models), [Go](https://opencode.ai/zen/go/v1/models), [OpenRouter](https://openrouter.ai/api/v1/models) e `opencode models <provider> --refresh` local; para OMP, passe `--tool omp --providers <provider-configurado>` para descobrir modelos locais. Lista, login armazenado ou tarifa OpenRouter **não comprovam** acesso da conta, cota Go, saldo Zen ou cobrança real. Rota pontuada elegível exige seus próprios `--availability-snapshot` e `--aa-snapshot` auditados; para cobranças/cotas nativas, `--price-overrides` com `native_tariffs`. Veja os [contratos](docs/goal-loop-model-routing-spec.md#4-contratos-de-dados-e-interface-proposta) e validadores de `scripts/model_catalog.py`. O Coding Agent Index v1.5 da AA é importado manualmente, com autorização e atribuição: sem scraping da leaderboard ou notas inventadas. Faixas fixas de nota de código: `[10,20)`, `[20,50)`, `[50,100]`; modelos inacessíveis ou sem nota não vencem uma rota pontuada. Preços OpenRouter em USD/1M são **comparativos**, não cobrança Zen/Go/Claude; cache ausente é `n/d`, não gratuito.
Uma nota `exact` exige o mesmo harness e esforço de execução; outro harness só entra como `proxy` autorizado. No OMP, apenas esforços `thinking` anunciados pelo modelo local são elegíveis, inclusive IDs de modelo com `/`. Overrides públicos de contexto longo do OpenRouter entram no custo **referencial** do perfil de tokens.

A [tabela CSV completa capturada](docs/model-catalog-zen-go-2026-09-25.csv) inclui **122 modelos públicos** (Zen 80, Go 42) em 2026-09-25 07:18:38 UTC: **0/122 notas AA licenciadas importadas**, oito pareamentos de preço OpenRouter curados e nenhum acesso de conta confirmado localmente nesta captura. Reproduza **exatamente estes bytes, sem rede**, usando o [snapshot normalizado arquivado](docs/model-catalog-snapshot-2026-09-25/catalog-opencode.json) com `python3 scripts/model_catalog.py list --tool opencode --show-missing --format csv --cache-dir docs/model-catalog-snapshot-2026-09-25 --as-of-utc 2026-09-25T07:18:38Z`; o SHA-256 da saída é `80e2930877b20e5c47d4fd18f394c17a4683b257ca715496e91c63520d528230`. Sem `--as-of-utc`, o relatório de obsolescência usa o horário atual. Rode `sync` e `list --format csv` para catálogos/preços *atuais*. Dados públicos não são fatura nem garantia de acesso.

No `.dev-workflows.toml` **do aplicativo**, preserve seus `[commands]` do gate e defina um avaliador independente mantido fora do checkout. O stdout deve ser JSON com `schema_version: 1`, métrica/valor/unidade/direção configuradas, `checks` aprovados e evidências geradas sob `DW_REPORT_DIR` (veja o [contrato do avaliador](docs/goal-loop-model-routing-spec.md#4-contratos-de-dados-e-interface-proposta)). Exemplo com assinatura Claude e alias fixo, deliberadamente **sem ranking**:

```toml
[loop]
enabled = false # mude para true apenas quando decidir executar
harness = "claude"
tier = 1 # mudança de comportamento pequena; aumente para tarefas de risco
max_iterations = 3
max_minutes = 15
max_stagnant = 2
min_improvement = 1
max_paid_usd = 0

[loop.goal]
name = "app_quality"
unit = "points"
direction = "maximize"
target = 80

[loop.evaluator]
argv = ["python3", "/caminho/absoluto/fora/do/checkout/evaluate.py"]
trusted_sha256 = "<cole os 64 caracteres do SHA-256 do avaliador>"
required_checks = ["test", "lint"]

[models.roles.implementer]
model_key = "sonnet"
billing_mode = "claude_subscription"
manual_unranked_approval = true
```

Aprove o arquivo/hash do avaliador (`sha256sum /caminho/absoluto/fora/do/checkout/evaluate.py`), defina meta mensurável e comandos do gate. Depois, **num checkout limpo do app** (troque `DW` pelo caminho absoluto deste repositório):

```bash
DW=/caminho/absoluto/para/dev-workflows
python3 "$DW/scripts/goal_loop.py" plan --config .dev-workflows.toml
# Mude enabled = true no app, faça commit dessa escolha deliberada e então:
python3 "$DW/scripts/goal_loop.py" run --config .dev-workflows.toml
python3 "$DW/scripts/goal_loop.py" status --config .dev-workflows.toml --run <run-id>
python3 "$DW/scripts/goal_loop.py" resume --config .dev-workflows.toml --run <run-id>
python3 "$DW/scripts/goal_loop.py" stop --config .dev-workflows.toml --run <run-id>
```

`plan` não chama agentes; `run` mede o score inicial do app e tenta mudanças em worktrees separados. Cada tentativa cria um commit candidato detached; o gate e o avaliador executam em cópias limpas e separadas desse commit, sem arquivos ignorados criados pelo agente. Só aceita melhora após gate `pass` atual, checks obrigatórios e avaliação independente. Não faz merge, publicação ou exclusão da sua branch/worktrees; inspecione `status` e o worktree/commit vencedor antes de decidir aplicar. Estado/evidências ficam em `$XDG_STATE_HOME/dev-workflows` (padrão `~/.local/state/dev-workflows`). `resume` revalida configuração/avaliador/gate/base/rota; `stop` solicita parar novas tentativas, sem interromper imediatamente uma chamada em andamento. Zen/pay-as-you-go requer auditoria recente de conta/saldo, estimativa nativa, orçamento explícito e positivo **e** autorização interativa antes de cada chamada; consumo real desconhecido pausa o loop e impede retomada automática, pois estimativas não são limite rígido de cobrança. Go exige cotas recentes por modelo para 5h/semana/mês, sem fallback para saldo Zen. Assinatura Claude **não** recebe custo fictício USD/token nem nota AA emprestada do alias.

## Estrutura

```
.claude-plugin/     plugin.json, marketplace.json
skills/             dev-router, lean-code, workflows wf-*, skills vendorizadas (NOTICE.md)
agents/             explorer, planner, implementer, reviewer, security-auditor, ui-critic, verifier
hooks/hooks.json    Stop, PreToolUse, PostToolUse
scripts/            quality-gate, instalação, catálogo/roteador, loop, executores e hooks
adapters/opencode/  plugin do OpenCode
adapters/omp/       construtor do pacote nativo OMP
qa/                 lint, testes do gate e de integração, checagem de upstream
docs/SKILLS.md      inventário de skills e comandos de instalação
```

## Licença

[MIT](LICENSE) © 2026 [Evandro Fonseca Junior](https://github.com/evandrodevbr). As skills vendorizadas mantêm as próprias licenças ([`skills/NOTICE.md`](skills/NOTICE.md)).
