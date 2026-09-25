---
name: wf-security-review
description: "Code review de segurança (front+back). OSV/NVD + OWASP."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [security, code-review, cve, owasp, sast, sca, workflow, devsecops]
---

# Workflow Security Code Review (front + backend)

Orquestrador obrigatório para todo code review de segurança — frontend E
backend. Cobre: revisão de código (OWASP), vulnerabilidades conhecidas em
dependências, E consulta de NOVAS vulnerabilidades nos lugares certos
(OSV.dev, NVD, GitHub Advisory) para que o review esteja sempre atualizado,
não preso ao cutoff de treino do modelo.

## When to Use

- "revisa a segurança desse código/PR/diff" (front ou back)
- "escaneia dependências por CVEs" / "alguma lib vulnerável?"
- "tem vulnerabilidade nova conhecida pra X?" (consulta de atualização)
- "audita auth/API/injeção" / "procura segredos commitados"
- QUALQUER review de merge que mexa em dado sensível ou rota nova
- Pré-commit ou pré-deploy como etapa de segurança

## Skills do stack (3 principais + auxiliares)

**As 3 skills de segurança atuais (instaladas de fontes primárias):**
1. `safedeps` (Jeneidi) — grounding em OSV.dev em tempo real: consulta
   `package@version` e traz CVE com severidade e fix. Cobre o gap de o
   modelo só conhecer vulns até o cutoff. CLI: `check_deps.py`.
2. `sca-audit` (OWASP secure-agent-playbook) — SCA (Supply Chain Analysis)
   de dependências com análise de alcance (reachability), CWE mapping.
3. `code-review-security` (OWASP secure-agent-playbook) — code review de
   segurança sistemático mapeado a OWASP Top 10 + ASVS.

**Auxiliares (carregar por contexto):**
- `secrets-scan` (OWASP) — busca credenciais/API keys no código e git history
- `api-security-review` + `bola-detector` + `auth-rbac-scaffold` +
  `injection-checker` (OWASP/API) — revisão de API
- `web-security-review` (OWASP) — web app OWASP Top 10
- `cve-triage` + `patch-prioritization` (UnitOne/SecuritySkills) — priorizar
  CVE por CVSS 4.0 / EPSS / CISA KEV
- Locais: `dependency-cve-audit`, `hermaguard` (caça bugs adversariais),
  `security-threat-model`

## Fase 1 — SCOPE (definir alvo antes de auditar)

1. Identificar o que está no escopo: diff/PR, arquivos, front, back, ambos.
2. Registrar stack do projeto (linguagens, frameworks, package managers,
   se há lockfile: package-lock.json / requirements.txt / go.mod / etc).
3. Rodar o código? Identificar se há ambiente local testável.
4. VERIFICAR: `git status` + `git diff --stat` para delimitar o alvo real.
5. Checkpoint: confirmar escopo com o usuário antes de gastar auditoria.

**Checklist da fase 1:**
- [ ] Escopo delimitado (arquivos/diff/PR)
- [ ] Stack e lockfiles identificados
- [ ] Alvo confirmado

## Fase 2 — HUNT (vulnerabilidades conhecidas — dimensão de dependências)

1. `sca-audit` — scan de dependências com análise de alcance; mapear CVEs
   por severidade e reachable/unreachable.
2. `safedeps` — para cada dependência-chave do manifest, consultar OSV.dev:
   `python3 ~/.hermes/skills/safedeps/check_deps.py "pkg@version"` (ou via
   manifest completo) — traz CVE reais com fix (o modelo NÃO sabe CVE nova
   do cutoff pra frente; o OSV.dev sim).
3. `cve-triage` / `patch-prioritization` — priorizar achados por
   CVSS 4.0 / EPSS / CISA KEV quando disponível.
4. `dependency-cve-audit` (local) — varredura das deps do projeto atual.
5. VERIFICAR: consolidar lista de CVE com severidade + versão afetada +
   versão fixa; separar reachable (devem ser bloqueantes) de non-reachable
   (registrar como risco residual).
6. CHECKPOINT: apresentar sumário de CVE antes de partir para o code review.

**Comandos úteis:**
```bash
python3 ~/.hermes/skills/safedeps/check_deps.py "lodash@4.17.20"   # 1 pkg
python3 ~/.hermes/skills/safedeps/check_deps.py -f package-lock.json  # manifest
# veja a skill sca-audit p/ reachability; cve-triage p/ priorização
```

**Anti-padrões desta fase:**
- NUNCA afirmar "sem CVE" sem ter CONSULTADO OSV.dev (memória do modelo é
  congelada no cutoff).
- NÃO tratar CVE de dependência transitiva não-reachable como crítica igual
  a reachable — reportar com nuance.
- NUNCA rodar scan em lockfile sem conferir o package manager certo.

**Comandos reais (Fase 2):**
```bash
python3 ~/.hermes/skills/safedeps/check_deps.py "express@4.18.2"
python3 ~/.hermes/skills/safedeps/check_deps.py -f package-lock.json
# alternatives: npm audit --json / pip-audit -r requirements.txt / trivy fs .
```

## Fase 3 — CONSULT (novas vulnerabilidades — atualização contínua)

O objetivo é responder "há vulnerabilidade NOVA que eu não conheço?" — o
modelo só sabe até o cutoff; consultar fontes vivas:

1. OSV.dev (API aberta, sem key) — já coberto na Fase 2 via safedeps.
2. GitHub Advisory Database — via `gh api`:
   `gh api graphql -f query='{securityAdvisories(first:10, orderBy:{field:PUBLISHED_AT,direction:DESC}){nodes{ghsaId,summary,severity,publishedAt}}}'
3. NVD — via API (key opcional): consultar CPE do stack ou CVEs recentes do
   framework em uso (`curl -s "https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=..."`).
4. Registros de framework (ex: changelog/security de Next.js, Express,
   NestJS, FastAPI) — advisories recentes do framework do projeto.
5. VERIFICAR: para LIB versão X e FRAMEWORK Y, registrar qual fonte foi
   consultada e a data — sem "não tem" sem fonte.
6. CHECKPOINT: se alguma vuln nova afeta o stack do projeto, tratar como
   finding HIGH e sugerir upgrade.

**Comandos úteis:**
```bash
gh api graphql -f query='{securityAdvisories(first:10, orderBy:{field:PUBLISHED_AT,direction:DESC}){nodes{ghsaId,summary,severity,publishedAt}}}'
curl -s "https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=nextjs&resultsPerPage=10"
# OSV batch: curl -s -X POST https://api.osv.dev/v1/querybatch -d '@manifests.json'
```

**Anti-padrões desta fase:**
- NUNCA responder "não tem vulnerabilidade nova" sem citar fonte viva + data.
- NÃO confiar no cutoff do modelo para saber CVE recente — sempre consultar.
- NÃO esquecer de incluir data da consulta (revisão vence se ficar velho).

## Fase 4 — CODE REVIEW (front + backend, OWASP)

Frontend (`web-security-review` + `code-review-security`):
1. XSS/injeção em renderização (dangerouslySetInnerHTML, v-html, innerHTML).
2. Exposição de segredos no client (API keys, tokens em bundle).
3. Containers: loads, links com user input, cookies httpOnly/secure.
4. `secrets-scan` — credenciais no código e git history.
5. Auth de frontend: fluxo de tokens, storage inseguro (localStorage p/ JWT).

Backend (`code-review-security` + `api-security-review` + `bola-detector` +
`auth-rbac-scaffold` + `injection-checker`):
1. AuthN/AuthZ: rotas sem auth, IDOR/BOLA (`bola-detector`), RBAC.
2. Input validation: SQLi, XSS, command injection, SSRF, path traversal
   (`injection-checker`).
3. Segredos: env vars, nunca logar senha/token.
4. Rate limit, erros sem vazar stack trace, CORS correto.
5. `hermaguard` (opcional) p/ caça adversarial de bugs no mesmo diff.
6. VERIFICAR: para cada rota com `:id`, rodar `bola-detector` de novo (IDOR
   é o achado nº1 em API) e para cada query, `injection-checker`.
7. VERIFICAR: rodar `secrets-scan` no diff E git history antes de fechar —
   credencial commitada em algum commit antigo ainda vaza.
8. VERIFICAR: conferir erros sem stack trace (grep por exceptions/console no
   cliente) e CORS/headers (`grep -rn "access-control\|csp"`).
9. VERIFICAR: `grep -rn "localStorage\|sessionStorage" src/` — nenhum JWT
   sensível em storage de frontend (usar httpOnly cookie).
10. VERIFICAR: confirmar rate limit em rotas de escrita (`grep -rniE "limiter|rate"`) e que respostas não vazam caminho interno.

**Output por finding:** Severidade (Critical/High/Med/Low) + CWE + OWASP ref +
Arquivo:linha + Evidência + Remediação.

**Anti-padrões desta fase (front + back):**
- NUNCA approve sem reportar achado de AuthN/AuthZ ou injection como mínimo.
- Padrão de coerência — NÃO misturar "parece ok" com achado sem evidência.
- NÃO confundir "não achei com grep" com "não existe" — checar fluxo inteiro.
- NÃO focar só no front quando o fix toca o back (IDOR/BOLA vive no back).

**Comandos de auditoria (Fase 4):**
```bash
# segredos: busca em código e git history
grep -rniE "(api[_-]?key|secret|password|token|bearer)" src/ | grep -v node_modules
git log -p --all -S "sk-" --oneline | head   # chave vazada em commit antigo
# headers/CORS/rate limit
grep -rniE "access-control|content-security-policy" src/
grep -rniE "ratelimit|rate_limit|limiter|express-rate" src/
python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py  # gate
```

## Fase 5 — REPORT + GATE (entregar e decidir)

1. Consolidar tudo: sumário (nº por severidade), findings detalhados,
   tabela de CVE com fonte/estado/reachable/fix, e status "consulta de
   atualização feita em <data> via <fontes>".
2. GATE: Critical/High reachable → BLOQUEAR merge até corrigir. Medium →
   tratar no próximo ciclo. Low/residual → registrar risco aceito.
3. Re-auditar após fixes: re-rodar as checagens que acusaram P0/P1.
4. VERIFICAR: `python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py`
   (gate não-regressivo do stack de workflows).
5. Relatório final em markdown (report.md) + resumo em chat.
6. VERIFICAR (comandos de report): gerar `security-report.md` com
   `find . -maxdepth 2 -name "*.md" | sort` conferindo artefatos, e
   `grep -c "CVE-" security-report.md` para ter contagem explícita no doc.
7. VERIFICAR (data da consulta): `grep -i "data da consulta\|20[2-9][0-9]-" security-report.md` — sem revisão sem carimbo de data (ela vence).

**Checklist de entrega:**
- [ ] Os 3 pilares rodados: safedeps (OSV), sca-audit, code-review-security.
- [ ] Consulta de novas vulns feita em fonte viva (OSV/GH Advisory/NVD) com data.
- [ ] Findings com CWE + OWASP + evidência + remediação.
- [ ] GATE aplicado (block/allow) por severidade/reachability.
- [ ] Nenhuma skill do stack removida; test_quality.py passando.

## Regras duras

- NUNCA afirmar "sem vulnerabilidades" sem consultar OSV.dev/GH Advisory
  (modelo tem cutoff; fonte viva não).
- NUNCA reportar CVE sem incluir versão afetada + versão fixa.
- NUNCA blocker Critical/High reachable "para depois" — bloquear merge.
- NUNCA logar/expor segredo durante o review (nem no relatório).
- Re-auditar sempre que o fix tocar >3 arquivos ou mudar dependência.
- SQL/queries: sempre parâmetros posicionais, nunca concatenação de input.
