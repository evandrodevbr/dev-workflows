# dev-workflows

Workflows de desenvolvimento que uso no dia a dia, codificados como skills
de agente (formato SKILL.md). Cada um define um processo com fases, passos
de verificação, comandos reais e regras duras - daí sai trabalho consistente
em vez de "confia em mim".

Em geral mexo com Node/TypeScript, NestJS, PostgreSQL, Docker e front em
React. Os workflows refletem isso, mas as fases são neutras o suficiente
pra servir em outros stacks.

## O que tem aqui

| Workflow | Para quê |
|---|---|
| [wf-frontend](workflows/wf-frontend.md) | UI/design/PDF: direção visual antes de codar, anti-AI-slop, perf React, QA visual |
| [wf-backend](workflows/wf-backend.md) | API/backend: contrato antes do handler, defaults seguros, auditoria OWASP, testes |
| [wf-architecture](workflows/wf-architecture.md) | Arquitetura: requisitos mensuráveis, C4, ADR, threat model, revisão |
| [wf-security-review](workflows/wf-security-review.md) | Code review de segurança front+back: CVE conhecidas + consulta de novas (OSV/NVD/GH Advisory) |

Cada SKILL.md funciona no Hermes Agent (e em qualquer agente que leia o
formato): a descrição no frontmatter é o gatilho - quando o contexto bate,
o fluxo carrega sozinho.

## Por que fases com verificação

O problema que isso resolve: agente "acha que fez" mas não tem como provar.
Cada fase termina com passos de verificação (rodar build, rodar teste,
consultar OSV.dev) e os workflows têm critérios de aceite. Sem evidência,
não entrega.

Tem um harness de qualidade no `qa/` que mede isso de forma objetiva:

```bash
cd qa
python3 wf_quality_harness.py        # score por workflow (30+ critérios)
python3 test_quality.py              # gates: não-regressão, skills válidas, verificação por fase
python3 test_tests.py                # teste dos testes: muta e confirma que o harness detecta
```

O `test_tests.py` é o diferencial: ele corrompe o harness e os workflows de
propósito e confirma que o score cai. Se o score não muda com a corrupção,
o detetor é inútil. Isso está sempre verde.

## Segurança: não confiar no cutoff

A skill de segurança tem uma regra dura: o modelo conhece CVE só até o
cutoff de treino. Então "não tem vulnerabilidade" nunca é resposta de
memória - o workflow consulta fontes vivas:

- OSV.dev via safedeps (CVE em tempo real por `package@version`)
- GitHub Advisory Database (via gh api)
- NVD

Leva 3 skills de segurança de fontes primárias (OWASP, OSV.dev, UnitOne
SecuritySkills) e as usa como pilares do review.

## Instalação

Copie os arquivos de `workflows/` para o diretório de skills do seu agente:

```bash
# Hermes Agent
cp workflows/*.md ~/.hermes/skills/software-development/

# Claude Code / agentes com skills dir
mkdir -p ~/.claude/skills && cp workflows/*.md ~/.claude/skills/
```

Para o `wf-security-review`, instale também a skill safedeps e o script
`check_deps.py` (veja `docs/SKILLS.md`) - é o que consulta o OSV.dev.

## Docs

- [docs/SKILLS.md](docs/SKILLS.md) - lista completa das skills usadas,
  origem de cada uma e como instalá-las
- [qa/](qa/) - harness de qualidade + gates + teste dos testes

Licença: MIT.
