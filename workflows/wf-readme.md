---
name: wf-readme
description: "Criar/auditar/reescrever README grounded. Scan real do repo."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [readme, documentation, docs, markdown, workflow]
---

# Workflow README (criar, auditar, reescrever)

Orquestrador obrigatório para qualquer trabalho de README (criar, melhorar,
auditar, padronizar) em qualquer projeto. Princípio central: **grounded** —
o README é construído a partir de fatos reais do repositório (manifest,
código, scripts, config, git), nunca fabricado de memória.

## When to Use

- "cria um README pra esse projeto" / "escreve a documentação"
- "melhora esse README" / "audita a qualidade do README"
- "padroniza a documentação do repo"
- Qualquer pedido de documentação de projeto (README/LICENSE/docs)

## Skills do stack

- `readme-crafter` (linhai0872) — classifica o projeto em 4 eixos (tipo,
  distribuição, público, temperamento) e gera README sob medida; 13 checks
  de verificação; modo collaborative/quick/surgical/audit.
- `good-readme` (adewale) — cria do zero com exemplos reais de código OU
  audita contra rubric de 22 critérios (escala 100); verifica exemplos
  contra o código real.
- `curating-readme` (liang-senbei) — padroniza README + docs relacionados
  (CONTRIBUTING/CHANGELOG/SECURITY/docs) com scripts determinísticos
  (`audit-repo.sh`) e estrutura canônica.
- Locais: `project-readme-clarity` (auditoria de onboarding/ambiguidades),
  `avoid-ai-writing` (remove AI-isms), `wf-frontend` (padrão visual de
  docs/README bonitos).

## Fase 1 — SCAN (coletar fatos reais)

1. Rodar o inventory determinístico do repo:
   `bash ~/.hermes/skills/curating-readme/scripts/audit-repo.sh <repo>`
   (ou o `scan-project.sh` do readme-crafter) — coleta manifest, entrypoints,
   scripts, config, estrutura, env vars, git, linguagens.
2. Ler manifest principal (package.json / pyproject.toml / go.mod / etc):
   nome, descrição, versão, dependências, scripts.
3. Identificar entrypoints: o que o projeto realmente faz (não o que diz).
4. Ler README existente (se houver), CLI_AGENTS.md, LICENSE.
5. VERIFICAR: marcar como **fato verificado** cada item com fonte no repo;
   qualquer coisa sem fonte vira `TODO:`/pergunta — nunca inventar.
6. VERIFICAR (comandos de scan): rodar `python3 -c "import json; json.load(open('package.json'))"`
   (ou equivalente para o manifest) para provar que o manifest parseia;
   e `git remote -v && git log --oneline -5` para capturar contexto real.
7. VERIFICAR (inventário): conferir com `find . -maxdepth 1 -type f | wc -l`
   a contagem real de arquivos e `du -sh .` para não documentar coisa que
   não existe. TRÊS CHECKS: manifest válido, git real, inventário presente.

**Checklist da fase 1:**
- [ ] Inventory do repo rodado (audit-repo.sh / scan-project.sh)
- [ ] Manifest lido e entendido
- [ ] Fato × suposição separados (suposição vira TODO/pergunta)

## Fase 2 — CLASSIFY (entender público e tipo)

1. `readme-crafter` — classificar o projeto:
   - Tipo: library / CLI / web app / framework / API / agent-AI / monorepo / ...
   - Distribuição: open-source público vs interno
   - Público: avaliador / novo usuário / contribuidor / operador / agente IA
   - Temperamento: developer utility / product / academic / community
2. Decidir audiência PRIMÁRIA (o README serve a quem primeiro).
3. VERIFICAR: registrar decisões de classificação (1 linha cada) — a
   estrutura do README deriva delas.
4. SE necessário, fazer perguntas do tipo "quem é o público?" ou "qual
   o tom?" quando o código não revela a intenção (3-5 perguntas máx).
5. VERIFICAR (comandos de classificação): para software com CLI, rodar
   `python3 -m <pkg> --help` (ou `node bin/index.js --help`) para capturar
   a sintaxe real de uso; para web app, listar `find src pages app -maxdepth 1 -type d 2>/dev/null` para ver as rotas reais.
6. VERIFICAR (decisões): registrar as 4 classificações com fonte — "tipo=CLI
   porque package.json.bin existe"; "público=developer porque docs de API".

**Checklist da fase 2:**
- [ ] Tipo / distribuição / público / temperamento definidos
- [ ] Audiência primária nomeada
- [ ] Perguntas de intenção (se houve) respondidas

## Fase 3 — AUDIT ou DRAFT (estado atual)

Se JÁ existe README:
1. `good-readme` — auditar contra 22 critérios; dar score /100.
2. Registrar: o que está bom, o que está desatualizado, o que está errado
   (claims que não batem com o código), o que falta.
3. `project-readme-clarity` — checar ambiguidades de onboarding (dependência
   opcional apresentada como obrigatória, passo que bloqueia primeiro valor).

Se NÃO existe README:
1. Anotar Fase 1+2 e seguir direto para a Fase 4 (draft).

VERIFICAR (comandos de auditoria):
- `grep -c "^#\|^##" README.md` — conta headings p/ o TOC futuro.
- `grep -oE "\]\([^)]*\)" README.md | grep -oE "\(\.?/?" | sort -u` — links
  locais que precisam existir no disco; conferir com `ls` que cada um vive.
- `grep -nE "install|npm |pnpm |pip |docker " README.md` — comandos citados;
  validar se existem de fato no repo (não só no texto).
- `bash ~/.hermes/skills/curating-readme/scripts/audit-repo.sh .` — re-rodar
  o inventory se o repo mudou desde a Fase 1.

**Comandos de auditoria (Fase 3):**
```bash
grep -nc "^#\|^##" README.md              # headings existentes
grep -oE "\]\(\.?/?[^)]*\)" README.md      # links locais citados
grep -nE "npm (install|run)|pnpm|pip |docker (run|compose)|uv " README.md 2>/dev/null
# validar que cada comando existe de fato:
command -v pnpm && pnpm --version
git log --oneline -3
```

**Anti-padrões (Fase 3):**
- NÃO dar score alto para README bonito mas incorreto (acurácia > estética).
- NÃO ignorar claims do README que não batem com o código — cada divergência
  é finding a corrigir.
- NÃO apresentar dependência opcional como obrigatória (project-readme-clarity).

**Checklist da fase 3:**
- [ ] README existente auditado (22 critérios / score) OU confirmado inexistente
- [ ] Checks de onboarding/ambiguidade rodados
- [ ] Comandos/links do README atual validados contra o repo
- [ ] Score baseline registrado (se README existia)

## Fase 4 — GENERATE (escrever com fatos verificados)

1. Estrutura canônica por tipo (referências do `good-readme`/`curating-readme`):
   título + badges (só os que existem) + descrição 1 linha + features reais +
   stack + prereqs + quickstart copy-paste + usage + config (tabela de env) +
   estrutura do projeto + contributing + license.
2. **Badges:** só incluir badges que refletem a realidade (license, linguagem,
   build se houver CI) — não criar badge de coisa que não existe.
3. **Exemplos de código: reais e testados.** Se o README mostra um comando
   ou exemplo, ELE DEVE funcionar no repo — verificar.
4. `avoid-ai-writing`: após redigir, limpar AI-isms (em-dash em excesso,
   "robust/seamless/leverage", transições genéricas, conclusões vazias).
5. Se o README for de repo público bonito (estilo shadcn/Vercel): seguir o
   padrão visual do `wf-frontend` (hero + badges + TOC + tabelas limpas).
6. VERIFICAR: cada claim do README tem fonte no repo (manifest, código,
   script, LICENSE) — nada inventado.

**Comandos reais (Fase 4):**
```bash
# comandos do README que precisam existir no repo
grep -oE '\b(npm|pnpm|python3|node |git|docker|uv) [^`]+' README.md
# conferir licença/tipo
head -1 LICENSE 2>/dev/null
# TOC vs headings: contar headings reais
grep -oE '^#{2,3} ' README.md | wc -l
```

**Checklist da fase 4:**
- [ ] Estrutura canônica seguida (adaptada ao tipo)
- [ ] Badges só do que existe
- [ ] Exemplos verificados contra o código
- [ ] 0 AI-isms (detect do avoid-ai-writing)
- [ ] Todo claim tem fonte

## Fase 5 — VERIFY + VALIDATE (prova de qualidade)

1. Validar README gerado:
   - Rodar `audit-repo.sh <repo>` de novo: conferir que nada essencial ficou
     de fora.
   - Checar links locais resolvem (`grep -o ']([^)]*)' README.md`; arquivos
     citados existem).
   - TOC bate com headings.
   - Comandos no README existem (checar que os binários/comandos citados
     são reais).
2. `good-readme` — re-auditar: score final deve subir vs Fase 3 (se houve
   README antes) ou ser alto (≥85/100) se criado.
3. `avoid-ai-writing` detect: 0 AI-isms restantes.
4. VERIFICAR gate do próprio workflow: `python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py`.
5. Relatório: score antes → depois, o que mudou, checks que passaram.

**Checklist final:**
- [ ] Links locais resolvem
- [ ] Comandos do README são reais
- [ ] TOC bate
- [ ] Score de qualidade ≥ 85/100 (good-readme) ou melhorou vs antes
- [ ] 0 AI-isms
- [ ] Gate do workflow (test_quality.py) verde

**Comandos de validação (Fase 5):**
```bash
# 1) links locais do README existem
grep -oE '\]\(\.?/?[^)]*\)' README.md | sed 's/](//; s/)$//' | while read p; do [ -e "$p" ] || echo "MISSING: $p"; done
# 2) TOC vs headings (sem TOC = ok, com TOC precisa bater)
grep -oE '^##{1,3} ' README.md | wc -l
# 3) 0 AI-isms (em-dash em excesso)
grep -o "—" README.md | wc -l
# 4) refere o LICENSE/contribuição existem
ls LICENSE CONTRIBUTING.md 2>/dev/null
# 5) gate do stack
python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py
```

**Anti-padrões desta fase:**
- NÃO pular a re-auditoria (good-readme score) por "tá bom já".
- NÃO entregar sem rodar o detect do avoid-ai-writing (AI-ism = regressão).
- NÃO tratar "README mais bonito" como objetivo sem validar acurácia —
  bonito ≠ correto; a acurácia vem antes.

## Regras duras

- NUNCA inventar instalação, comando, exemplo, screenshot ou feature que
  não exista no repo — fato sem fonte vira TODO ou pergunta.
- NUNCA incluir badge de coisa que não existe (CI sem CI, licensa sem LICENSE).
- NUNCA entregar README com AI-isms (rodar avoid-ai-writing antes de fechar).
- NUNCA afirmar "testado" sem ter executado o comando.
- NUNCA copiar estrutura de outro projeto sem adaptar ao tipo/público real.
- README do usuário do repo deve entender "clono → rodar" sem configurar
  dependência opcional desnecessária (project-readme-clarity).
- NUNCA deixar `TODO:` no README final — TODO só durante o rascunho; na
  entrega, todo fato ou foi preenchido com fonte ou virou pergunta ao usuário.
- NUNCA trocar linguagem da prosa no meio (EN/PT misturados) — o README
  principal tem UMA língua; traduções vão em arquivos separados.
- NÃO encher de emojis/badges decorativos; cada elemento tem função.
- NÃO duplicar informação (instalação em 2 seções é bug de manutenção).
