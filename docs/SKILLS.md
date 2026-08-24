# Skills usadas e de onde vieram

Este é o inventário do que os workflows carregam. Cada skill é um diretório
com um `SKILL.md`; para o Hermes Agent, vão em `~/.hermes/skills/`; para
Claude Code, em `~/.claude/skills/<nome>/SKILL.md` (subdiretório por skill —
Claude Code não carrega arquivo `.md` solto, precisa do diretório).

## Workflows orquestradores (em `workflows/`)

| Workflow | Para quê |
|---|---|
| `wf-frontend` | UI/design/PDF |
| `wf-backend` | API/backend seguro |
| `wf-architecture` | Arquitetura/ADR/C4 |
| `wf-security-review` | Code review de segurança front+back |
| `wf-readme` | Criar/auditar/reescrever READMEs grounded |

## README (wf-readme)

| Skill | Origem | O que faz |
|---|---|---|
| `readme-crafter` | [linhai0872/readme-crafter-skill](https://github.com/linhai0872/readme-crafter-skill) | Classifica projeto (tipo/público/temperamento) e gera README sob medida; 13 checks |
| `good-readme` | [adewale/good-readme](https://github.com/adewale/good-readme) | Cria com exemplos reais OU audita contra 22 critérios (escala 100) |
| `curating-readme` | [liang-senbei/curating-readme](https://github.com/liang-senbei/curating-readme) | Padroniza README + docs (CONTRIBUTING/CHANGELOG) com `audit-repo.sh` |

## Pilar de segurança (wf-security-review)

**Vendorizadas neste repo** em `skills/<nome>/` — ver `skills/NOTICE.md` pra
origem exata (commit + licença) de cada uma. Não precisa clonar nada externo
pra este pilar.

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

**Pilar de segurança:** já vem vendorizado em `skills/` neste repo — sem
clone externo. Copie direto:

```bash
# Hermes Agent:
cp -r skills/* ~/.hermes/skills/

# Claude Code (cada skill no seu próprio diretório):
mkdir -p ~/.claude/skills
for d in skills/*/; do
  nome=$(basename "$d")
  [ "$nome" = "NOTICE.md" ] && continue
  mkdir -p "~/.claude/skills/$nome"
  cp -r "$d." "~/.claude/skills/$nome/"
done
```

**Frontend/backend/arquitetura** (ainda não vendorizadas, instalam de fora):
a maioria via `npx skills` (formato agentskills.io):

```bash
npx skills add anthropics/skills --skill frontend-design
npx skills add vercel-labs/agent-skills --skill vercel-react-best-practices
npx skills add conorbronsdon/avoid-ai-writing
npx skills add https://github.com/pbakaus/impeccable --skill impeccable
```
