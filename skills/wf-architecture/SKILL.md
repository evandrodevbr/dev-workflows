---
name: wf-architecture
description: Use para decisões de arquitetura - desenho de sistema ou serviço novo, escolha de stack, mudança de fronteira entre módulos, migração com dado existente, troca de auth, diagrama C4, ADR, threat model, "isso é uma boa ideia arquitetonicamente?". É o workflow do nível 3 do dev-router (e do nível 2 quando surge uma decisão difícil de desfazer). Não use para bug, refactor local, tela ou endpoint isolado sem decisão estrutural (use wf-bugfix, wf-refactor, wf-frontend ou wf-backend).
license: MIT
metadata:
  dev-workflows:
    uses: []
    external: [system-design, c4-architecture, isaqb-architecture-governance, secure-architecture-governance]
---

# Workflow Arquitetura

**Nível 3** do `dev-router`, ou nível 2 quando aparece uma decisão difícil de desfazer (banco,
protocolo, fronteira de serviço, modelo de auth). No nível 2, faça só a Fase 3 (um ADR para a decisão)
e siga com `wf-backend`/`wf-frontend`. Abaixo disso, este workflow não roda.

Cada fase produz um arquivo versionado. O que não virou arquivo não foi decidido.

Skills externas, se instaladas: `system-design` (raciocínio de design), `c4-architecture` (diagramas),
`isaqb-architecture-governance` (arc42 e ADR), `secure-architecture-governance` (STRIDE e S-ADR).
Sem elas, os modelos em [references/](references/) bastam.

## Fase 1: REQUIREMENTS

Entender antes de desenhar. Use o agente `planner` com o mapa do `explorer`.

1. Requisitos funcionais em **EARS com ID** (`REQ-001: WHEN ... THE SYSTEM SHALL ...`).
   Modelo e padrões: [references/ears.md](references/ears.md).
2. Não funcionais **com número**: SLO (ex.: p95 < 250 ms, 99,9% ao mês), orçamento de performance
   (LCP, tamanho de bundle, custo mensal), nível ASVS 5.0 (L2 por padrão no nível 3).
   "Rápido" ou "escalável" sem número não é requisito.
3. Atores, entidades centrais e fronteiras de confiança.
4. Stack ou framework novo: consulte a documentação atual e registre URL e data. Não decida pela memória.

**Artefato:** `docs/specs/<nome>.md` com os `REQ-` e os não funcionais.
**Gate da fase:** o usuário aprova a spec antes do DESIGN.

Rastreabilidade: adicione ao `.dev-workflows.toml` do projeto

```toml
[spec]
file = "docs/specs/<nome>.md"
tests = ["tests"]
```

e o gate nível 3 falha se algum `REQ-` não aparecer em um teste
(ver `skills/dev-router/references/quality-gate.md`).

## Fase 2: DESIGN

1. Fluxo de design: requisitos, entidades, API, fluxo de dados, visão geral, pontos críticos.
2. **C4** em Mermaid: Context e Container sempre; Component só onde houver decisão.
   Até 20 elementos por view, setas rotuladas, IDs estáveis. Modelo: [references/c4.md](references/c4.md).
3. Modelo de dados e estratégia de migração (reversível; com dado existente, plano de backfill e rollback).
4. **Pelo menos uma alternativa** por decisão importante, com o motivo da escolha.

**Artefato:** `docs/architecture/design.md` com os diagramas.
Confira que o Mermaid renderiza: `npx -y @mermaid-js/mermaid-cli -i docs/architecture/c4.mmd -o /tmp/c4.svg`.

## Fase 3: DOCS (ADR)

Um ADR por decisão difícil de desfazer: contexto, opções, decisão, consequências (boas e ruins).
Modelo: [references/adr.md](references/adr.md).

- `docs/architecture/adr/NNNN-<titulo>.md`, numeração sequencial, nunca reescrever um ADR aceito
  (substitua por um novo com `Substitui: ADR-NNNN`).
- Decisão motivada por segurança vira S-ADR em `docs/security/adr/`.
- Todo ADR citado no design (`ADR-0003`) existe como arquivo.

## Fase 4: THREAT MODEL

STRIDE por fronteira de confiança, cada ameaça ligada a um controle ASVS 5.0 L2.
Tabela e mapeamento: [references/stride.md](references/stride.md).

1. Liste as fronteiras (internet/app, app/banco, serviço/serviço, app/terceiros, app/LLM).
2. Para cada fronteira, as seis categorias STRIDE: ameaça concreta, controle, capítulo ASVS, status.
3. Caminhos internos sem autenticação e confiança implícita entre serviços são achados, não detalhes.
4. Feature que chama LLM: inclua OWASP LLM Top 10 (prompt injection, excessive agency).

**Artefato:** `docs/security/threat-model.md`.

## Fase 5: REVIEW

1. Agente `reviewer` sobre spec, design e ADRs: consistência entre `REQ-`, diagramas e ADRs,
   requisito sem dono, decisão sem alternativa.
2. Agente `security-auditor` sobre o threat model e as decisões de segurança.
3. Veredito por escrito: `Aprovado`, `Aprovado com mudanças` ou `Revisar`, cada achado com evidência
   (arquivo e trecho). Gap de fronteira de confiança volta para o DESIGN.
4. O usuário aprova. A implementação segue com `wf-backend`/`wf-frontend`, tarefa a tarefa,
   e fecha com `"${CLAUDE_PLUGIN_ROOT}/scripts/quality-gate" --tier 3`.

## Não faça

- Desenhar antes de ter requisito mensurável.
- ADR sem alternativa ou sem consequências.
- Mais de um ADR para a mesma decisão.
- Tratar segurança como nota mental: vira ameaça no threat model ou S-ADR.
- Decidir stack sem fonte atual.

## Checklist de entrega

- [ ] `docs/specs/<nome>.md` com `REQ-` em EARS e não funcionais com número, aprovado pelo usuário.
- [ ] `[spec]` no `.dev-workflows.toml` do projeto.
- [ ] `docs/architecture/design.md` com C4 que renderiza e alternativas registradas.
- [ ] Um ADR por decisão difícil de desfazer, com consequências.
- [ ] `docs/security/threat-model.md` com STRIDE por fronteira e controles ASVS L2.
- [ ] Revisão do `reviewer` e do `security-auditor` com veredito e evidência.
