---
name: wf-frontend
description: Use para trabalho de frontend e UI - componentes, páginas, layouts, estilos, design system, animação, acessibilidade, redesign de tela existente, e geração de PDF ou documento visual a partir de HTML. Fluxo DESIGN, BUILD, REVIEW com profundidade definida pelo nível do dev-router. Não use para backend ou API (wf-backend), para bug sem mudança visual (wf-bugfix) nem para refactor sem mudança de comportamento (wf-refactor).
license: MIT
metadata:
  dev-workflows:
    uses: [design-taste-frontend, redesign-existing-projects, lean-code, dev-router]
    external: [frontend-design, web-design, vercel-react-best-practices, vercel-composition-patterns, animate, impeccable, avoid-ai-writing]
---

# Workflow Frontend

A profundidade vem do nível que o `dev-router` definiu. Cada fase diz a partir de qual nível roda.

| Nível | O que roda |
|---|---|
| 0 | só o gate (`--tier 0`) |
| 1 | ajuste de UI: siga o design system que já existe; sem DESIGN.md, sem aprovação; BUILD enxuto + gate `--tier 1` |
| 2 | tela ou componente novo: DESIGN curto, BUILD, REVIEW com `ui-critic` e `reviewer` |
| 3 | fluxo ou design system novo: DESIGN com aprovação do usuário, BUILD por tarefas, REVIEW completo |

## Skills (carregar só na fase que usa)

- **Tela nova:** `design-taste-frontend` (~35 mil tokens; só para tela nova, nunca para ajuste) e, se instalada, `frontend-design`.
- **Tela existente:** `redesign-existing-projects` (audita antes de mudar).
- **Auditoria anti "UI de IA":** `impeccable` (`/impeccable audit`, externa).
- **React/Next:** `vercel-react-best-practices` (performance), `vercel-composition-patterns` (composição).
- **Motion:** `animate`. **Microcopy:** `avoid-ai-writing`.
- Sempre: `lean-code`.

Externas são opcionais: se não estiverem instaladas, siga as regras desta página. Instalação em `docs/SKILLS.md`.

## Fase 1, DESIGN (nível 2+, tela ou componente novo)

Nível 1 pula esta fase e usa os tokens, componentes e padrões que o projeto já tem.

1. `explorer` mapeia o design system existente: tokens (cor, tipografia, espaçamento), componentes reutilizáveis, biblioteca de UI. Reaproveitar vem antes de criar.
2. Defina a direção: paleta, tipografia, densidade, claro/escuro. Tela nova usa `design-taste-frontend`; redesign usa `redesign-existing-projects`.
3. Registre as decisões em `DESIGN.md` (curto: tokens e o porquê).
4. Nível 3, ou decisão que é do usuário (identidade visual, troca de stack): pare e peça aprovação antes de codar. Nível 2 segue sem parar se a direção vem do design system existente.

Evite: gradiente roxo genérico, glassmorphism sem motivo, cards idênticos em grade, ícone decorativo sem função, dois design systems na mesma tela.

## Fase 2, BUILD (nível 1+)

1. `implementer` (ou você, em mudança pequena) implementa com `lean-code`: componente e hook existentes antes de novos; CSS e HTML nativos antes de JS.
2. **Estados em todo fluxo com dados:** carregando, vazio, erro, sucesso.
3. **Acessibilidade por padrão:** HTML semântico, foco visível e em ordem, rótulos, contraste de texto >= 4.5:1. ARIA só quando o HTML não resolve.
4. **Responsivo mobile-first**, testado em 375 px e 1280 px.
5. **Composição:** compound components em vez de explosão de props booleanas (`isX`, `showY`).
6. **Motion com propósito** (estado, entrada, feedback) e `prefers-reduced-motion` respeitado.
7. React/Next: sem waterfall de dados, sem re-render em cascata, imagem com dimensões, código dividido por rota.
8. TypeScript sem `any` nem cast forçado para "passar".
9. Rode o gate a cada componente relevante, não só no fim.

Entrada de usuário renderizada como HTML, `dangerouslySetInnerHTML`, `eval`, `postMessage` ou mudança de CSP disparam `security-auditor` (XSS/CSP).

## Fase 3, REVIEW (nível 2+)

1. `ui-critic`: screenshot em 375 e 1280, estados, a11y, padrões genéricos. Se `impeccable` estiver instalada, `/impeccable audit`.
2. `reviewer`: correção e simplicidade do diff.
3. `avoid-ai-writing` nos textos entregues ao usuário (labels, vazios, erros), se instalada.
4. Corrija o que for `bloqueante` ou `importante` e rode os dois de novo só no que mudou.

## Gate

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/quality-gate" --tier N
```

Lint, typecheck, testes, segredos e build rodam sozinhos. O que depende do app de pé (Lighthouse,
axe, bundle, regressão visual) entra como `[[check]]` no `.dev-workflows.toml` do projeto: modelos em
[references/checks.md](references/checks.md). Lista completa de checagens:
`skills/dev-router/references/quality-gate.md`.

Metas de referência (nível 2+): LCP <= 2,5 s, INP <= 200 ms (TBT como proxy em laboratório),
CLS <= 0,1; axe sem violação `serious` ou `critical`; bundle dentro do limite do `size-limit`.

O `verifier` roda o gate e devolve a evidência. Ferramenta ausente aparece como "não verificado":
diga isso ao usuário, nunca chame de testado.

## PDF e documento visual

Sempre HTML + CSS renderizado pelo Playwright (`page.pdf()`), depois cada página convertida em PNG e
inspecionada com Read: nada cortado na margem, tabela longa quebrando entre páginas. Nunca
reportlab platypus direto para tabelas longas. Método completo: [references/pdf.md](references/pdf.md).

## Aceite

- [ ] Nível declarado; fases puladas coerentes com ele.
- [ ] Nível 2+: direção registrada em `DESIGN.md` (aprovada pelo usuário no nível 3).
- [ ] Estados carregando, vazio, erro e sucesso em todo fluxo com dados.
- [ ] Acessível: semântica, foco, rótulos, contraste >= 4.5:1; axe sem `serious`/`critical` se configurado.
- [ ] Responsivo em 375 px e 1280 px, sem corte ou sobreposição.
- [ ] `prefers-reduced-motion` respeitado; animação só com propósito.
- [ ] Sem explosão de props booleanas; composição com compound components.
- [ ] Gate `pass`, ou falhas explicadas; "não verificado" listado ao usuário.
- [ ] PDF: páginas renderizadas e inspecionadas, nada cortado.
