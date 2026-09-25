---
name: wf-security-review
description: Use para revisão de segurança de código, diff ou PR (frontend e backend), para varrer dependências atrás de CVE, procurar segredos commitados ou auditar auth, API e injeção; também quando o dev-router dispara um gatilho de segurança (auth, dinheiro, dados pessoais, upload, SQL montado à mão, dependência nova, feature com LLM). Consulta fontes vivas de vulnerabilidade com data. Não use para revisão de correção ou estilo sem aspecto de segurança (isso é o agente reviewer) nem para desenhar arquitetura (wf-architecture).
license: MIT
metadata:
  dev-workflows:
    uses: [safedeps, sca-audit, code-review-security, secrets-scan, api-security-review, web-security-review, cve-triage, patch-prioritization, dependency-scanning, hermaguard]
    external: [bola-detector, injection-checker, auth-rbac-scaffold]
---

# Workflow Security Review

O conhecimento de CVE do modelo para na data de corte do treino. Por isso toda revisão consulta
fontes vivas (OSV.dev, GitHub Advisory Database, NVD, CISA KEV) e registra a data da consulta.
**Nunca afirme "sem CVE" sem ter consultado.** Uma revisão sem fonte e sem data já nasce vencida.

Este workflow vem pré-carregado no agente `security-auditor`.

## Profundidade por nível (do `dev-router`)

| Nível | Escopo | Padrão | Ferramentas |
|---|---|---|---|
| 1 com gatilho | só o diff | Top 10 no que o diff toca | gate `--tier 1` (gitleaks, semgrep) |
| 2 | diff + superfície alcançável (rotas, handlers, queries, componentes que usam o código alterado) | ASVS 5.0 L1 | gate `--tier 2` (+ osv-scanner), `safedeps` em toda dependência nova |
| 3 ou auditoria completa | toda a superfície | ASVS 5.0 L2 | gate `--tier 3` (+ trivy), passe adversarial do `hermaguard`, STRIDE contra a arquitetura |

Gate: `"${CLAUDE_PLUGIN_ROOT}/scripts/quality-gate" --tier N`. Checagens e configuração em
[../dev-router/references/quality-gate.md](../dev-router/references/quality-gate.md). Os scanners
são ponto de partida, não substituem a leitura do código.

## Fase 1: SCOPE

1. Delimite o alvo: `git diff --stat <base>` e arquivos não rastreados; front, back ou os dois.
2. Registre a stack, os gerenciadores de pacote e os lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `requirements.txt`, `poetry.lock`, `go.mod`, `Cargo.lock`).
3. No nível 2 ou mais, mapeie a superfície alcançável: quem chama o código alterado e o que fica exposto (rota, fila, webhook, UI).

## Fase 2: HUNT (dependências)

1. `safedeps` nas dependências novas ou alteradas, com versão e ecossistema:
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/safedeps/check_deps.py" express@4.18.2:npm`
   ou o manifest inteiro: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/safedeps/check_deps.py" requirements.txt`.
2. `sca-audit` para alcance (reachability): a função vulnerável é chamada pelo projeto?
3. `cve-triage` e `patch-prioritization` para ordenar por CVSS 4.0, EPSS e CISA KEV.
4. Separe **alcançável** (bloqueia) de **não alcançável** (risco residual registrado).

## Fase 3: CONSULT (fontes vivas)

Responda "há vulnerabilidade nova que eu não conheço?" consultando, com data:

- OSV.dev (já coberto pelo `safedeps`; batch: `POST https://api.osv.dev/v1/querybatch`).
- GitHub Advisory Database: `gh api graphql -f query='{securityAdvisories(first:10, orderBy:{field:PUBLISHED_AT,direction:DESC}){nodes{ghsaId summary severity publishedAt}}}'`.
- NVD: `curl -s "https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=<framework>&resultsPerPage=10"`.
- CISA KEV para saber se já há exploração ativa.
- Página de security ou changelog do framework em uso.

Vulnerabilidade nova que afeta a versão do projeto vira achado HIGH, com a versão de correção.

## Fase 4: CODE REVIEW

Referências atuais: **OWASP Top 10:2025**, **OWASP API Security Top 10 (2023)**, **ASVS 5.0** e,
se a feature chama um LLM, **OWASP LLM Top 10 (2025)**. As skills OWASP vendorizadas ainda citam o
Top 10 de 2021; use o mapa 2021 para 2025 em [references/owasp-2025.md](references/owasp-2025.md).

**Frontend** (`web-security-review`, `code-review-security`):
- renderização de HTML com entrada do usuário (`dangerouslySetInnerHTML`, `v-html`, `innerHTML`);
- segredo no bundle do cliente; token em `localStorage` (prefira cookie `httpOnly`, `Secure`, `SameSite`);
- CSP, links e redirecionamentos montados com entrada do usuário.

**Backend** (`code-review-security`, `api-security-review`; se instaladas, `bola-detector`, `injection-checker`, `auth-rbac-scaffold`):
- autenticação e autorização por objeto (BOLA/IDOR): a query é escopada pelo usuário autenticado?
- injeção: SQL, ORM cru, shell, template, path traversal; SSRF (agora dentro de A01);
- tratamento de condição excepcional (A10:2025): erro que falha aberto, exceção engolida, stack trace na resposta;
- rate limit em escrita e login, CORS com allowlist explícita, segredo nunca em log.

**Segredos**: `secrets-scan` no diff e no histórico (`git log -p -S "<padrão>"`); o gitleaks do gate cobre os arquivos alterados.

**Cadeia de suprimentos** (A03:2025): dependência nova justificada, lockfile commitado, scripts de
instalação suspeitos, versões fixadas no CI.

**Nível 3**: rode o `hermaguard` no diff (edge cases, ataque, blast radius) e confira o threat model
STRIDE do `wf-architecture`: cada ameaça tem mitigação no código?

Cada achado: severidade (CRITICAL, HIGH, MEDIUM, LOW), CWE, referência OWASP, `arquivo:linha`,
passos de exploração, impacto e correção. Diferencie confirmado de suspeita. "Não achei com grep"
não é "não existe": siga o fluxo.

## Fase 5: REPORT + GATE

Relatório com: cabeçalho (nível, escopo, padrão ASVS e a linha "consulta de atualização feita em
<AAAA-MM-DD> via <fontes>"), resumo por severidade, decisão do gate, os achados, tabela de
dependências (pacote, versão, CVE, severidade, corrigida em, alcançável, fonte), veredito do gate de
qualidade com o que ficou não verificado, e riscos aceitos.

Regra do gate: **CRITICAL ou HIGH alcançável em aberto = não aprovado.** MEDIUM entra no próximo
ciclo; LOW e residual ficam registrados como risco aceito. Depois de cada correção, rode de novo a
checagem que acusou o problema e o gate no mesmo nível.

## Regras duras

- Nunca "sem vulnerabilidades" sem consulta a fonte viva com data.
- Nunca CVE sem versão afetada e versão corrigida.
- Nunca expor um segredo encontrado no relatório: cite arquivo, linha e tipo, com o valor mascarado.
- Queries sempre parametrizadas, nunca concatenadas com entrada.
- Correção que muda dependência ou mais de 3 arquivos: nova rodada de revisão.
