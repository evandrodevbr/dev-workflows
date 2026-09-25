# Skills: inventário e origem

Cada skill é um diretório `skills/<nome>/SKILL.md`. O plugin carrega todas; `scripts/install.py`
copia para o opencode ou o Hermes.

## Do próprio repositório

| Skill | Para quê |
|---|---|
| `dev-router` | Classifica o pedido em nível 0 a 3 e decide workflows, agentes e gate |
| `lean-code` | Menor solução que resolve: reaproveitar, apagar, sem abstração nem dependência sem motivo |
| `wf-bugfix` | Reproduzir, causa raiz, teste de regressão que falha antes e passa depois |
| `wf-refactor` | Testes de caracterização, passos pequenos, comportamento igual |
| `wf-frontend` | UI e PDF: design (nível 2+), build acessível e responsivo, revisão visual |
| `wf-backend` | API: contrato primeiro (nível 2+), defaults seguros, auditoria OWASP, testes |
| `wf-architecture` | Nível 3: spec EARS, C4, ADR, STRIDE, revisão |
| `wf-security-review` | Revisão de segurança front e back com CVEs consultados ao vivo |
| `wf-readme` | README fundamentado em fatos do repositório, comandos executados antes da entrega |

## Vendorizadas (vêm no clone)

Origem, commit e licença de cada uma: [`skills/NOTICE.md`](../skills/NOTICE.md).

| Skill | Origem | O que faz |
|---|---|---|
| `safedeps` | [Jeneidi/safedeps](https://github.com/Jeneidi/safedeps) | CVE por `package@version` consultando o OSV.dev ao vivo |
| `sca-audit` | [OWASP/secure-agent-playbook](https://github.com/OWASP/secure-agent-playbook) | Auditoria de dependências com análise de alcance e CWE |
| `code-review-security` | OWASP/secure-agent-playbook | Code review de segurança mapeado a OWASP Top 10 e ASVS |
| `secrets-scan` | OWASP/secure-agent-playbook | Credenciais e chaves no código e no histórico do git |
| `api-security-review` | OWASP/secure-agent-playbook | API contra o OWASP API Security Top 10 |
| `web-security-review` | OWASP/secure-agent-playbook | Web app contra o OWASP Top 10 |
| `cve-triage` | [UnitOneAI/SecuritySkills](https://github.com/UnitOneAI/SecuritySkills) | Prioriza CVE por CVSS 4.0, EPSS e CISA KEV |
| `patch-prioritization` | UnitOneAI/SecuritySkills | Ordem de remediação |
| `dependency-scanning` | UnitOneAI/SecuritySkills | Varredura da árvore de dependências |
| `hermaguard` | [Sahil-SS9/hermaguard](https://github.com/Sahil-SS9/hermaguard) | Revisão adversarial: pre-scan e 3 agentes (borda, ataque, blast radius) |
| `design-taste-frontend` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | Gera tela nova sem cara de template |
| `redesign-existing-projects` | Leonxlnx/taste-skill | Audita UI existente e melhora sem quebrar |

## Externas (opcionais)

Os workflows usam estas quando instaladas e seguem as próprias regras quando não. Instalação no
formato Agent Skills:

```bash
npx skills add <dono/repo> --skill <nome>
```

| Skill | Origem | Usada por |
|---|---|---|
| `frontend-design` | [anthropics/skills](https://github.com/anthropics/skills) | `wf-frontend` |
| `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | `wf-frontend`, `ui-critic` |
| `vercel-react-best-practices` | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | `wf-frontend` |
| `vercel-composition-patterns` | vercel-labs/agent-skills | `wf-frontend` |
| `animate` | [emilkowalski/skill](https://github.com/emilkowalski/skill) | `wf-frontend` |
| `web-design` | [KAOPU-XiaoPu/web-design](https://github.com/KAOPU-XiaoPu/web-design) | `wf-frontend` |
| `avoid-ai-writing` | [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | `wf-frontend`, `wf-readme` |
| `secure-coding` | [securityreviewai/secure-coding-skill](https://github.com/securityreviewai/secure-coding-skill) | `wf-backend` |
| `bola-detector` | [apisec-inc/apisec-skills](https://github.com/apisec-inc/apisec-skills) | `wf-backend`, `wf-security-review` |
| `auth-rbac-scaffold` | apisec-inc/apisec-skills | `wf-backend`, `wf-security-review` |
| `injection-checker` | apisec-inc/apisec-skills | `wf-backend`, `wf-security-review` |
| `openapi-hardener` | apisec-inc/apisec-skills | `wf-backend` |
| `security-test-generator` | apisec-inc/apisec-skills | `wf-backend` |
| `system-design` | [Kotivskyi/architecture-governance-skills](https://github.com/Kotivskyi/architecture-governance-skills) | `wf-architecture` |
| `c4-architecture` | Kotivskyi/architecture-governance-skills | `wf-architecture` |
| `isaqb-architecture-governance` | Kotivskyi/architecture-governance-skills | `wf-architecture` |
| `secure-architecture-governance` | Kotivskyi/architecture-governance-skills | `wf-architecture` |
| `readme-crafter` | [linhai0872/readme-crafter-skill](https://github.com/linhai0872/readme-crafter-skill) | `wf-readme` |
| `good-readme` | [adewale/good-readme](https://github.com/adewale/good-readme) | `wf-readme` |
| `curating-readme` | [liang-senbei/curating-readme](https://github.com/liang-senbei/curating-readme) | `wf-readme` |

A apisec-inc também publica uma skill chamada `api-security-review`. Ela não é usada aqui: o nome
colide com a versão OWASP vendorizada.

O `impeccable` não é vendorizado porque traz scripts executáveis de terceiros; instale-o você mesmo
(`npx skills add https://github.com/pbakaus/impeccable --skill impeccable`) se quiser o `/impeccable audit`.
