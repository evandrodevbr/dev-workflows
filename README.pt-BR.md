<div align="center">

# Dev Workflows

**Workflows de agente como arquivos SKILL.md**: frontend, backend, arquitetura e code review de segurança que nunca pulam a verificação.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](qa/wf_quality_harness.py)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-1.0-8A2BE2)](https://agentskills.io)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/evandrodevbr/dev-workflows/pulls)

Transforme seu agente de código num processo repetível e verificável. Cada workflow define fases, passos de verificação concretos, comandos reais e regras duras. O agente entrega trabalho que dá pra *checar*, não só *afirmar*.

**🇺🇸 [Read this in English](README.md)**

</div>

---

## Por quê

Agente é ótimo pra gerar código e péssimo pra admitir que não sabe. Este projeto resolve a segunda parte.

Cada workflow força o agente a **provar** o trabalho em cada fase:

- **Passos de verificação**: rodar build, rodar testes, chamar a API, consultar o registry. Não "acho que funciona".
- **Critérios de aceite**: portões com checkbox que precisam estar marcados pra fase fechar.
- **Regras duras**: "nunca faça merge com build vermelho", "nunca afirme 'sem CVE' sem consultar o OSV.dev".
- **Harness de QA**: um placar que mede a qualidade dos workflows de forma objetiva, mais meta-testes que corrompem o harness pra provar que ele detecta regressão.

## Sumário

- [Workflows](#workflows)
- [Segurança: não confie no cutoff de treino](#segurança-não-confie-no-cutoff-de-treino)
- [Skills usadas e seus donos](#skills-usadas-e-seus-donos)
- [Começo rápido](#começo-rápido)
- [O harness de QA](#o-harness-de-qa)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Licença](#licença)

## Workflows

| Workflow | Arquivo | Cobre |
|---|---|---|
| 🎨 **Frontend / UI** | [workflows/wf-frontend.md](workflows/wf-frontend.md) | Direção de design antes do código, anti-AI-slop, performance React, QA visual de PDFs |
| ⚙️ **Backend / API** | [workflows/wf-backend.md](workflows/wf-backend.md) | Contrato antes do handler, defaults seguros, auditoria OWASP, testes + caça de bugs adversarial |
| 🏗️ **Arquitetura** | [workflows/wf-architecture.md](workflows/wf-architecture.md) | Requisitos mensuráveis, diagramas C4, ADRs, threat modeling, revisão |
| 🛡️ **Security review** | [workflows/wf-security-review.md](workflows/wf-security-review.md) | Code review (front + back), CVEs conhecidas **e** consulta ao vivo de novas |

Cada arquivo é um `SKILL.md` padrão. A `description` no frontmatter é o gatilho: quando o contexto do agente bate, o workflow carrega sozinho. Funciona no [Hermes Agent](https://hermes-agent.nousresearch.com), Claude Code e qualquer coisa que leia o formato Agent Skills.

## Segurança: não confie no cutoff de treino

O conhecimento de CVEs de um modelo para na data do treinamento. Qualquer coisa divulgada depois disso, ele nunca viu, então "não tem vulnerabilidade" vindo de memória é um chute, não resposta.

O workflow de segurança nasceu desse fato:

```
Código/diff → SCOPE → HUNT (CVEs conhecidas) → CONSULT (fontes vivas) → CODE REVIEW → REPORT + GATE
                    │                            │
                    │                            └─ OSV.dev · GitHub Advisory DB · NVD
                    └──────────────┘
```

Todo security review **precisa** consultar fontes vivas e carimbar a data. Review sem fonte e sem data vence na hora.

## Skills usadas e seus donos

Os workflows carregam essas skills por contexto. Os três pilares do security review vêm de fontes primárias de segurança (OWASP, OSV.dev, UnitOne SecuritySkills), não da memória de um modelo.

### 🛡️ Security review: os três pilares

| Skill | O que faz | Dono |
|---|---|---|
| [`safedeps`](https://github.com/Jeneidi/safedeps) | Consulta o OSV.dev em tempo real; devolve CVE + severidade + versão corrigida pra um `package@version`. Cobre o buraco que um modelo congelado não cobre. | [Jeneidi](https://github.com/Jeneidi) |
| [`sca-audit`](https://github.com/OWASP/secure-agent-playbook) | Auditoria de supply chain de dependências com análise de alcance e mapeamento CWE. | [OWASP](https://github.com/OWASP) |
| [`code-review-security`](https://github.com/OWASP/secure-agent-playbook) | Code review de segurança sistemático mapeado a OWASP Top 10 + ASVS. | [OWASP](https://github.com/OWASP) |

### 🛡️ Security review: skills de apoio

| Skill | O que faz | Dono |
|---|---|---|
| [`secrets-scan`](https://github.com/OWASP/secure-agent-playbook) | Encontra credenciais / API keys no código e no git history. | [OWASP](https://github.com/OWASP) |
| [`api-security-review`](https://github.com/OWASP/secure-agent-playbook) | Revisão de API contra OWASP API Security Top 10. | [OWASP](https://github.com/OWASP) |
| [`web-security-review`](https://github.com/OWASP/secure-agent-playbook) | Revisão de web app contra OWASP Top 10. | [OWASP](https://github.com/OWASP) |
| [`cve-triage`](https://github.com/UnitOneAI/SecuritySkills) | Prioriza CVEs com CVSS 4.0 / EPSS / CISA KEV. | [UnitOneAI](https://github.com/UnitOneAI) |
| [`patch-prioritization`](https://github.com/UnitOneAI/SecuritySkills) | Decide a ordem da correção. | [UnitOneAI](https://github.com/UnitOneAI) |
| [`dependency-scanning`](https://github.com/UnitOneAI/SecuritySkills) | Varredura da árvore de dependências. | [UnitOneAI](https://github.com/UnitOneAI) |
| [`hermaguard`](https://github.com/Sahil-SS9/hermaguard) | Review adversarial: pré-scan estático + 3 agentes especialistas (edge cases, ataque, blast radius). | [Sahil-SS9](https://github.com/Sahil-SS9) |

### 🎨 Frontend / UI

| Skill | O que faz | Dono |
|---|---|---|
| [`frontend-design`](https://github.com/anthropics/skills) | Direção visual intencional, tipografia, fugindo do padrão "IA genérica". | [Anthropic](https://github.com/anthropics) |
| [`web-design`](https://github.com/KAOPU-XiaoPu/web-design) | Estética web coesa. | [KAOPU-XiaoPu](https://github.com/KAOPU-XiaoPu) |
| [`vercel-react-best-practices`](https://github.com/vercel-labs/agent-skills) | 40+ regras de performance React/Next da engenharia da Vercel. | [Vercel Labs](https://github.com/vercel-labs) |
| [`vercel-composition-patterns`](https://github.com/vercel-labs/agent-skills) | Compound components, composição limpa. | [Vercel Labs](https://github.com/vercel-labs) |
| [`animate`](https://github.com/emilkowalski/skill) | Motion com propósito. | [emilkowalski](https://github.com/emilkowalski) |
| [`anti-ai-slop`](https://github.com/evandrodevbr/dev-workflows) | Detecta padrão visual "gerado por IA" (auto-carregada, local). | skill da comunidade |
| [`avoid-ai-writing`](https://github.com/conorbronsdon/avoid-ai-writing) | Remove AI-isms de microcopy, labels e docs. | [conorbronsdon](https://github.com/conorbronsdon) |

### ⚙️ Backend / API

| Skill | O que faz | Dono |
|---|---|---|
| [`secure-coding`](https://github.com/securityreviewai/secure-coding-skill) | Padrões de codificação segura em 15 stacks. | [securityreviewai](https://github.com/securityreviewai) |
| [`bola-detector`](https://github.com/apisec-inc/apisec-skills) | Object-level authorization quebrada (OWASP API1). | [apisec-inc](https://github.com/apisec-inc) |
| [`auth-rbac-scaffold`](https://github.com/apisec-inc/apisec-skills) | Autenticação + RBAC (OWASP API2 / API5). | [apisec-inc](https://github.com/apisec-inc) |
| [`injection-checker`](https://github.com/apisec-inc/apisec-skills) | Injeção SQL / ORM / shell / template (OWASP API8). | [apisec-inc](https://github.com/apisec-inc) |
| [`openapi-hardener`](https://github.com/apisec-inc/apisec-skills) | Sanear schemas OpenAPI / Zod / Pydantic (OWASP API3). | [apisec-inc](https://github.com/apisec-inc) |
| [`api-security-review`](https://github.com/apisec-inc/apisec-skills) | Review completo OWASP API Top 10. | [apisec-inc](https://github.com/apisec-inc) |
| [`security-test-generator`](https://github.com/apisec-inc/apisec-skills) | Gera suítes de testes de segurança. | [apisec-inc](https://github.com/apisec-inc) |

### 🏗️ Arquitetura

| Skill | O que faz | Dono |
|---|---|---|
| [`system-design`](https://github.com/Kotivskyi/architecture-governance-skills) | Framework HelloInterview de system design. | [Kotivskyi](https://github.com/Kotivskyi) |
| [`c4-architecture`](https://github.com/Kotivskyi/architecture-governance-skills) | Diagramas C4 (Mermaid / Structurizr). | [Kotivskyi](https://github.com/Kotivskyi) |
| [`isaqb-architecture-governance`](https://github.com/Kotivskyi/architecture-governance-skills) | arc42 + ADRs. | [Kotivskyi](https://github.com/Kotivskyi) |
| [`secure-architecture-governance`](https://github.com/Kotivskyi/architecture-governance-skills) | Threat models STRIDE+CIA, ADRs de segurança. | [Kotivskyi](https://github.com/Kotivskyi) |

> 📖 Instruções completas de instalação de cada skill estão em [docs/SKILLS.md](docs/SKILLS.md).

## Começo rápido

```bash
# 1. Copie os workflows pro diretório de skills do seu agente
# Hermes Agent:
cp workflows/*.md ~/.hermes/skills/software-development/

# Claude Code / qualquer agente com diretório de skills:
mkdir -p ~/.claude/skills && cp workflows/*.md ~/.claude/skills/

# 2. (Opcional, pro security review) instale o safedeps + o checker OSV
git clone --depth 1 https://github.com/Jeneidi/safedeps.git
cp -r safedeps/skills/safedeps ~/.hermes/skills/safedeps
cp safedeps/check_deps.py ~/.hermes/skills/safedeps/

# 3. Use
# "review this PR for security"  -> wf-security-review carrega
# "build a new page"              -> wf-frontend carrega
```

## O harness de QA

O diretório `qa/` mantém os próprios workflows honestos:

```bash
cd qa

python3 wf_quality_harness.py   # pontua cada workflow em 30+ critérios
python3 test_quality.py         # gates: sem regressão, skills válidas, fases verificadas
python3 test_tests.py           # meta-testes: corrompe o harness, prova que ele detecta a corrupção
```

Os meta-testes são a parte legal. Eles quebram o harness e os workflows de propósito e confirmam que o placar *cai*. Se o placar não mudasse, o detetor seria inútil. Esses testes ficam verdes como contrato.

## Estrutura do repositório

```
dev-workflows/
├── README.md            # versão em inglês
├── README.pt-BR.md      # este arquivo
├── workflows/           # os quatro workflows em SKILL.md
│   ├── wf-frontend.md
│   ├── wf-backend.md
│   ├── wf-architecture.md
│   └── wf-security-review.md
├── docs/
│   └── SKILLS.md        # inventário completo de skills + instalação
└── qa/                  # harness de qualidade, gates, meta-testes
    ├── wf_quality_harness.py
    ├── test_quality.py
    ├── test_tests.py
    └── snapshots/
```

## Licença

[MIT](LICENSE) © 2026 [Evandro Fonseca Junior](https://github.com/evandrodevbr)

---

<div align="center">

⭐ Se isso te salvar de um "na minha máquina funciona" no merge, dá uma estrela.

</div>
