---
name: wf-architecture
description: "Use p/ arquitetura. Fluxo REQ→DESIGN→DOCS→REVIEW."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [architecture, design, c4, adr, arc42, threat-model, workflow]
---

# Workflow Arquitetura

Orquestrador obrigatório para todo trabalho de arquitetura: desenho de
sistemas, decisões (ADR), diagramas C4, threat modeling, revisão de
arquitetura. Processo de 4 fases com skills fixas.

## When to Use

Sempre que a tarefa envolver: arquitetura/design de sistema, escolha de
stack, diagramas, ADR, threat model, revisão estrutural, ou "é uma boa
ideia arquitetonicamente?".

## Skills do stack (carregar conforme a fase)

- Design de sistema (raciocínio): `system-design` (HelloInterview framework)
- Diagramas: `c4-architecture` (Context/Container/Component/Deployment)
- Documentação: `isaqb-architecture-governance` (arc42 + ADR)
- Segurança: `secure-architecture-governance` (STRIDE+CIA, S-ADR)
- Qualidade de documentação: `avoid-ai-writing` (remove AI-isms de ADRs,
  docs de arquitetura, RFCs — registros que vão durar anos não devem soar
  gerados por IA)
- Locais: `security-threat-model`, `architecture-diagram` (SVG),
  `excalidraw`, `brainstorming`, `writing-plans`

## Fase 1 — REQUIREMENTS (entender antes de desenhar)

1. `brainstorming` — explorar intenção, requisitos funcionais e NFRs
   (latência, escala, disponibilidade, custo) antes de qualquer desenho.
2. Identificar entidades centrais, limites, fluxos de dados e atores.
3. Estado da arte: checar evolução/relevância de stack/framework.
4. VERIFICAR: rodar `hermaguard` conceitual no escopo (o que pode dar
   errado com esta arquitetura?) e validar com o usuário que cada NFR é
   mensurável (ex: "p95 < 250ms" e não "rápido").
5. Checkpoint: listar requisitos validados e SÓ seguir ao DESIGN com
   aprovação explícita.
6. VERIFICAR (comandos de requisitos): escrever FRs/NFRs em
   `docs/requirements.md` e rodar `grep -c "NFR" docs/requirements.md`
   para garantir que TODOS os NFRs viraram critério mensurável.
7. VERIFICAR (cobertura): usar `search_files` para confirmar que nenhum
   requisito levantado ficou órfão (cada FR/NFR tem dono e número).
8. VERIFICAR (comandos de estado da arte): consultar fontes atuais para
   stack/framework antes de decidir — usar `web_search`/consultas técnicas
   e registrar URL + data no requirements.md (não decidir stack do nada).
9. VERIFICAR (pontos de risco): listar os 3 maiores riscos técnicos do
   escopo e checar com `hermaguard` conceitual se algum deles muda a
   decisão de arquitetura — risco conhecido não vira surpresa depois.
10. CHECKPOINT final da Fase 1: apresentar requisitos para aprovação; sem
    OK explícito não avança para DESIGN.
11. VERIFICAR (comandos de requisitos): `python3 -c "import yaml,sys; yaml.safe_load(open('docs/requirements.md'))"` se requisitos em YAML
    (ou parser equivalente) para provar que o formato é válido; e
    `curl -s -o /dev/null -w "%{http_code}" URL` quando houver fonte
    externa de referência citada.
12. VERIFICAR (critério de requisito): conferir que cada requisito tem
    "critério de aceite" ou número alvo — sem requisito "aberto" sem
    definição de pronto.

**Checklist da fase 1 (validar requisitos):**
- [ ] Requisitos funcionais e NFRs (latência, escala, disponibilidade, custo)
      coletados e mensuráveis (ex: "p95 < 250ms" ao invés de "rápido").
- [ ] Entidades centrais, limites e atores identificados.
- [ ] Estado da arte de stack/framework verificado.
- [ ] Requisitos aprovados pelo usuário antes de desenhar.

**Anti-padrões desta fase:**
- NUNCA desenhar sem requisito mensurável.
- NUNCA inventar NFR ("ser escalável") — exigir número e critério.
- NÃO pular a aprovação do usuário para "andar logo".
- NÃO decidir stack antes de validar requisitos (viés de ferramenta).

## Fase 2 — DESIGN (modelar o sistema)

1. `system-design` — percorrer o framework: requisitos → entidades → API →
   data flow → high-level design → deep dives. Documentar trade-offs.
2. `c4-architecture` — gerar diagramas (Context → Container → Component)
   em Mermaid/Structurizr. Declarar elementos em ordem de leitura, evitar
   cruzamentos (research-backed).
3. `secure-architecture-governance` — mapear trust boundaries e rodar
   STRIDE+CIA nas decisões de segurança (auth, dados sensíveis).
4. VERIFICAR: rodar `c4-architecture` de novo para audit — cada diagrama
   tem IDs estáveis, setas com rótulo e <=20 elementos por view? Validar
   com o usuário antes de documentar.
5. VERIFICAR (comandos de design): se Structurizr, validar com
   `python3 -c "import json; json.load(open('workspace.json'))"` que o
   modelo é parseável; para Mermaid, conferir que os blocos ```mermaid
   fecham corretamente (contar crases ímpares = erro).
6. VERIFICAR (trade-offs): `grep -c "alternativa" docs/design.md` — cada
   decisão tem pelo menos 1 alternativa documentada com o porquê?
7. VERIFICAR (limites): `grep -n "boundary\|trust" docs/design.md` —
   trust boundaries explícitos nos diagramas; todo fluxo de dado sensível
   cruza boundary documentada.
8. VERIFICAR (comandos de render): se Mermaid, rodar `npx @mermaid-js/mermaid-cli -i d.mmd -o d.svg` (ou Playwright) para provar que o
   diagrama renderiza sem erro de sintaxe.
9. VERIFICAR (comandos de contagem): `grep -c "component\|container" docs/c4.md` — todo container mapeado tem representação; `wc -l docs/c4.md > 10` garante diagrama não-vazio.
10. VERIFICAR (critério de design): confirmar com o usuário que cada view
    reflete os requisitos da Fase 1 (rastreabilidade view→requisito) e
    que os trade-offs estão anotados — sem view "solta".

**Checklist da fase 2 (validar o modelo):**
- [ ] `system-design` percorrido: requisitos → entidades → API → data flow →
      high-level → deep dives.
- [ ] Diagramas C4 (Context → Container → Component) com IDs estáveis, setas
      rotuladas e <=20 elementos por view.
- [ ] Trust boundaries mapeados; STRIDE+CIA aplicado nas decisões sensíveis.
- [ ] Trade-offs documentados (as 2 soluções alternativas + por quê a escolha).

**Anti-padrões desta fase:**
- NUNCA diagramar sem requisitos (Fase 1) — diagrama sem base vira enfeite.
- NUNCA deixar seta sem rótulo ou elemento sem ID estável.
- NÃO desenhar >20 elementos por view (ilegível = não é documento).
- NÃO ignorar trust boundary ao desenhar fluxo de dados sensível.

## Fase 3 — DOCS (decisões em registros)

1. `isaqb-architecture-governance` — criar ADR (e S-ADR se decisão for
   security-driven) com alternativas e consequências. ID estável e
   reutilizado nos diagramas/docs.
2. `avoid-ai-writing` — pós-escrever QUALQUER doc/ADR/RFC: detect+rewrite
   dos AI-isms (tiers 1/2/3, em-dash, "crucial", "robust", transições
   genéricas). Arquitetura documentada é lida por anos — não deve soar IA.
3. Estrutura de saída: `docs/architecture/` (ADRs, views arc42) e
   `docs/security/` (S-ADRs, threat models) — sem colisão de nomes.
4. NFRs virarem critérios mensuráveis (não frase de efeito).
5. VERIFICAR: rodar `avoid-ai-writing` em modo detect em cada ADR (0 AI-isms
   restantes), confirmar arquivos criados em `docs/architecture/adr/` e
   `docs/security/adr/` e conferir que IDs de ADR/S-ADR são únicos.
6. VERIFICAR (comandos de docs): `ls docs/architecture/adr/ docs/security/adr/`
   para listar os registros criados e `grep -rL "Consequências" docs/` para
   achar ADR que esqueceu a seção de consequências.
7. VERIFICAR (rastreabilidade): `grep -rc "AD-...-NNN" docs/architecture/`
   — cada ADR aparece referenciado em pelo menos um diagrama ou decision log.
8. VERIFICAR (comandos de docs): confirmar com `find docs/ -name "*.md" -o -name "*.mmd" | sort` que a árvore está organizada; e `wc -l docs/architecture/adr/*.md` para garantir ADR com corpo (não só título).
9. VERIFICAR (estilo consistente): `grep -rn "em dash\|—" docs/architecture/adr/ | wc -l` — em-dash em excesso = AI-ism residual (rodar avoid-ai-writing).
10. VERIFICAR (comandos de validação de docs): `python3 -m json.tool docs/workspace.json > /dev/null` para Structurizr; `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/...` se houver visualização local; e `git diff --stat docs/` para conferir o que foi documentado.
11. VERIFICAR (critério de aceite de doc): cada ADR responde "por que essa decisão?" e lista consequências — `grep -L "Consequências" docs/architecture/adr/*.md` deve ser vazio.

**Checklist da fase 3 (documentação):**
- [ ] ADR (ou S-ADR se security-driven) criado com alternativas + consequências.
- [ ] `avoid-ai-writing` em detect = 0 em cada ADR/RFC.
- [ ] Arquivos em `docs/architecture/adr/` e `docs/security/adr/`; IDs únicos.
- [ ] NFRs viram critérios mensuráveis no documento (não frase solta).

**Anti-padrões desta fase:**
- NUNCA publicar ADR sem alternativas consideradas.
- NUNCA publicar doc com AI-isms não tratados.
- NÃO criar 2 ADRs para a mesma decisão; NÃO duplicar decisão geral e S-ADR.
- NÃO deixar ID solto (decisão precisa ser rastreável ao diagrama/código).

## Fase 4 — REVIEW (verificar antes de aprovar)

1. `secure-architecture-governance` — auditar decisões contra ISO/IEC
   25010 (performance, segurança, confiabilidade, manutenibilidade).
2. Threat model final + gaps de trust boundary (unauthenticated internal
   paths, implicit service trust) priorizados.
3. Checar consistência: IDs batem entre diagramas, ADRs e docs?
4. Verdict objetivo: Approved / Approved-with-changes / Needs-revision,
   com evidência por finding — não gosto pessoal.
5. VERIFICAR (gate final): rodar `secure-architecture-governance` como
   checklist, validar a árvore de arquivos com `search_files`, e dar o
   verdict com base na evidência — se houver gap de security, reverter ao
   DESIGN.
6. VERIFICAR (comandos de revisão): usar `grep -r "AD-...-NNN" docs/` para
   provar que IDs aparecem nos diagramas, e `git status` para conferir que
   tudo que foi modelado virou arquivo versionado.
7. VERIFICAR (anti-slop de docs): rodar `node .../avoid-ai-writing/detector/validate.js`
   nos ADRs e `test_quality.py` no workflow — sem regressão.
8. VERIFICAR (todos os arquivos versionados): `git status --porcelain` deve
   mostrar só o esperado; `find docs/ -name "*.md" | wc -l` confere a
   contagem de docs criados vs planejados na Fase 1.
9. VERIFICAR (comandos de evidência por finding): para cada finding,
   `grep -rn "<id-do-finding>" docs/security/` deve retornar a evidência —
   sem achado "sem referência".
10. VERIFICAR (conclusão): `git diff --stat` + `git status` para conferir
    o que o ciclo produziu; nada de diagrama/doc não versionado sendo
    citado como entregue.
11. VERIFICAR (comandos de revisão final): rodar `python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py` (gate) e conferir o
    `git diff --stat` — a revisão só fecha com gate verificado e sem
    pendências de arquivo.
12. VERIFICAR (não-regressão de nomes): conferir que nenhuma skill do stack
    foi renomeada/quebrada — rodar o harness (G4) e `test_tests.py`.

**Checklist da fase 4 (revisão):**
- [ ] Auditoria contra ISO/IEC 25010 por decisão (performance, segurança,
      confiabilidade, manutenibilidade).
- [ ] Threat model final com gaps de trust boundary priorizados.
- [ ] Consistência de IDs: diagramas × ADRs × docs batem.
- [ ] Verdict objetivo emitido: Approved / Approved-with-changes /
      Needs-revision, com evidência por finding.

**Anti-padrões desta fase:**
- NUNCA dar verdict "approved" sem evidência em cada finding.
- NUNCA ignorar gap de trust boundary (unauthenticated internal path).
- NÃO confundir opinião estética com achado — achado exige referência.
- NÃO deixar segurança como "nota mental" — virar S-ADR ou finding listado.

## Comandos de Verificação (executáveis)

```bash
# Gate de qualidade do próprio workflow (sem regressão)
python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py

# Verifica consistência da documentação (IDs estáveis em diagramas/docs)
# (skill isaqb-architecture-governance + c4-architecture)

# Threat model: auditoria STRIDE+CIA contra ISO 25010
# (skill secure-architecture-governance)

# Audit de AI-isms nos ADRs/RFCs (detect = só mostra)
node ~/.hermes/skills/avoid-ai-writing/detector/validate.js adr.md adr-limp.md
```

## Critérios de Aceite (checklist não-regressivo)

- [ ] Fase 1 concluída com requisitos/NFRs mensuráveis aprovados pelo usuário.
- [ ] Fase 2 gerou diagramas C4 com IDs estáveis e rótulos; validados.
- [ ] Fase 3 gerou ADR/S-ADR em `docs/architecture/` e `docs/security/`;
      `avoid-ai-writing` detect = 0 AI-isms.
- [ ] Fase 4 auditou contra ISO 25010 + threat model; verdict emitido.
- [ ] Nenhuma skill do stack removida do arquivo.
- [ ] Rodar `python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py`
      → exit 0 (sem regressão).

## Exemplos de execução por fase (comandos reais)

Fase 1 — requisitos estruturados:

```bash
cat > docs/requirements.md <<'EOF'
# Requisitos
FR1: usuário cria e gerencia listas
NFR1: p95 < 250ms (API)
NFR2: disponibilidade 99.9%
NFR3: custo mensal < R$ 500
EOF
```

Fase 2 — diagrama C4 (definir estrutura antes):

```bash
# Estrutura do C4 em texto (depois renderizar com c4-architecture/Mermaid)
cat > docs/c4.md <<'EOF'
Context: [Usuário] -> [Sistema X]
Container: [Web] -> [API] -> [Postgres] -> [Redis]
EOF
```

Fase 3 — ADR curto:

```bash
# Criar ADR em docs/architecture/adr/0001-*.md (isaqb-architecture-governance)
# S-ADR em docs/security/adr/ quando a decisão for security-driven
```

Fase 4 — validação do conjunto:

```bash
# Consistência de IDs entre diagramas, ADRs e docs (search_files)
grep -r "ADR-" docs/ | wc -l            # cada referência existe
grep -rn "S-ADR" docs/security/ | wc -l # decisões security-driven têm S-ADR
# "audite a arquitetura" (secure-architecture-governance: ISO 25010)
python3 -m json.tool docs/workspace.json > /dev/null  # Structurizr válido?
# "rode o avoid-ai nos ADRs" (modo detect)
node ~/.hermes/skills/avoid-ai-writing/detector/validate.js adr.md adr-limp.md
find docs/ -name "*.md" -o -name "*.mmd" | sort  # árvore organizada
```

Gates do workflow (anti-regressão):

```bash
python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py
python3 ~/.hermes/skills/software-development/wf-qa/test_tests.py
```

## Regras duras

- NUNCA diagramar antes de requisitos claros (Fase 1).
- NUNCA entregar ADR sem alternativas consideradas e consequências.
- NUNCA publicar ADR/RFC/doc com AI-isms não tratados (passar por
  `avoid-ai-writing` antes de dar como entregue).
- Decisão com load-bearing security → S-ADR em `docs/security/`, nunca nos
  ADRs gerais.
- Diagrama tem que ter declaração em ordem de leitura + alvo de
  cruzamentos — legibilidade é requisito, não luxo.
