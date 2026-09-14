#!/usr/bin/env python3
"""
test_tests.py — 'teste dos testes' (meta-testes) do wf_quality_harness.

Prova que o harness REALMENTE mede qualidade:
  1. Baseline registrado em snapshots/baseline-final.json (score 1613.2).
  2. Muta o harness (zera o anti_slop) e confirma que o score CAI -> o
     harness não é indiferente ao input.
  3. Muta um workflow (tira 'Regras duras') e confirma que o score CAI ->
     o harness responde a perda de conteúdo. Se o workflow não for
     encontrado, isso é FALHA, não skip: meta-teste que não roda é falso
     verde.
  4. Re-verifica o estado real: score atual >= baseline (não-regressão).

Exit 0 = testes dos testes OK e não-regressão verificada.
Exit 1 = falhou (meta-teste ou regressão real).
"""
import json, os, shutil, subprocess, sys, tempfile, importlib.util

WF_QA = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(WF_QA, "wf_quality_harness.py")
SNAPSHOT = os.path.join(WF_QA, "snapshots", "baseline-final.json")

def load_harness():
    """Importa o harness pra reusar a mesma resolução de caminho dos workflows."""
    spec = importlib.util.spec_from_file_location("wfq_harness", HARNESS)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"não consegui carregar o harness em {HARNESS}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run_harness():
    r = subprocess.run([sys.executable, HARNESS, "--json"], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr
    return json.loads(r.stdout), None

def main():
    fails = []
    baseline = json.load(open(SNAPSHOT))["total"]

    # --- Teste 1: harness roda e retorna total válido ---
    res, err = run_harness()
    if res is None:
        fails.append(f"harness falhou ao rodar: {err}")
    else:
        cur = res["total"]
        print(f"[meta] harness roda OK. score atual={cur:.1f} baseline={baseline:.1f}")
        if not (baseline > 0 and cur > 0):
            fails.append("scores inválidos (<=0)")
        if cur < baseline:
            fails.append(f"REGRESSÃO REAL: atual {cur:.1f} < baseline {baseline:.1f}")

    # Sem harness não há o que comparar: os testes 2 e 3 dependem do score atual.
    if res is None:
        print("\nFALHAS META-TESTE:")
        for f in fails:
            print("  -", f)
        sys.exit(1)

    # --- Teste 2: mutação do harness muda o resultado (sensibilidade) ---
    tmp = tempfile.mkdtemp(prefix="wfqamut_")
    try:
        mutated = os.path.join(tmp, "wf_quality_harness_mut.py")
        src = open(HARNESS, encoding="utf-8").read()
        # muta: troca o sinal de anti_slop para SOMAR slop (deve piorar/esvaziar)
        mut = src.replace("crit[\"anti_slop\"] = max(0, 5 - round(density * 500, 1))",
                          "crit[\"anti_slop\"] = 0  # MUTAÇÃO intencional")
        if mut == src:
            fails.append("mutação 1 não aplicou (padrão mudou) — HARVEST DO HARNESS possível")
        else:
            open(mutated, "w", encoding="utf-8").write(mut)
            r = subprocess.run([sys.executable, mutated, "--json"], capture_output=True, text=True)
            try:
                j = json.loads(r.stdout)
                if j["total"] >= res["total"]:
                    fails.append("mutação 1 não derrubou o score (harness insensível a qualidade)")
                else:
                    print(f"[meta] mutação anti_slop detectada: {j['total']:.1f} < {res['total']:.1f} OK")
            except Exception:
                fails.append("mutação 1: saída não-JSON após remoção do anti_slop")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- Teste 3: workflow mutado (remove Regras duras) derruba score ---
    # Resolve o mesmo caminho que o harness usa (clone do repo ou instalado).
    # Um meta-teste que não roda é falso verde: se o arquivo não for achado,
    # isso é FALHA, não skip.
    try:
        h = load_harness()
        wk = h.resolve_workflow("wf-frontend", h.WORKFLOWS["wf-frontend"])
    except Exception as e:
        h, wk = None, None
        fails.append(f"não consegui resolver o workflow wf-frontend: {e}")
    if h is not None and wk is None:
        fails.append("workflow wf-frontend não encontrado (nem workflows/wf-frontend.md no repo nem instalado) — meta-teste 3 não pôde rodar")
    if wk is not None:
        orig = open(wk, encoding="utf-8").read()
        if "## Regras duras" not in orig:
            fails.append(f"'{wk}' não tem '## Regras duras' — meta-teste 3 não consegue mutar")
        else:
            ctx = tempfile.mkdtemp(prefix="wfqamutwf_")
            backup = os.path.join(ctx, "backup.md")
            shutil.copy(wk, backup)
            try:
                removed = orig.replace("## Regras duras", "## Regras_duras_mutadas")
                open(wk, "w", encoding="utf-8").write(removed)
                r2, _ = run_harness()
                if r2 is None or r2["total"] >= res["total"]:
                    fails.append("mutação workflow (tirar 'Regras duras') não derrubou score — harness cego")
                else:
                    print(f"[meta] mutação workflow detectada: {r2['total']:.1f} < {res['total']:.1f} OK")
            finally:
                shutil.copy(backup, wk)
                shutil.rmtree(ctx, ignore_errors=True)

    print()
    if fails:
        print("FALHAS META-TESTE:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("META-TESTES OK: harness sensível, sem regressão real. Score atual >= baseline.")
    sys.exit(0)

if __name__ == "__main__":
    main()
