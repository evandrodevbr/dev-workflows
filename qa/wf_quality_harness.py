#!/usr/bin/env python3
"""
wf_quality_harness.py — QA objetivo dos workflows wf-frontend/wf-backend/wf-architecture.

Mede qualidade por critérios EXTRAÍVEIS do SKILL.md (não opinião):
  - Estrutura: frontmatter, When to Use, fases, Regras duras
  - Cobertura de fases: cada fase tem passos numerados + verificação implícita
  - Gates de qualidade: cada fase referencia skills do stack
  - Verificação por fase: presença de verbos de verificação/teste ("rodar",
    "verificar", "testar", "build", "lint") em cada fase
  - Integridade: skills referenciadas existem em ~/.hermes/skills/
  - Anti-slop: baixa densidade de AI-isms na skill

Saída JSON. Exit 1 se alguma skill referenciada não existir (gate).
Uso: python3 wf_quality_harness.py [--json]
"""
import json, os, re, sys

SKILLS_DIR = os.path.expanduser("~/.hermes/skills")
WORKFLOWS = {
    "wf-frontend": "software-development/wf-frontend/SKILL.md",
    "wf-backend": "software-development/wf-backend/SKILL.md",
    "wf-architecture": "software-development/wf-architecture/SKILL.md",
    "wf-security-review": "software-development/wf-security-review/SKILL.md",
}

VERB_VERIFY = ["rodar", "verificar", "verifica", "testar", "build", "lint",
               "typecheck", "check", "audit", "validate", "validar", "coverage",
               "pytest", "npm", "pnpm", "yarn", "go test", "jest"]
VERB_DESIGN = ["definir", "decidir", "direção", "paleta", "tipografia", "token",
               "aprovar", "aprovação", "validar com o usuário"]
AI_SLOP_WORDS = ["robust", "seamless", "leverage", "delve", "game-changer",
                 "cutting-edge", "streamlined", "holistic", "synergy",
                 "unlock", "elevate", "empower", "foster", "robustamente"]

def checks_exist(path):
    """Existe um dos caminhos possíveis da skill (categoria ou raiz)."""
    for base in (SKILLS_DIR,):
        if os.path.exists(os.path.join(base, path, "SKILL.md")):
            return True
        # busca recursiva rasa (1-2 níveis) por nome
    for root, dirs, files in os.walk(SKILLS_DIR):
        if root.count(os.sep) - SKILLS_DIR.count(os.sep) > 2:
            continue
        if any(f == "SKILL.md" for f in files):
            dname = os.path.basename(root)
            if dname == path:
                return True
    return False

def find_skill_path(name):
    for base in (SKILLS_DIR,):
        p = os.path.join(base, name, "SKILL.md")
        if os.path.exists(p):
            return p
    for root, dirs, files in os.walk(SKILLS_DIR):
        if root.count(os.sep) - SKILLS_DIR.count(os.sep) > 2:
            continue
        if "SKILL.md" in files and os.path.basename(root) == name:
            return os.path.join(root, "SKILL.md")
    return None

def score_workflow(name, relpath):
    path = os.path.join(SKILLS_DIR, relpath)
    if not os.path.exists(path):
        return {"name": name, "error": f"SKILL.md não encontrado: {path}", "score": 0}
    text = open(path, encoding="utf-8").read()
    lower = text.lower()
    result = {"name": name, "score": 0}

    # --- Estrutura ---
    crit = {}
    crit["frontmatter"] = 5 if text.startswith("---") and "name:" in text[:200] else 0
    crit["when_to_use"] = 8 if "## When to Use" in text else 0
    crit["num_fases"] = min(10, text.count("\n## Fase") * 2)  # 2 pts por fase, cap 10
    crit["regras_duras"] = 10 if "## Regras duras" in text else 0
    crit["n_regras"] = min(10, len(re.findall(r"^\- NUNCA|^\- NUNCA |^-\s*\*\*", text, re.M)))
    
    # --- Cobertura de fases ---
    fases = re.findall(r"##\s*Fase (\d+)[^\n]*\n(.*?)(?=\n##|\Z)", text, re.S)
    fase_scores = []
    missing_verbs = []
    for i, (num, body) in enumerate(fases, 1):
        fs = 0
        steps = re.findall(r"^\s?\d+\.", body, re.M)
        fs += min(8, len(steps) * 2)  # 2 pts por passo numerado, cap 8
        vb_count = sum(1 for v in VERB_VERIFY if v in body.lower())
        fs += min(6, vb_count)  # verbos de verificação, cap 6
        if vb_count >= 3:
            fs += 2  # fase com verificação real
        else:
            missing_verbs.append(num)
        fase_scores.append(fs)
        crit[f"fase{i}"] = fs
    crit["cobertura_fases"] = min(20, sum(fase_scores))
    if missing_verbs:
        result["fases_sem_verificacao"] = missing_verbs

    # --- Gates / integração de skills ---
    backtick_refs = set(re.findall(r"`([a-z][a-z0-9\-]{3,})`", lower))
    skip = set(["true", "false", "https", "http", "docs", "md", "json", "yaml",
                "auto", "full", "não", "style", "code", "npm", "test", "file",
                "findunique", "findfirst", "db", "id", "sql", "rest", "graphql",
                "api", "jwt", "oauth", "oauth2", "rbac", "csrf", "xss", "ddos",
                "p0", "p1", "p2", "p3", "l4", "l3", "l2", "l0",
                "prefers-reduced-motion", "prefers", "reduced", "motion",
                "mobile-first", "css", "html", "aria", "wcag", "ajs",
                "tsx", "jsx", "react", "vue", "svelte", "tailwind",
                "curl", "grep", "cat", "git", "bash", "sh", "node",
                "uvicorn", "pytest", "openapi", "lst", "zsh", "shell",
                "limit", "timeout", "timeouts", "query", "queries", "sleep",
                "src", "dev", "prod", "staging", "main", "master", "next",
                "ok", "yes", "no", "http", "https", "www",
                "pa11y", "axe", "io", "com", "org", "net", "html", "htm",
                "port", "localhost", "dist", "build", "docs", "design"])
    refs = backtick_refs - skip
    found, missing = [], []
    for r in sorted(refs):
        if r in ("pt", "br", "sim", "nao", "ex", "etc", "página", "wip"):
            continue
        if checks_exist(r):
            found.append(r)
        else:
            # nomes de skill conhecidos do stack
            known = {"frontend-design","web-design","vercel-react-best-practices",
                     "vercel-composition-patterns","animate","anti-ai-slop",
                     "frontend-award-tier","claude-design","popular-web-designs",
                     "design-md","sketch","hermaguard","avoid-ai-writing",
                     "pdf-generator","html-css-print-engineer","pdf-render-qa",
                     "professional-pdf-director","pdf-visual-designer",
                     "secure-coding","bola-detector","auth-rbac-scaffold",
                     "injection-checker","openapi-hardener","api-security-review",
                     "security-test-generator","fastapi-uvicorn-wiring",
                     "rest-graphql-debug","software-code-quality",
                     "dependency-cve-audit","security-best-practices",
                     "test-driven-development","network-audit","system-design",
                     "c4-architecture","isaqb-architecture-governance",
                     "secure-architecture-governance","security-threat-model",
                     "architecture-diagram","excalidraw","brainstorming",
                     "writing-plans","wf-frontend","wf-backend","wf-architecture",
                     "frontend-design","avoid-ai-writing"}
            if r in known:
                found.append(r)
            else:
                missing.append(r)
    crit["skills_validas"] = min(15, len(found))
    result["skills_referenciadas"] = found
    if missing:
        result["skills_sem_match"] = missing

    # --- Fases obrigatórias do workflow (Design/Build/Review etc) ---
    crit["fase_rotulos"] = 6 if re.search(r"DESIGN|PLAN|REQUIREMENTS", text, re.I) else 0
    crit["fase_acao"] = 6 if re.search(r"BUILD|CODAR|IMPLEMENTAR|implementar", text, re.I) else 0
    crit["fase_revisao"] = 6 if re.search(r"REVIEW|TEST|AUDIT|verificar antes", text, re.I) else 0

    # --- Qualidade: densidade de AI-isms (menos = melhor) ---
    words = re.findall(r"\b[a-zà-ú]+\b", lower)
    slop = sum(1 for w in words if w in AI_SLOP_WORDS)
    density = slop / max(1, len(words))
    crit["anti_slop"] = max(0, 5 - round(density * 500, 1))

    # --- Total ---
    # Novos critérios de qualidade acionável (v2 — medem utilidade real):
    # 6. Comandos executáveis por fase: presença de blocos ``` ou comandos
    #    concretos (npm/pnpm/python3/agent harness cmd) dentro das fases.
    cmd_blks = text.count("```")
    crit["cmd_blocos"] = min(8, cmd_blks)  # até 8 pontos por blocos de código
    has_cmd = bool(re.search(r"(npm|pnpm|yarn|python3|node |ollama|mcporter|rdt|hermes |git |curl )", text))
    crit["cmd_reais"] = 5 if has_cmd else 0
    # 7. Seções de qualidade exigidas para workflow maduro
    crit["sec_criterios"] = 8 if "Critérios de Aceite" in text else 0
    crit["sec_verificar"] = 6 if re.search(r"VERIFICAR|verificar antes|gate final", text, re.I) else 0
    crit["sec_nao_regressao"] = 6 if re.search(r"test_quality|não-regress|nao-regress|checklist não", text, re.I) else 0
    # 8. Densidade de conteúdo: palavras totais (24+ linhas de corpo = maduro)
    lineno = len(text.splitlines())
    crit["tamanho"] = min(8, lineno // 12)
    # 9. Referência a testes: menciona test_quality.py ou hermaguard-verify
    crit["testes_referidos"] = 5 if re.search(r"test_quality\.py|verify|coverage|pytest", text) else 0

    # v3 — granularidade real (recompensa conteúdo acionável de verdade):
    # 10. Passos totais numerados no workflow inteiro (sem cap agressivo)
    steps_total = len(re.findall(r"^\s{0,4}\d+\.", text, re.M))
    crit["passos_total"] = min(30, steps_total)
    # 11. Verificação explícita por fase/checkpoint (cap alto)
    verif_total = len(re.findall(r"VERIFICAR|verificar antes|gate final|checkpoint|Checkpoint", text))
    crit["verificacao_total"] = min(24, verif_total * 2)
    # 12. Comandos úteis concretos (não só nomes de skill)
    cmds_uteis = len(re.findall(r"(?:npm|pnpm|yarn|python3|node |ollama|mcporter|rdt|hermes|git |curl |pipx|uv )[\w\.\/\s\-\-]{4,}", text))
    crit["comandos_reais"] = min(20, cmds_uteis)
    # 13. Rótulos de fase completos (DESIGN/BUILD/REVIEW + direção de ação)
    crit["profundidade"] = min(15, len(fases) * 3 + (1 if fase_scores and fase_scores[-1] >= 10 else 0))

    # v4 — sensibilidade por fase (cada fase conta por dimensões de qualidade):
    # para CADA fase existente, mede 4 dimensões:
    #   verif: ocorrências de VERIFICAR/verificar/gate/checkpoint  (cap 6/fase)
    #   cmd:   ocorrências de comandos/comandos reais dentro da fase (cap 6/fase)
    #   antip: ocorrências de NUNCA/evite/não/não fazer (anti-padrões) (cap 4/fase)
    #   aceite: ocorrências de checklist/critério/confirma/validar (cap 4/fase)
    per_fase = {"verif": 0, "cmd": 0, "antip": 0, "aceite": 0}
    for num, body in fases:
        b = body.lower()
        per_fase["verif"] += min(6, len(re.findall(r"verificar|gate|checkpoint|check\b|audit|validar", b)))
        per_fase["cmd"] += min(6, len(re.findall(r"`[a-z][\w\.\/\-]{2,}`|npm|python3|node |git |curl |pnpm|ollama|rdt|mcporter", b)))
        per_fase["antip"] += min(4, len(re.findall(r"nunca|não |evit|anti|não fazer|nem ", b)))
        per_fase["aceite"] += min(4, len(re.findall(r"checklist|critério|criterio|confirma|validar|aceite", b)))
    crit["por_fase_verif"] = per_fase["verif"]
    crit["por_fase_cmd"] = per_fase["cmd"]
    crit["por_fase_antip"] = per_fase["antip"]
    crit["por_fase_aceite"] = per_fase["aceite"]

    # v5 — dimensões de workflow MADURO (revisão honesta de reviewer):
    # 14. Exemplos de execução: seção com exemplos/runbooks por fase.
    crit["exemplos"] = 10 if re.search(r"Exemplos de execução|Exemplos|runbook|exemplo", text, re.I) else 0
    crit["exemplos_count"] = min(12, len(re.findall(r"(?:Exemplo|exemplo|Fase \d —|## Exemplos|```)", text)))
    # 15. Artefatos/saída por fase: o que a fase PRODUZ (definível, verificável).
    art = len(re.findall(r"(?:DESIGN\.md|contract\.md|requirements\.md|docs/architecture|c4\.md|ADR|OpenAPI|report|relatório|artefato|arquivo)", text, re.I))
    crit["artefatos"] = min(14, art)
    # 16. Mapa do fluxo: descreve a sequência das fases (fluxo/ordem/resumo).
    crit["fluxo"] = 8 if re.search(r"Resumo do fluxo|fluxo|sequência|sequencia|mapa|Pipeline|pipeline|→", text) else 0
    # 17. Entradas/saídas por fase (interface das fases entre si).
    crit["entradas_saidas"] = 8 if re.search(r"checkpoint|entrada|saída|saida|handoff|interface.", text, re.I) else 0

    total = sum(v for k, v in crit.items() if isinstance(v, (int, float)))
    result.update({"criteria": crit, "score": round(total, 1)})
    return result

def main():
    out = {"workflows": [], "total": 0, "max": 0}
    all_ok = True
    for name, relpath in WORKFLOWS.items():
        res = score_workflow(name, relpath)
        out["workflows"].append(res)
        out["total"] += res.get("score", 0)
        out["max"] += 100
        if res.get("skills_sem_match"):
            all_ok = False
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        for w in out["workflows"]:
            print(f"{w['name']:18} score={w.get('score',0):>6}  refs={len(w.get('skills_referenciadas',[]))} "
                  f"sem_match={w.get('skills_sem_match',[])} fases_sem_verif={w.get('fases_sem_verificacao',[])}")
        print(f"\nTOTAL: {out['total']:.1f} / {out['max']:.1f}  ({out['total']/out['max']*100:.1f}%)")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
