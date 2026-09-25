# Quality gate: checagens e configuração

`scripts/quality-gate --tier N` roda as checagens do nível N e dos níveis abaixo, só sobre os arquivos
alterados em relação à branch base (merge-base com `origin/HEAD`, `main` ou `master`). O resultado vai
para `.dev-workflows/gate.json` (ignorado pelo git automaticamente) e uma linha resumida vai para
`.dev-workflows/log.jsonl`.

`--list` mostra o que rodaria e o que está faltando, sem rodar nada.

## Checagens

| Nível | Checagem | Ferramenta | Como é detectada |
|---|---|---|---|
| 0 | lint | script `lint` do package.json, eslint, ruff, `go vet`, clippy | primeira que existir |
| 0 | typecheck | script `typecheck`, `tsc --noEmit`, pyright, mypy | tsconfig ou config do checker |
| 0 | test | script `test`, pytest (usa `.venv` se existir), `go test`, `cargo test` | stack do projeto |
| 0 | secrets | gitleaks, só nos arquivos alterados | binário no PATH |
| 1 | diff-coverage | diff-cover sobre `coverage.xml` | relatório de cobertura presente |
| 1 | semgrep | `semgrep --config p/default --baseline-commit <base>` | binário no PATH |
| 1 | dead-code (info) | knip, vulture | binário no projeto ou PATH |
| 2 | build | script `build` | package.json |
| 2 | mutation | Stryker nos arquivos alterados; mutmut (paths configurados) | config do Stryker ou `[tool.mutmut]` |
| 2 | osv-scanner | `osv-scanner scan source --recursive .` | binário no PATH |
| 2 | architecture | dependency-cruiser, import-linter | arquivo de config |
| 2 | duplication (info) | jscpd | binário no projeto |
| 3 | trivy | vulnerabilidades, misconfig e segredos, HIGH e CRITICAL | binário no PATH |
| 3 | traceability | todo `REQ-NNN` da spec aparece em algum teste | `[spec]` na config |

Estados: `pass`, `fail`, `unverified` (ferramenta ou config ausente, nunca conta como aprovado) e
`info` (só relatório). Veredito: `fail` se algo falhou; `incomplete` se algo ficou não verificado; senão `pass`.

## `.dev-workflows.toml` (opcional, na raiz do projeto)

```toml
timeout = 600                 # segundos por checagem

[commands]                    # substitui o que foi detectado
test = "pnpm vitest run --coverage"
lint = "pnpm eslint ."
mutation = "pnpm stryker run --incremental"

[thresholds]
diff_coverage = 80

[coverage]
report = "coverage/cobertura-coverage.xml"

[spec]                        # nível 3: rastreabilidade requisito -> teste
file = "docs/spec.md"
tests = ["tests", "e2e"]

[[check]]                     # checagem extra; kind = "gate" (padrão) ou "info"
name = "lighthouse"
cmd = "npx lhci autorun"
tier = 2

[[check]]
name = "a11y"
cmd = "npx playwright test e2e/a11y.spec.ts"
tier = 2

[[check]]
name = "api-fuzz"
cmd = "schemathesis run http://localhost:8000/openapi.json --checks all"
tier = 2
```

Frontend, API e carga dependem do app estar de pé, então entram como `[[check]]` do projeto
(Lighthouse CI com orçamento, Playwright com `@axe-core/playwright`, schemathesis, k6 com thresholds).

`DW_GATE=off` desliga o hook de `Stop` numa sessão.
