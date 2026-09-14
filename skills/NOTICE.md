# Skills vendorizadas — origem e licença

Este diretório contém cópias vendorizadas (não forks, não submodules) das
skills de terceiros usadas pelo `wf-security-review`. Vendorizar em vez de só
linkar (como `docs/SKILLS.md` fazia antes) significa que `git clone
dev-workflows` já traz tudo funcional, sem passo manual de instalação externa.

Cada linha abaixo registra o commit exato de onde a cópia local foi tirada —
use isso pra checar se a origem teve atualização (`git log <sha>..HEAD` no
repo de origem, ou comparar datas).

| Skill | Origem | Commit vendorizado | Licença |
|---|---|---|---|
| `safedeps` | [Jeneidi/safedeps](https://github.com/Jeneidi/safedeps) | `3f4dd8d` (2026-06-29) | MIT |
| `sca-audit` | [OWASP/secure-agent-playbook](https://github.com/OWASP/secure-agent-playbook) | `79fea6b` (2026-06-02) | CC-BY-4.0 |
| `secrets-scan` | OWASP/secure-agent-playbook | `79fea6b` (2026-06-02) | CC-BY-4.0 |
| `code-review-security` | OWASP/secure-agent-playbook | `79fea6b` (2026-06-02) | CC-BY-4.0 |
| `api-security-review` | OWASP/secure-agent-playbook | `79fea6b` (2026-06-02) | CC-BY-4.0 |
| `web-security-review` | OWASP/secure-agent-playbook | `79fea6b` (2026-06-02) | CC-BY-4.0 |
| `cve-triage` | [UnitOneAI/SecuritySkills](https://github.com/UnitOneAI/SecuritySkills) | `70bc259` (2026-06-18) | MIT |
| `patch-prioritization` | UnitOneAI/SecuritySkills | `70bc259` (2026-06-18) | MIT |
| `dependency-scanning` | UnitOneAI/SecuritySkills | `70bc259` (2026-06-18) | MIT |
| `hermaguard` | [Sahil-SS9/hermaguard](https://github.com/Sahil-SS9/hermaguard) | `b491fbe` (2026-08-15) | MIT |

Licença CC-BY-4.0 (OWASP/secure-agent-playbook) exige atribuição — mantida
via a tabela acima e o link direto ao repo original em cada menção nos
READMEs. Nenhum conteúdo foi modificado em relação ao original; cópia 1:1
do diretório da skill, mais os arquivos de apoio que a própria skill
referencia (ver abaixo).

## Arquivos de apoio vendorizados

Os `SKILL.md` acima não são autossuficientes: eles apontam para playbooks,
templates e schemas que ficam em outros diretórios do repo de origem. A
primeira vendorização copiou só o `SKILL.md` e deixou esses arquivos para
trás — o resultado é que a skill carregava e apontava para um arquivo
inexistente. Eles foram trazidos junto, dentro do diretório de cada skill,
para que ela continue funcional depois de copiada sozinha:

| Arquivo | Skill(s) que referenciam | Origem |
|---|---|---|
| `plays/api-security-review.md` | `api-security-review` | OWASP/secure-agent-playbook `plugins/code-security-skills/plays/` |
| `plays/code-review-security.md` | `code-review-security` | idem |
| `plays/sca-audit.md` | `sca-audit` | idem |
| `plays/secrets-scan.md` | `secrets-scan` | idem |
| `plays/owasp-top10-web-review.md` | `web-security-review` | idem |
| `templates/finding.md` | `code-review-security`, `sca-audit`, `secrets-scan`, `web-security-review` | idem, `templates/` |
| `schemas/finding.schema.json` | `cve-triage`, `patch-prioritization`, `dependency-scanning` | UnitOneAI/SecuritySkills `schemas/` |
| `docs/sarif-output.md` | `dependency-scanning` | UnitOneAI/SecuritySkills `docs/` |
| `docs/fixer-policy.md` | `dependency-scanning` | UnitOneAI/SecuritySkills `docs/` |
| `docs/normalized-json-output.md` | `dependency-scanning` (linkado de `docs/sarif-output.md`) | UnitOneAI/SecuritySkills `docs/` |

Esses arquivos são cópias 1:1 do upstream. A única edição nos `SKILL.md` foi
nos caminhos: as referências `../../../schemas/…` e `../../../docs/…`
apontavam para a raiz do repo de origem, que tinha um nível a mais
(`skills/<categoria>/<skill>/`). Como aqui o diretório é plano
(`skills/<skill>/`), os links foram ajustados para o caminho relativo dentro
da própria skill, que é o que sobrevive a `cp -r skills/* ~/.hermes/skills/`.

## Lacunas conhecidas

- `hermaguard` referencia `governance/multi-gate-qa.md` e
  `.github/workflows/hermaguard.yml`, que existem só no ambiente do autor
  original (pipeline `kensei`), não no repo upstream. Não foram criados: são
  contexto de integração, não dependência de execução da skill.
- Os playbooks citam controles ASVS em `data/asvs/*.md` (dataset do
  OWASP/secure-agent-playbook). São citações informativas por check, não
  arquivos que a skill precise abrir para rodar; o dataset inteiro (~90
  arquivos) não foi vendorizado de propósito.
- `hermaguard` foi vendorizado no commit `b491fbe`; o upstream já avançou
  (adicionou a ferramenta `hermaguard-trajectory` e `test_trajectory.py`). A
  cópia local é internamente consistente (README, `pyproject.toml` e testes
  batem entre si), mas está atrás do upstream.

Pra atualizar uma skill vendorizada: reclone o repo de origem, `diff -r`
contra o diretório aqui, copie por cima se houver mudança real, e atualize
o commit/data desta tabela.
