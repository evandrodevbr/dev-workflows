---
name: dev-router
description: Use no início de qualquer pedido de código (feature, bug, refactor, UI, API, migração, review; "implement", "fix", "build", "add", "change"). Classifica o pedido em nível 0 a 3 e decide quais workflows, agentes e checagens rodar, para um pedido pequeno não pagar o custo de um grande.
---

# Dev Router

A primeira linha da resposta declara o nível: `Nível N: <motivo em uma frase>`.

## 1. Classificar

| Nível | Quando | Exemplos |
|---|---|---|
| 0, trivial | nenhum comportamento muda; 1 arquivo | texto, cor, typo, renomear variável local |
| 1, pequeno | comportamento muda em 1 a 3 arquivos, sem superfície pública nova | bug localizado, ajuste de validação, refactor local |
| 2, feature | superfície nova ou contrato alterado; 4+ arquivos; dependência nova | endpoint, tela, módulo, integração |
| 3, grande ou de risco | vários módulos ou serviços, dados existentes, arquitetura, release | migração com dados, troca de auth, novo serviço |

Na dúvida entre dois níveis, escolha o menor e suba quando aparecer um gatilho.

## 2. Gatilhos que sobem o nível a qualquer momento

| Gatilho | Mínimo | Soma |
|---|---|---|
| autenticação, autorização, sessão, tokens, criptografia | 2 | `security-auditor` |
| dinheiro, cobrança, dados pessoais (LGPD) | 2 | `security-auditor` |
| upload, SQL montado à mão, shell/exec, desserialização, template com entrada do usuário | 2 | `security-auditor` |
| dependência nova | 1 | `safedeps` antes de instalar |
| migração de schema | 2 (3 se mexe em dado existente) | rollback testado |
| feature que chama um LLM | 2 | OWASP LLM Top 10 no `security-auditor` |

Depois que um gatilho disparou, não rebaixe por conta própria.

O usuário pode forçar: "modo rápido" vira nível 0 ou 1, mas gatilho de segurança continua valendo (avise); "modo completo" vira nível 3.

## 3. O que cada nível roda

| Nível | Fluxo | Workflow | Agentes |
|---|---|---|---|
| 0 | fazer, rodar o gate | nenhum | nenhum |
| 1 | entender ou reproduzir, mudar, teste de regressão, gate | `wf-bugfix` ou `wf-refactor` | `explorer` só se não souber onde está o código |
| 2 | explorar, plano curto, TDD, revisão independente, gate | `wf-backend` e/ou `wf-frontend`; full-stack começa pelo contrato do backend | `explorer`, `implementer`, `reviewer`; `security-auditor` com gatilho; `ui-critic` com UI |
| 3 | spec EARS com IDs e ADR, aprovação do usuário, tarefas pequenas com TDD, revisões, gate | `wf-architecture` antes; `wf-backend`/`wf-frontend` na execução; `wf-security-review` no fim | `planner`, `implementer`, `reviewer`, `security-auditor`, `ui-critic` com UI, `verifier` |

Em todo nível: aplique `lean-code`. Peça aprovação do usuário só quando houver uma decisão que é dele (produto, custo, dado existente); no nível 3, a spec sempre passa por ele.

Delegue a um agente quando o trabalho dele não precisa voltar inteiro para esta conversa (mapear código, revisar um diff). Tarefa que cabe em poucos passos você mesmo faz.

## 4. Gate de qualidade

Antes de dizer que terminou, rode:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/quality-gate" --tier N
```

- `fail`: corrija. Se não der, explique ao usuário o que falhou e por quê.
- `incomplete`: diga ao usuário quais checagens ficaram "não verificado" (ferramenta ausente). Nunca chame de testado o que não rodou.
- `dependências novas`: justifique cada uma (ver `lean-code`).

O hook de `Stop` bloqueia o encerramento enquanto houver código alterado sem gate atualizado ou com gate falho. Configuração por projeto e lista de checagens: [references/quality-gate.md](references/quality-gate.md).

## 5. Relatório final (nível 1 ou mais)

1. Nível e motivo.
2. O que mudou: arquivos e linhas líquidas (`diff` do gate).
3. Evidência: veredito do gate; checagens ok, falhas e não verificadas.
4. O que ficou de fora ou é risco conhecido.
