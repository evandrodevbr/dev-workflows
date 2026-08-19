---
name: wf-frontend
description: "Use p/ frontend/UI. Fluxo DESIGN→BUILD→REVIEW."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [frontend, ui, ux, design, react, tailwind, workflow]
---

# Workflow Frontend/Design

Orquestrador obrigatório para TODO trabalho de frontend, UI, UX ou design
(componentes, páginas, landing, apps, re-design, design system). Processo de
3 fases com skills fixas por fase.

## When to Use

Sempre que a tarefa envolver interface do usuário ou GERAÇÃO DE PDF:
- Frontend/UI: criar/editar componentes React/Vue/Svelte, páginas, layouts,
  estilos, animações, acessibilidade, qualquer pedido de "design"
- **PDF/DOCUMENTOS VISUAIS: SEMPRE via este workflow** (regra do Evandro,
  ago/2026) — NUNCA reportlab platypus raw (estoura bordas em tabelas
  longas). Usar HTML+CSS → Playwright headless (`pdf-generator`,
  `html-css-print-engineer`, `pdf-render-qa`). Design primeiro, depois
  render, depois QA visual (vision_analyze) antes de entregar.
- Vale para apps novos e refactors.

## Skills do stack (carregar conforme a fase)

- Direção visual / anti-AI-slop: `frontend-design` (Anthropic), `web-design`,
  `impeccable` (pbakaus — 23 comandos de design: craft/shape/audit/polish/
  animate/live; 59 regras determinísticas anti-slop), e locais
  `frontend-award-tier`, `claude-design`, `popular-web-designs`,
  `anti-ai-slop`
- React/Next performance + composição: `vercel-react-best-practices`,
  `vercel-composition-patterns`
- Motion: `animate` (emilkowalski)
- Bug hunting: `hermaguard` (pre-scan + 3 agentes adversariais; read-only)
- Qualidade de texto/UI copy: `avoid-ai-writing` (remove AI-isms de microcopy,
  textos de componente, a11y labels, README de frontend)
- Esboço rápido / docs visuais: `sketch`, `design-md` (locais)
- PDF de qualidade: `pdf-generator` (HTML+CSS LaTeX → Playwright),
  `html-css-print-engineer`, `pdf-render-qa` (QA), `professional-pdf-director`,
  `pdf-visual-designer` — todo PDF passa por aqui

## Fase 1 — DESIGN (decidir antes de codar)

1. Carregar `frontend-design` + `frontend-award-tier` + `anti-ai-slop`.
2. Definir direção visual explícita: paleta, tipografia, espaçamento,
   densidade, dark/light — NUNCA gerar "default AI slop".
3. Se for re-design/variação: `claude-design`/`popular-web-designs` para
   basear em design systems reais (Stripe/Linear/Vercel) e fugir do genérico.
4. Documentar decisões em `DESIGN.md` (padrão `design-md` se aplicável).
5. Parar e validar a direção com o usuário ANTES de implementar.
6. VERIFICAR: rodar `avoid-ai-writing` em detect no DESIGN.md (0 AI-isms) e
   confirmar que a direção está registrada (paleta + tipografia + density)
   antes de codar.
7. VERIFICAR (gate visual): se for PDF/artefato visual, renderizar um
   rascunho e inspecionar com `vision_analyze` ANTES de avançar — validar
   que a direção visual de fato foi aplicada e nada está fora de margem.
8. CHECKPOINT: gravar decisões (paleta final, fonte, density) num
   `DESIGN.md` com versionamento, para as fases seguintes referenciarem.
9. VERIFICAR (comandos de direção): conferir que `DESIGN.md` existe e tem
   conteúdo — `wc -l DESIGN.md` > 5; e que as cores/fontes estão anotadas
   (`grep -c "paleta\|fonte\|spacing" DESIGN.md` >= 3).
10. VERIFICAR (anti-slop real): rodar o `anti-ai-slop` no direção proposta
    antes de mostrar ao usuário — detectar gradiente/glassmorphism
    prematuramente economiza retrabalho.
11. VERIFICAR (comandos de design): validar a direção também contra a
    ferramenta de design usada — `npx`/CLI do design system (ex:
    `pnpm tailwindcss` se Tailwind) confirmando tokens aplicáveis; e
    checar com `grep -rn "palette\|tokens\|--color" DESIGN.md` que os
    tokens ficaram declarados.

**Checklist da fase 1 (validar todos antes de seguir):**
- [ ] Direção visual definida e DOCUMENTADA (paleta, tipografia, spacing).
- [ ] Anti-slop: nenhum padrão "default IA" (gradiente, glassmorphism, ícones genéricos).
- [ ] `DESIGN.md` existe e está aprovado pelo usuário.
- [ ] `avoid-ai-writing` detect = 0 no DESIGN.md.

**Anti-padrões desta fase:**
- NUNCA pular a definição de direção visual "só para ver como fica".
- NUNCA aprovar design sem a confirmação explícita do usuário.
- NÃO misturar 2 design systems na mesma tela; se for variação, basear em um só.

## Fase 2 — BUILD (implementar com padrões de produção)

1. Carregar `vercel-react-best-practices` + `vercel-composition-patterns`
   (React) — aplicar regras de performance (waterfalls, bundle, re-renders)
   e composição (compound components, sem boolean-prop explosion).
2. Componentes acessíveis por padrão (WCAG): semântica HTML, foco,
   contraste — sem depender de ARIA desnecessário.
3. Animações só quando agregam: `animate` — propósito, duração, easing,
   reduzir motion para prefers-reduced-motion.
4. Responsivo mobile-first; estados vazios/loading/erro em todo fluxo.
5. VERIFICAR: rodar build + lint incrementalmente a cada componente
   (npm/pnpm build) e `vercel-react-best-practices` como checklist de perf
   durante o build — não deixar para o fim.
6. VERIFICAR (a11y atômica): para cada componente novo, conferir semântica
   HTML, gerenciamento de foco e contraste ANTES de considerar pronto —
   acessibilidade é parte do build, não polimento final.
7. VERIFICAR (perf real): medir com DevTools/Lighthouse por tela-chave
   (LCP, INP, CLS) e registrar os números no relatório de perf.
8. VERIFICAR (composição limpa): `grep -rn "is[A-Z]\|show[A-Z]" src/components`
   para caçar boolean-prop explosion (deve ser 0 ou poucos intencionais);
   se houver, refatorar para compound components.
9. VERIFICAR (animações justificadas): para cada `animate`/motion adicionada,
   conferir com `grep -rn "animate\|transition\|motion" src/` que há propósito
   (hover/estado/entrada) — animação decorativa sem função = cortar.
10. VERIFICAR (limpeza): `git status` e `git diff --stat` antes de fechar —
    nada de arquivo órfão/debug commitado.
11. VERIFICAR (critério de aceite do componente): cada componente novo
    confirma o critério definido na Fase 1 (estado correto, a11y ok, perf
    ok) antes de passar para o próximo — validar item a item do checklist.
12. VERIFICAR (comandos de estado): conferir que loading/erro/vazio são
    tratados em cada fluxo — `grep -rn "loading\|isLoading\|error\|empty" src/`
    para provar a presença nos componentes que interagem com dados.
13. VERIFICAR (anti-padrão visual final): percorrer os componentes com
    `anti-ai-slop` de novo ao fechar a fase — sombra/glassmorphism que
    "escapou" no scroll é regressão de qualidade.
14. VERIFICAR (critério de aceite): validar que cada item do checklist da
    fase está marcado (sem checkbox em branco) antes de declarar BUILD
    concluído.

**Checklist da fase 2 (validar antes da REVIEW):**
- [ ] Build e lint verdes (`npm run build` / `npx tsc --noEmit`).
- [ ] Componentes acessíveis (semântica HTML, foco, contraste) — auditar com
      `frontend-design`/a11y antes de considerar pronto.
- [ ] Estados vazios/loading/erro presentes em todo fluxo.
- [ ] Animações com propósito + `prefers-reduced-motion` respeitado.

**Anti-padrões desta fase:**
- NUNCA usar `any`/forçar cast em TS para "fazer passar".
- NUNCA animar sem propósito — animação decorativa gratuita é anti-padrão.
- NÃO implementar responsivo só no final; mobile-first desde o início.
- NÃO duplicar lógica de estado em vários componentes (compor, não copiar).

## Fase 3 — REVIEW (verificar antes de entregar)

1. `anti-ai-slop` sobre o resultado (gradientes-texto, glassmorphism,
   sombras genéricas, layout previsível).
2. `avoid-ai-writing` sobre textos entregues ao usuário: microcopy, labels,
   empty states, mensagens de erro, README/descrições — remover AI-isms
   (em-dash em excesso, "robust", "seamless", "let's dive in", etc).
3. `hermaguard` no diff de frontend (JS/TS/TSX/CSS): caça bugs adiversariais
   no código produzido (lógica de estado, efeitos, a11y que quebra).
4. `vercel-react-best-practices` como checklist de perf (LCP/INP/CLS,
   bundle, imagem, Suspense).
5. Rodar build + lint + testes do projeto; corrigir o que quebrar.
6. Relatório curto: o que foi decidido na Fase 1, entregue na 2, verificado
   na 3.
7. VERIFICAR (regressão visual): se houver, comparar screenshots do antes
   vs depois (ou `vision_analyze` no render) para garantir que nada quebrou
   de layout.
8. VERIFICAR (não-regressão QA): rodar `test_quality.py` (gate do workflow)
   e conferir que o score do stack não caiu.
9. VERIFICAR (hermaguard re-audit): se o REVIEW mudou >3 arquivos, rodar
   `hermaguard` no novo diff antes de fechar.
10. VERIFICAR (bundle/perf real): rodar `npm run build` e conferir tamanho
    dos chunks (`ls -lh dist/static/*.js`), anotar LCP/INP/CLS se houver
    Lighthouse.
11. VERIFICAR (html válido): para PDF/páginas, validar o HTML antes do
    render — `python3 -c "from html.parser import HTMLParser; ...
    "` (ou parser disponível) e `grep -c "</t" arquivo.html` = 0 (sem tag
    truncada).
12. VERIFICAR (comandos de acessibilidade): rodar auditoria de a11y no
    render final — `npx @axe-core/cli http://localhost:PORT` (se houver
    dev server) ou `pa11y`/equivalente; anotar violações sérias.
13. VERIFICAR (contraste verificado): para paleta dark/light, conferir
    contraste com ferramenta (ex: `npx contrast-checker` ou manual) —
    textos principais >= 4.5:1.

**Checklist da fase 3 (gate de entrega):**
- [ ] `anti-ai-slop` aplicado e sem ressalvas no resultado final.
- [ ] `avoid-ai-writing` detect = 0 em microcopy/labels/errors/README.
- [ ] `hermaguard` rodado no diff (0 findings CRITICAL/HIGH pendentes).
- [ ] `vercel-react-best-practices` auditado (LCP/INP/CLS, bundle, imagem).
- [ ] Build + lint + testes verdes com contagem real.
- [ ] Para PDF: renderização via Playwright + `vision_analyze` sem corte.

**Anti-padrões desta fase:**
- NUNCA dar como entregue com build vermelho.
- NUNCA ignorar finding CRITICAL/HIGH do hermaguard "para depois".
- NÃO pular o QA visual de PDF (conteúdo cortado nas bordas = entrega quebrada).
- NÃO entregar relatório sem os itens do checklist marcados.

## Comandos de Verificação (executáveis)

Gate de qualidade do stack (rodar SEMPRE antes de entregar):

```bash
# 1) Não-regressão: valida que os workflows continuam íntegros
python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py

# 2) Testes-dos-testes: prova que o harness detecta regressão
python3 ~/.hermes/skills/software-development/wf-qa/test_tests.py
```

QA visual de PDF — renderizar páginas e inspecionar bordas (nada cortado):

```bash
cd ~/.hermes/skills/productivity/pdf/scripts
python pdf_page_image.py /caminho/do.pdf --pages 1-3 --dpi 150 --out-dir /tmp/qa
# depoiss: vision_analyze em cada PNG — margens ok, sem truncamento
```

Qualidade de texto (microcopy, labels, README) — auditoria de AI-isms:

```bash
# detect (só lista) — passa 2 arquivos para comparar original vs limpo
node ~/.hermes/skills/avoid-ai-writing/detector/validate.js ui-copy.md ui-copy-limp.md

# ou debaixo do wf: pedir "roda o avoid-ai no README" (modo detect/rewrite)
```

Bug hunt adversarial no diff (comandos da skill hermaguard):

```bash
# gatilho: "hermaguard this" / "adversarial review" / "bug hunt this"
# gera relatório em /tmp/hermaguard/hermaguard-<ts>.md + .json
```

Performance React/Next — checklist durante o build:

```bash
npm run build   # ou pnpm build — verificar warnings de bundle chunk
npx tsc --noEmit  # typecheck limpo
npm run lint     # sem erros
```

Resumo do fluxo (mapa de navegação do workflow):

```text
[Fase 1 DESIGN]  -> frontend-design + anti-ai-slop -> DESIGN.md aprovado
[Fase 2 BUILD]   -> vercel patterns + animate -> build/lint verdes
[Fase 3 REVIEW]  -> avoid-ai + hermaguard + perf -> QA visual (PDF)
[Gate final]     -> test_quality.py exit 0
```

## Critérios de Aceite (checklist não-regressivo)

- [ ] DESIGN.md com direção visual aprovada (Fase 1 validada pelo usuário).
- [ ] BUILD com perf/a11y; build e lint verdes a cada componente.
- [ ] REVIEW: anti-ai-slop + avoid-ai-writing + hermaguard + perf checklist.
- [ ] Para PDF: renderização via Playwright e QA visual (vision_analyze)
      sem conteúdo cortado nas bordas.
- [ ] Nenhuma skill do stack removida do arquivo.
- [ ] Rodar `python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py`
      → exit 0 (sem regressão).

## Exemplos de execução por fase (comandos reais)

Fase 1 — direção visual documentada:

```bash
cat > DESIGN.md <<'EOF'
# Direção visual
Paleta: fundo #ffffff, acento #1e40af, texto #1a1a1a
Tipografia: serif corpo (Noto Serif/Georgia), mono p/ código
Density: padrão; dark/light: light first
EOF
```

Fase 2 — build e perf:

```bash
npm run build        # ou pnpm build
npx tsc --noEmit     # typecheck
npm run lint         # sem erros
# "audite a perf"  (vercel-react-best-practices)
```

Fase 3 — review/QA:

```bash
# "rode o anti-ai-slop" / "rode o avoid-ai nos textos"
# "hermaguard this"  (bug hunt no diff de frontend)
```

Para PDF (regra do Evandro — SEMPRE este caminho):

```bash
# HTML+CSS -> Playwright headless
~/.hermes/venvs/latebra/bin/python /tmp/gen-pdf.py   # ver pdf-generator
cd ~/.hermes/skills/productivity/pdf/scripts
python pdf_page_image.py saida.pdf --pages 1-N --dpi 150 --out-dir /tmp/qa
# depois vision_analyze em cada PNG: NENHUM conteúdo cortado nas bordas

# QA de perfil visual (se tiver origem de design)
node ~/.hermes/skills/avoid-ai-writing/detector/validate.js ui-copy.md ui-limp.md
```

Verificação de integridade do workflow (gate anti-regressão):

```bash
python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py    # não-regressão
python3 ~/.hermes/skills/software-development/wf-qa/test_tests.py      # teste dos testes
# "hermaguard this"  -> bug hunt adversarial se o diff >3 arquivos
# "rode o anti-ai-slop" -> antes de entregar
```

## Regras duras

- NUNCA pular a Fase 1 (consulta de design) direto para código.
- NUNCA entregar UI sem passar pelo `anti-ai-slop` + `avoid-ai-writing` +
  `hermaguard` + build verde.
- Dúvida de stack (Vite vs Next, Tailwind vs CSS) → decidir na Fase 1 com
  aprovação do usuário, não no meio do build.
