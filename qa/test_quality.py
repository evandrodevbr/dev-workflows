#!/usr/bin/env python3
"""
test_quality.py — testes validados + aprovados (gate de qualidade não-regressivo).

Roda o harness, compara com o baseline snapshot e aplica gates:

Gate 1 (NÃO REGRESSÃO): score total atual >= baseline (364.1). Se caiu, exit 1.
Gate 2 (MELHORIA ≥2×): score total atual >= 2 * baseline (728.2). Meta do usuário.
Gate 3 (POR WORKFLOW): cada um dos 3 workflows >= 2 * seu baseline individual.
Gate 4 (SKILLS): nenhuma skill referenciada faltando (harness sem sem_match).
Gate 5 (VERIFICAÇÃO POR FASE): toda fase tem >=3 verbos de verificação.

Uso: python3 test_quality.py   -> exit 0 se G1,G3,G4,G5 ok (evidência)
       python3 test_quality.py --strict  -> também exige G2 (2x) — meta final
"""
import json, os, subprocess, sys

WF_QA = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(WF_QA, "wf_quality_harness.py")
SNAPSHOT = os.path.join(WF_QA, "snapshots", "baseline-final.json")

def run_harness():
    r = subprocess.run([sys.executable, HARNESS, "--json"], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr
    return json.loads(r.stdout), None

def main():
    strict = "--strict" in sys.argv
    base = json.load(open(SNAPSHOT))
    base_total = base["total"]
    base_per = {w["name"]: w.get("score", 0) for w in base["workflows"]}

    res, err = run_harness()
    if res is None:
        print(f"HARNESS FALHOU: {err}")
        sys.exit(1)
    cur_total = res["total"]
    cur_per = {w["name"]: w.get("score", 0) for w in res["workflows"]}
    sem_match = {w["name"]: w.get("skills_sem_match", []) for w in res["workflows"]}
    fases_vazias = {w["name"]: w.get("fases_sem_verificacao", []) for w in res["workflows"]}

    print("="*72)
    print("GATES DE QUALIDADE (não-regressivos + meta 2x)")
    print("="*72)
    print(f"baseline: {base_total:.1f} | atual: {cur_total:.1f} | meta(2x): {2*base_total:.1f}")

    ok = True

    # Gate 1 — não regressão
    g1 = cur_total >= base_total
    print(f"[G1] NÃO REGRESSÃO: atual {cur_total:.1f} >= baseline {base_total:.1f} -> {'OK' if g1 else 'FALHOU'}")
    ok &= g1

    # Gate 2 — 2x (strict)
    g2 = cur_total >= 2 * base_total
    print(f"[G2] META 2x (strict): atual {cur_total:.1f} >= {2*base_total:.1f} -> {'OK' if g2 else 'ainda não (meta final)'}")
    if strict:
        ok &= g2

    # Gate 3 — por workflow, 2x individual
    print("[G3] POR WORKFLOW (2x individual):")
    for name, b in base_per.items():
        cur = cur_per.get(name, 0)
        g3i = cur >= 2 * max(b, 0.1)
        print(f"     {name:18} base={b:6.1f} atual={cur:6.1f} 2x={2*max(b,0.1):6.1f} -> {'OK' if g3i else 'FALHOU'}")
        ok &= g3i

    # Gate 4 — skills
    print("[G4] SKILLS REFERENCIADAS:")
    all_skills_ok = True
    for name, miss in sem_match.items():
        st = "OK" if not miss else f"FALTANDO: {miss}"
        print(f"     {name:18} {st}")
        all_skills_ok = all_skills_ok and not miss
    ok &= all_skills_ok

    # Gate 5 — verificação por fase
    print("[G5] VERIFICAÇÃO POR FASE (>=3 verbos):")
    for name, fv in fases_vazias.items():
        st = "OK (todas as fases com verificação)" if not fv else f"sem verificação nas fases {fv}"
        print(f"     {name:18} {st}")
        ok &= not fv

    print("="*72)
    if ok:
        print(f"RESULTADO: APROVADO (gates G1,G3,G4,G5 passaram{' + G2' if strict and g2 else ''}; score {cur_total:.1f})")
        sys.exit(0)
    else:
        print(f"RESULTADO: REPROVADO — gates abaixo falharam. Score {cur_total:.1f}. Rodar refinamento de novo.")
        sys.exit(1)

if __name__ == "__main__":
    main()
