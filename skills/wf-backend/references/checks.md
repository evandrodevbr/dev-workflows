# Checagens de backend que dependem do app de pé

Estas checagens entram como `[[check]]` no `.dev-workflows.toml` do projeto, porque precisam de
servidor, banco ou carga reais. O gate roda cada uma no nível indicado e trata ferramenta ausente
como "não verificado".

## Contrato de exemplo (`docs/contract.md`)

```text
POST /api/v1/users      -> 201 | 400 | 401 | 409 | 429
GET  /api/v1/users/:id  -> 200 | 403 | 404
Erros: RFC 9457 (application/problem+json)
Paginação: ?cursor=&limit= (limit máx. 100)
Rate limit: 60 req/min por usuário em escrita; 429 com Retry-After
Auth: sessão em cookie httpOnly; rotas /admin exigem papel admin
```

## Receitas de `[[check]]`

```toml
# Fuzz da API a partir do OpenAPI: zero 5xx e zero violação de schema
[[check]]
name = "api-fuzz"
cmd = "schemathesis run http://localhost:8000/openapi.json --checks all"
tier = 2

# Contrato com consumidores (quando outro serviço usa a API)
[[check]]
name = "pact-verify"
cmd = "npx pact-provider-verifier --provider-base-url http://localhost:8000 --pact-broker-url $PACT_BROKER_URL"
tier = 2

# Migração reversível num banco descartável (up -> down -> up)
[[check]]
name = "migration-roundtrip"
cmd = "alembic upgrade head && alembic downgrade -1 && alembic upgrade head"
tier = 2

# Carga no caminho quente, com threshold de p95 no próprio script k6
[[check]]
name = "load"
cmd = "k6 run --quiet load/hot-path.js"
tier = 3
```

No k6, o threshold fica no script e faz o comando sair com erro quando estoura:

```js
export const options = {
  vus: 20, duration: "30s",
  thresholds: { http_req_duration: ["p(95)<300"], http_req_failed: ["rate<0.01"] },
};
```

Para a migração, suba um Postgres descartável (testcontainers ou `docker run --rm -p 5433:5432 postgres`)
e aponte a `DATABASE_URL` do comando para ele. Nunca rode o roundtrip num banco com dados reais.

## Queries novas

- Rode `EXPLAIN (ANALYZE, BUFFERS)` em cada query nova com volume parecido com o de produção; seq scan
  em tabela grande pede índice ou filtro.
- N+1: conte as queries de uma requisição de listagem (log do ORM ou `django-debug-toolbar`,
  `nplusone`, `bullet`). O número não pode crescer com o tamanho da página.
