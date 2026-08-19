# Skills usadas e de onde vieram

Este é o inventário do que os workflows carregam. Cada skill é um diretório
com um `SKILL.md`; para o Hermes Agent, vão em `~/.hermes/skills/`.

## Pilar de segurança (wf-security-review)

| Skill | Origem | O que faz |
|---|---|---|
| `safedeps` | [Jeneidi/safedeps](https://github.com/Jeneidi/safedeps) | Consulta OSV.dev em tempo real; CVE por `package@version` com severidade e versão de fix. Inclui o script `check_deps.py` |
| `sca-audit` | [OWASP/secure-agent-playbook](https://github.com/OWASP/secure-agent-playbook) | SCA de dependências com análise de alcance (reachability), mapeamento CWE |
| `code-review-security` | OWASP/secure-agent-playbook | Code review de segurança sistemático mapeado a OWASP Top 10 + ASVS |
| `secrets-scan` | OWASP/secure-agent-playbook | Detecta credenciais/API keys no código e no git history |
| `api-security-review` | OWASP/secure-agent-playbook | Revisão de API contra OWASP API Security Top 10 |
| `web-security-review` | OWASP/secure-agent-playbook | Web app contra OWASP Top 10 (2021) |
| `cve-triage` | [UnitOneAI/SecuritySkills](https://github.com/UnitOneAI/SecuritySkills) | Prioriza CVE por CVSS 4.0 / EPSS / CISA KEV |
| `patch-prioritization` | UnitOneAI/SecuritySkills | Decide a ordem de remediação |
| `dependency-scanning` | UnitOneAI/SecuritySkills | Varredura de dependências |

## Frontend / UI / design (wf-frontend)

| Skill | Origem | O que faz |
|---|---|---|
| `frontend-design` | [anthropics/skills](https://github.com/anthropics/skills) | Direção visual, tipografia, fugir do genérico |
| `web-design` | [KAOPU-XiaoPu/web-design](https://github.com/KAOPU-XiaoPu/web-design) | Estética web coesa |
| `vercel-react-best-practices` | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | 40+ regras de perf React/Next |
| `vercel-composition-patterns` | vercel-labs/agent-skills | Compound components, composição |
| `animate` | [emilkowalski/skill](https://github.com/emilkowalski/skill) | Motion com propósito |
| `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Vocabulário de design: 23 comandos + 59 regras determinísticas anti-slop |
| `anti-ai-slop` | local | Detecta padrão visual "gerado por IA" |
| `avoid-ai-writing` | [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | Remove AI-isms de texto/microcopy |

## Backend / API (wf-backend)

| Skill | Origem | O que faz |
|---|---|---|
| `secure-coding` | [v6x/secure-coding-skill](https://github.com/securityreviewai/secure-coding-skill) | Padrões de codificação segura em 15 stacks |
| `bola-detector` | [apisec-inc/apisec-skills](https://github.com/apisec-inc/apisec-skills) | Detecta object-level authorization (OWASP API1) |
| `auth-rbac-scaffold` | apisec-inc/apisec-skills | Auth/RBAC (OWASP API2/API5) |
| `injection-checker` | apisec-inc/apisec-skills | Injection SQL/ORM/shell (OWASP API8) |
| `openapi-hardener` | apisec-inc/apisec-skills | Saneia schemas OpenAPI/Zod (OWASP API3) |
| `api-security-review` | apisec-inc/apisec-skills | Review completo OWASP API Top 10 |
| `security-test-generator` | apisec-inc/apisec-skills | Gera testes de segurança |

## Arquitetura (wf-architecture)

| Skill | Origem | O que faz |
|---|---|---|
| `system-design` | [Kotivskyi/architecture-governance-skills](https://github.com/Kotivskyi/architecture-governance-skills) | Framework HelloInterview de system design |
| `c4-architecture` | Kotivskyi/architecture-governance-skills | Diagramas C4 (Mermaid/Structurizr) |
| `isaqb-architecture-governance` | Kotivskyi/architecture-governance-skills | arc42 + ADR |
| `secure-architecture-governance` | Kotivskyi/architecture-governance-skills | Threat model STRIDE+CIA, S-ADR |

## Caça de bugs (todas)

| Skill | Origem | O que faz |
|---|---|---|
| `hermaguard` | [Sahil-SS9/hermaguard](https://github.com/Sahil-SS9/hermaguard) | Review adversarial: pre-scan + 3 agentes (edge cases, ataque, blast radius) |

## Como instalar as skills de origem

A maioria instala via `npx skills` (formato agentskills.io):

```bash
npx skills add anthropics/skills --skill frontend-design
npx skills add vercel-labs/agent-skills --skill vercel-react-best-practices
npx skills add conorbronsdon/avoid-ai-writing
npx skills add https://github.com/pbakaus/impeccable --skill impeccable
```

As de segurança do OWASP e UnitOne instalam clonando e copiando o diretório
da skill:

```bash
git clone --depth 1 https://github.com/OWASP/secure-agent-playbook.git
cp -r secure-agent-playbook/plugins/code-security-skills/skills/{sca-audit,secrets-scan} ~/.hermes/skills/

git clone --depth 1 https://github.com/UnitOneAI/SecuritySkills.git
cp -r SecuritySkills/skills/vuln-management/{cve-triage,patch-prioritization} ~/.hermes/skills/
```

O safedeps precisa do script junto da skill:

```bash
git clone --depth 1 https://github.com/Jeneidi/safedeps.git
cp -r safedeps/skills/safedeps ~/.hermes/skills/safedeps
cp safedeps/check_deps.py ~/.hermes/skills/safedeps/
```
