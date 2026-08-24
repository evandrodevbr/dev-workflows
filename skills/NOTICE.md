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
do diretório da skill (mais `check_deps.py` no caso do `safedeps`, que a
skill referencia como script auxiliar).

Pra atualizar uma skill vendorizada: reclone o repo de origem, `diff -r`
contra o diretório aqui, copie por cima se houver mudança real, e atualize
o commit/data desta tabela.
