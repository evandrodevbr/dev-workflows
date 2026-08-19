---
name: wf-backend
description: "Use p/ backend/API. Fluxo PLAN→BUILD→SECURITY→TEST."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [backend, api, security, rest, sql, auth, workflow]
---

# Workflow Backend/API

Orquestrador obrigatório para TODO trabalho backend: APIs REST/GraphQL,
autenticação, banco de dados, integrações, serviços, jobs. Processo de 4
fases com skills fixas.

## When to Use

Sempre que a tarefa envolver servidor: criar/editar endpoints, auth, schema
DB, integrações, filas, webhooks, ou revisar segurança de backend/models.

## Skills do stack (carregar conforme a fase)

- Segurança multi-stack: `secure-coding` (15 stacks)
- Segurança de API (OWASP): `api-security-review`, `bola-detector`,
  `auth-rbac-scaffold`, `injection-checker`, `openapi-hardener`,
  `security-test-generator`
- Bug hunting adversarial: `hermaguard` (pre-scan + 3 agentes — edge cases,
  ataque, blast radius; read-only, encontra o que está quebrado)
- Locais: `fastapi-uvicorn-wiring` (Python), `rest-graphql-debug`,
  `software-code-quality`, `dependency-cve-audit`, `security-best-practices`,
  `test-driven-development`, `network-audit`

## Fase 1 — PLAN (contrato antes de código)

1. Definir API contract primeiro: rotas, métodos, payloads, status codes,
   erros (RFC 9457 / RFC 7807), rate limit, versionamento.
2. Validar schema: `openapi-hardener` — OpenAPI/Zod/Pydantic saneado antes
   de escrever handler.
3. Definir modelo de dados + migração (idempotente) ANTES de query.
4. Decidir auth: sessão/OAuth/JWT com base no contexto; documentar.
5. Approved do contrato pelo usuário antes de build.
6. VERIFICAR: validar o contrato com `openapi-hardener` (schemas coerentes),
   conferir rate limit + versionamento definidos, e confirmar que o modelo
   de dados tem migração idempotente antes de construir.
7. VERIFICAR (comandos de plano): usar `curl` para provar o contrato contra
   um stub (ex: `curl -i localhost:PORT/health`) e `git log`/branches para
   confirmar que o contrato fica versionado no repo.
8. CHECKPOINT: registrar contrato em `docs/contract.md` (ou OpenAPI) para as
   fases seguintes referenciarem.
9. VERIFICAR (comandos de contrato completo): `grep -c "->" docs/contract.md` — todas as rotas têm status codes esperados; e `grep -c "429\|rate" docs/contract.md` para provar que rate limit está no contrato.
10. VERIFICAR (auth no contrato): `grep -rn "auth\|bearer\|session" docs/contract.md` — decidir e documentar o modelo de auth ANTES do build (não deixar para a Fase 2/3).
11. VERIFICAR (validação de contrato): se OpenAPI, `python3 -m json.tool docs/openapi.json > /dev/null` para provar que o schema é válido em JSON.

**Checklist da fase 1 (validar antes do build):**
- [ ] Rotas/métodos/payloads/status codes definidos e aprovados.
- [ ] Erros no padrão RFC 9457/7807; rate limit e versionamento especificados.
- [ ] `openapi-hardener` validou os schemas (Zod/Pydantic/OpenAPI).
- [ ] Migração de dados idempotente desenhada antes de qualquer query.

**Anti-padrões desta fase:**
- NUNCA escrever handler sem contrato aprovado.
- NUNCA deixar schema "se inferir na mão livre" — definir e validar.
- NÃO esquecer rate limit/versionamento na fase 1 (correção é cara depois).
- NÃO misturar payload v2 com contrato v1 sem versionamento explícito.

## Fase 2 — BUILD (escrever com defaults seguros)

1. `secure-coding` — aplicar padrões da stack em uso (Node/FastAPI/Go/etc).
2. Validação na borda (Zod/Pydantic), erros estruturados, timeouts em
   clientes HTTP e DB, idempotência em mutações.
3. Argon2id p/ senhas, httpOnly cookies p/ sessões, nunca logar segredos.
4. Type-safe boundaries; evitar `any`/`as` descontrolados em TS.
5. VERIFICAR: rodar `secure-coding` como checklist da stack (validação na
   borda, timeouts, idempotência) e `rest-graphql-debug` para confirmar
   que os status codes/mensagens batem com o contrato da Fase 1.
6. VERIFICAR (timeouts): para todo cliente HTTP do serviço, confirmar
   `timeout` definido — `grep -rn "requests\|fetch(" src/ | wc -l` contra
   o número de `timeout` presentes; igual = OK.
7. VERIFICAR (redação de segredos): `grep -rniE "password|secret|token" src/ --include="*.py" --include="*.ts" | grep -i "log\|print"` — zero
   hits é o esperado (nenhum segredo sendo logado).
8. VERIFICAR (queries): conferir que toda listagem tem `LIMIT` — checar
   com `search_files` as chamadas sem paginação antes de seguir.

**Checklist da fase 2 (build seguro):**
- [ ] Validação na borda (Zod/Pydantic) em TODA entrada externa.
- [ ] Erros estruturados; timeouts em clientes HTTP e DB.
- [ ] Mutações idempotentes; transações onde há múltiplas gravações.
- [ ] Senhas com Argon2id; sessões httpOnly; nenhum segredo em log.
- [ ] Type-safe boundaries; sem `any` solto no que atravessa a fronteira.

**Anti-padrões desta fase:**
- NUNCA logar senha/token/dado sensível.
- NUNCA confiar em input externo sem validação na borda.
- NÃO fazer query sem LIMIT/paginação em listas não limitadas.
- NÃO engolir erro com `except: pass` / catch vazio (mascara falha).

## Fase 3 — SECURITY (auditar tudo)

1. `bola-detector` em rotas com `:id`/`findUnique` (Object-Level Authz).
2. `auth-rbac-scaffold` em qualquer fluxo de JWT/login/roles.
3. `injection-checker` em SQL/ORM/shell/templates.
4. `api-security-review` no conjunto final (OWASP API Top 10).
5. `dependency-cve-audit` nas deps do projeto (local).
6. VERIFICAR: consolidar achados P0/P1 por severidade, validar que cada
   rota sensível tem auth + ownership-scope, e re-auditar depois de
   qualquer fix (nada de despachar cego).
7. VERIFICAR (ownership): para rotas com `:id`, conferir que a query usa o
   ID autenticado — `grep -rn "user_id\|user.id\|req.user" src/ | wc -l`
   >= número de rotas protegidas.
8. VERIFICAR (rate limit): `grep -rniE "ratelimit|rate_limit|limiter" src/`
   — toda rota de escrita tem rate limit de referência; se ausente, anotar
   como P2.
9. VERIFICAR (headers/CORS): conferir CSP/CORS configurados (CORS
   allowlist explícita, não `*` com credenciais); `grep -rn "access-control\|csp\|content-security" src/`.
10. VERIFICAR (re-audit pós-fix): após corrigir P0/P1, re-rodar
    `bola-detector` + `api-security-review` e confirmar que os achados
    sumiram (não só mudaram de arquivo).
11. VERIFICAR (critério de aceite de segurança): para cada achado P0/P1,
    reexecutar o teste que o reproduzia e confirmar que agora passa;
    manter o PoC no repositório de testes.
12. VERIFICAR (comandos de confirmação): `grep -c "auth\|ownership" src/`
    deve ser >= número de rotas que mexem em dado de usuário — cada rota
    sensível tem o controle por objeto documentado no código.

**Checklist da fase 3 (segurança):**
- [ ] `bola-detector` limpo em rotas com `:id` (object-level authz).
- [ ] Auth/RBAC (`auth-rbac-scaffold`) cobrindo roles e sessions.
- [ ] `injection-checker` limpo (SQL/ORM/shell/templates).
- [ ] `api-security-review` sem P0/P1 (OWASP API Top 10).
- [ ] `dependency-cve-audit` sem CVEs críticas pendentes.

**Anti-padrões desta fase:**
- NUNCA definir query escopada por outro ID que não o autenticado.
- NUNCA aceitar finding P0/P1 sem evidência de correção.
- NÃO revisar segurança só nos endpoints novos — escopar também os existentes.
- NÃO tratar auditoria como checklist burocrático: achado não resolvido bloqueia.

## Fase 4 — TEST + BUG HUNT (provar antes de entregar)

1. `hermaguard` no diff do backend — dispachar os 3 agentes adversariais
   (Edge Case Hunter, Adversarial Reviewer, Blast Radius). Esperar falhar:
   NUNCA parar em "parece ok"; exigir cobertura de edge cases, races,
   rollback safety e schema drift. Read-only (não corrige — acha).
2. `test-driven-development`: testar o que valida/auth/idempotência.
3. `security-test-generator`: testes de segurança (authz negativa,
   payloads malformados, rate limit).
4. Rodar suíte + lint + typecheck; status real, não suposição.
5. Corrigir os findings P0/P1 do hermaguard como tarefas separadas; rodar
   hermaguard de novo se o fix mudou >3 arquivos.
6. Relatório: contrato entregue, achados de segurança P0/P1/P2 resolvidos,
   bugs caçados pelo hermaguard (por severidade), testes passando (contagem).
7. VERIFICAR (não-regressão QA): rodar `test_quality.py` (gate do workflow)
   — score não pode cair em relação ao baseline.
8. VERIFICAR (cobertura de classes): para rolls em produção, conferir que
   o hermaguard cobriu edge cases, races, rollback safety e schema drift —
   não aceitar "sem achados" sem essa cobertura.
9. VERIFICAR (efeito colateral): se a mudança alterou contrato/DB, rodar
   `rest-graphql-debug` para confirmar status codes e mensagens sem
   regressão.
10. VERIFICAR (cobertura de testes real): `python3 -m pytest --cov=app -q`
    (ou `npm test -- --coverage`) — anotar % de cobertura e garantir que
    os módulos críticos (auth, validação, idempotência) têm pelo menos
    smoke test.
11. VERIFICAR (migração reversível): se houve schema change, rodar
    `alembic downgrade -1`/equivalente em dev para provar rollback; e
    `git diff --stat` para conferir o escopo do que está indo pra frente.
12. VERIFICAR (config por ambiente): `grep -rn "getenv\|os.environ\|process.env" src/` — toda configuração via env, sem valores hardcoded que
    vazam para prod.
13. VERIFICAR (comandos de entrega): `python3 -m pytest -q && npm run build` (ou stack equivalente) como smoke final; e `git status` para
    confirmar que os artefatos de teste não vazaram pro repo.
14. VERIFICAR (critério de entrega): relatório final só fecha quando cada
    item do checklist da Fase 4 está marcado — sem exceção de última hora
    não auditada.

**Checklist da fase 4 (gate de entrega):**
- [ ] `hermaguard` rodado; findings CRITICAL/HIGH zero ou com plano de fix.
- [ ] TDD: testes de validação, auth e idempotência verdes.
- [ ] `security-test-generator`: authz negativa, payloads mal, rate limit.
- [ ] Suíte + lint + typecheck verdes (contagem real, não suposição).
- [ ] Findings P0/P1 corrigidos e re-verificados (hermaguard rodado de novo
      se o fix alterou >3 arquivos).

**Anti-padrões desta fase:**
- NUNCA rodar hermaguard em código com testes quebrados (polui o review).
- NUNCA dar "suíte passando" sem ter executado a suíte.
- NÃO aceitar "hermaguard não achou nada" sem exigir a cobertura por classe
  (edge cases, races, rollback, schema drift).
- NÃO reportar achado P0/P1 como resolvido sem a verificação de volta.

## Comandos de Verificação (executáveis)

```bash
# Gate de qualidade do próprio workflow (sem regressão)
python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py

# Testes + meta-testes (prova que o harness detecta regressão)
python3 ~/.hermes/skills/software-development/wf-qa/test_tests.py

# Audit OWASP de um endpoint/controller
# (skill api-security-review) — veja a skill

# CVE nas deps do projeto
# (skill dependency-cve-audit) — veja a skill

# Bug hunt adversarial no diff (read-only)
# (skill hermaguard: "hermaguard this")
```

## Critérios de Aceite (checklist não-regressivo)

- [ ] Contrato aprovado (PLAN) antes de qualquer handler.
- [ ] BUILD com defaults seguros; `secure-coding` validado na stack.
- [ ] SECURITY: bola/auth/injection/api-review/CVE rodados; P0/P1 resolvidos.
- [ ] TEST: hermaguard + TDD + security-test-generator; suíte verde com
      contagem real.
- [ ] Nenhuma skill do stack removida do arquivo.
- [ ] Rodar `python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py`
      → exit 0 (sem regressão).

## Exemplos de execução por fase (comandos reais)

Fase 1 — validar contrato antes de codar:

```bash
# Lista de rotas planejadas (contrato em aberto)
cat > docs/contract.md <<'EOF'
POST /api/v1/users   -> 201 | 400 | 401 | 409 | 429
GET  /api/v1/users/:id -> 200 | 404 | 403
Erros: RFC 9457 (application/problem+json)
EOF
```

Fase 2 — build seguro (exemplo FastAPI + Pydantic):

```bash
# Rodar a stack e conferir a OpenAPI gerada
uvicorn app.main:app --reload   # ou npm run dev
curl -s localhost:8000/openapi.json | python3 -m json.tool > /tmp/openapi.json
python3 -c "import sys,json; d=json.load(open('/tmp/openapi.json')); print('schemas:', len(d.get('components',{}).get('schemas',{})))"

# Validação de contrato contra a OpenAPI real
curl -s localhost:8000/health -i | head -5        # status codes do health
curl -s -X POST localhost:8000/api/v1/users -d '{}' -i | head -5  # 400 esperado
```

Fase 3 — auditoria de segurança:

```bash
# Rodar as skills de auditoria OWASP (veja cada skill p/ uso exato)
# bola-detector: "audite rotas com :id" / auth-rbac-scaffold: "valide o fluxo de login"
# injection-checker: "escaneie SQL/ORM" / api-security-review: "revisão OWASP do conjunto"
# dependency-cve-audit: "audite as dependências" (skill local)
```

Fase 4 — testes e bug hunt:

```bash
python3 -m pytest -v                   # ou npm test
python3 ~/.hermes/skills/software-development/wf-qa/test_quality.py  # gate do workfl
# "hermaguard this"  (bug hunt adversarial no diff)
```

Gates anti-regressão (rodar junto com o fluxo):

```bash
python3 ~/.hermes/skills/software-development/wf-qa/test_tests.py   # teste dos testes
# verifica que o harness DETECTA regressão (mutações sempre derrubam o score)
python3 -m pytest tests/security/ -x   # se existir suíte de segurança
```

## Regras duras

- NUNCA escrever handler antes do contrato aprovado.
- NUNCA entregar endpoint sem passar pelas 4 fases (security + testes +
  hermaguard).
- Rota que mexe em dado do usuário → ownership-check obrigatório (query
  escopada ao ID autenticado).
- Tests vermelhos = fixar primeiro; hermaguard não roda em código quebrado.
