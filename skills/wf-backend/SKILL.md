---
name: wf-backend
description: Use para trabalho de backend e API - endpoint REST/GraphQL, autenticação, schema e migração de banco, integração, fila, webhook, job. Contrato antes do handler, defaults seguros, auditoria OWASP e gate de qualidade no nível que o dev-router definiu. Não use para UI (wf-frontend), para correção pontual sem mudança de contrato (wf-bugfix) nem para desenho de sistema com vários serviços (wf-architecture primeiro).
license: MIT
metadata:
  dev-workflows:
    uses: [api-security-review, safedeps, sca-audit, secrets-scan, hermaguard]
    external: [secure-coding, bola-detector, auth-rbac-scaffold, injection-checker, openapi-hardener, security-test-generator]
---

# Workflow Backend/API

O `dev-router` define o nível. Cada fase diz a partir de qual nível roda. No nível 1, a mudança segue
o `wf-bugfix` (ou `wf-refactor`) com as regras de build seguro abaixo e o gate `--tier 1`.

## Fase 1: PLAN, contrato antes do código (nível 2+)

Nível 0 e 1 pulam esta fase. No nível 3, o `planner` escreve a spec EARS e esta fase vira a parte de
API dela.

1. `explorer` mapeia rotas, modelos e validações que já existem. Reaproveite antes de criar.
2. Contrato em `docs/contract.md` ou OpenAPI: rotas, métodos, payloads, status codes, erros em
   RFC 9457 (`application/problem+json`), paginação, rate limit e versionamento.
3. Schemas validados na borda (Zod, Pydantic, OpenAPI). `openapi-hardener`, se instalado, saneia.
4. Modelo de dados e migração desenhados antes da query: idempotente e reversível.
5. Modelo de auth decidido e escrito no contrato (sessão, OAuth, JWT) com o motivo.
6. Contrato com decisão de produto passa pelo usuário antes do build.

## Fase 2: BUILD com defaults seguros (nível 1+)

`implementer` com TDD: comportamento novo começa por teste que falha. Regras:

- Validação de toda entrada externa na borda; nada de confiar em payload, header ou query.
- Erros estruturados (RFC 9457); nunca `except: pass` nem `catch` vazio.
- Timeout em todo cliente HTTP e conexão de banco; retry só em operação idempotente.
- Mutações idempotentes (chave de idempotência em POST que cobra ou cria); transação quando há várias escritas.
- Toda listagem com paginação e limite máximo.
- Query de dado do usuário escopada ao ID autenticado (ownership), nunca a um ID vindo do cliente.
- Senha com Argon2id; sessão em cookie `httpOnly`, `Secure`, `SameSite`; nenhum segredo, token ou senha em log.
- CORS com allowlist explícita (nunca `*` com credenciais); configuração por variável de ambiente.
- Tipos seguros na fronteira: sem `any` ou cast forçado no que entra ou sai.
- `secure-coding`, se instalado, como checklist da stack.

Dependência nova: justifique (`lean-code`) e consulte `safedeps` antes de instalar.

## Fase 3: SECURITY (nível 2+, ou nível 1 com gatilho)

Gatilhos do `dev-router` (auth, dinheiro, dado pessoal, SQL montado à mão, upload, shell, LLM) chamam
o `security-auditor`, que segue o `wf-security-review` com escopo no diff e no que ele alcança.

- Referências: OWASP API Security Top 10 (2023) e OWASP Top 10:2025.
- ASVS 5.0: L1 no nível 2, L2 no nível 3.
- Vendorizadas: `api-security-review` (OWASP API Top 10), `secrets-scan`, `sca-audit`, `safedeps` (CVE ao vivo no OSV.dev).
- Externas, se instaladas: `bola-detector` em rotas com `:id`, `auth-rbac-scaffold` em login e papéis, `injection-checker` em SQL/ORM/shell/template.
- Achado P0/P1 bloqueia a entrega; depois do fix, rode a auditoria de novo e confirme que sumiu.
- Nível 3 ou gatilho disparado: `hermaguard` no diff como passe adversarial (edge cases, ataque, blast radius).

## Fase 4: TEST + GATE (nível 1+)

1. Testes de validação, auth negativa (outro usuário, sem token, papel errado) e idempotência.
   `security-test-generator`, se instalado, ajuda a gerar os casos negativos.
2. Gate: `"${CLAUDE_PLUGIN_ROOT}/scripts/quality-gate" --tier N`. Já cobre lint, typecheck, testes,
   gitleaks, semgrep, cobertura do diff, mutação e osv-scanner conforme o nível.
3. Checagens que dependem do app de pé entram como `[[check]]` no `.dev-workflows.toml` do projeto
   (receitas em [references/checks.md](references/checks.md)):
   - schemathesis contra o OpenAPI (nível 2+): zero erro 5xx e zero violação de schema;
   - Pact quando há outro serviço consumindo a API;
   - migração up, down, up num banco descartável (testcontainers) quando o schema muda;
   - `EXPLAIN` das queries novas e detecção de N+1 quando há query nova;
   - k6 com thresholds de p95 quando a mudança toca um caminho quente (nível 3 ou gatilho de performance).
4. No nível 2+, `reviewer` revisa o diff; no nível 3, `verifier` roda o gate final e devolve a evidência.

Detalhes do gate e da configuração: [../dev-router/references/quality-gate.md](../dev-router/references/quality-gate.md).

## Relatório

Contrato entregue (nível 2+), achados de segurança por severidade e o que foi corrigido, testes que
provam (nomes e contagem real), veredito do gate com o que ficou não verificado, e linhas líquidas.

## Critérios de aceite

- [ ] Nível 2+: contrato aprovado antes do primeiro handler.
- [ ] Toda entrada externa validada na borda; erros em RFC 9457.
- [ ] Queries de dado do usuário escopadas ao ID autenticado.
- [ ] Nenhum P0/P1 de segurança aberto; CVEs consultados ao vivo, com data.
- [ ] Migração reversível provada (up, down, up) quando o schema mudou.
- [ ] Gate `pass`, ou `incomplete` com a lista do que não foi verificado dita ao usuário.

## Regras duras

- Nunca escrever handler antes do contrato aprovado (nível 2+).
- Nunca rodar `hermaguard` ou auditoria em código com testes vermelhos; corrija os testes primeiro.
- Nunca dizer "suíte passando" sem ter rodado a suíte.
