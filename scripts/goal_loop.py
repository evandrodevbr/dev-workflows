#!/usr/bin/env python3
"""Opt-in, evaluator-driven experiments in detached git worktrees.

The user's branch is never reset, staged, merged, or published. Agent output is
untrusted; only the external evaluator and current quality-gate report decide.
"""
import argparse
import contextlib
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import tomllib
import uuid

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "scripts" / "quality-gate"
MODEL_CATALOG = ROOT / "scripts" / "model_catalog.py"


class LoopError(Exception):
    pass

class SafetyPause(LoopError):
    """The next model invocation is not authorized or cannot be budgeted."""



def command(argv, cwd, timeout=60, env=None):
    try:
        return subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LoopError(f"falha ao executar {argv[0]}: {exc}") from exc


def sandbox_binary():
    bwrap = next((path for path in ("/usr/bin/bwrap", "/bin/bwrap") if Path(path).is_file()), None)
    if not bwrap:
        raise LoopError("bubblewrap indisponível: não executar código do projeto sem isolamento")
    return bwrap


def preflight_isolation(project):
    """Prove namespace support without modifying the project or invoking a model."""
    result = command([sandbox_binary(), "--die-with-parent", "--new-session", "--unshare-net",
                      "--unshare-pid", "--ro-bind", "/", "/", "--dev-bind", "/dev", "/dev",
                      "--proc", "/proc", "--", "/usr/bin/true"], project, timeout=15)
    if result.returncode:
        raise LoopError(f"isolamento bubblewrap indisponível: {result.stderr.strip()[:300]}")


def isolated_command(argv, cwd, timeout=60, env=None, writable=()):
    """Run untrusted project checks with no network or write access outside mounts."""
    bwrap = sandbox_binary()
    repo = Path(cwd).resolve(strict=True)
    home = repo / ".dev-workflows" / "sandbox-home"
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    child_env = dict(os.environ if env is None else env)
    child_env.update(HOME=str(home), XDG_CACHE_HOME=str(home), TMPDIR=str(home),
                     PYTHONDONTWRITEBYTECODE="1")
    marker = repo / ".git"
    if marker.is_symlink() or not marker.is_file():
        raise LoopError("sandbox exige ponteiro .git de worktree regular")
    args = [bwrap, "--die-with-parent", "--new-session", "--unshare-net", "--unshare-pid",
            "--ro-bind", "/", "/", "--dev-bind", "/dev", "/dev", "--proc", "/proc",
            "--bind", str(repo), str(repo), "--ro-bind", str(marker), str(marker)]
    for directory in writable:
        resolved = Path(directory).resolve(strict=True)
        if not resolved.is_dir():
            raise LoopError(f"diretório de relatório inválido: {directory}")
        args.extend(("--bind", str(resolved), str(resolved)))
    args.extend(("--", *argv))
    return command(args, repo, timeout, child_env)



def git(root, *args):
    result = command(["git", *args], root)
    if result.returncode:
        raise LoopError(f"git {args[0]} falhou: {result.stderr.strip()[:300]}")
    return result.stdout.strip()


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def number(value, name):
    if isinstance(value, bool):
        raise LoopError(f"{name}: número inválido")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise LoopError(f"{name}: número inválido") from exc
    if not d.is_finite():
        raise LoopError(f"{name}: número não finito")
    return d


def bounded_timeout(limit, deadline=None):
    if deadline is None:
        return limit
    remaining = deadline - time.time()
    if remaining <= 0:
        raise LoopError("limite global de tempo esgotado")
    return min(limit, remaining)


def within(path, directory):
    return path == directory or directory in path.parents


def config_at(config_path):
    path = Path(config_path).resolve(strict=True)
    with path.open("rb") as source:
        config = tomllib.load(source)
    top = Path(git(path.parent, "rev-parse", "--show-toplevel")).resolve()
    if not within(path, top):
        raise LoopError("configuração deve estar no repositório avaliado")
    loop = config.get("loop", {})
    goal = loop.get("goal", {})
    evaluator = loop.get("evaluator", {})
    if not goal.get("name") or not goal.get("unit") or goal.get("direction") not in ("maximize", "minimize"):
        raise LoopError("[loop.goal] requer name, unit e direction maximize|minimize")
    target = number(goal.get("target"), "target")
    argv = evaluator.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x for x in argv):
        raise LoopError("[loop.evaluator].argv deve ser uma lista de argumentos")
    # An interpreter may precede the evaluator. The executable script must not
    # come from the editable checkout; a bare command in PATH is not auditable.
    candidate = argv[1] if Path(argv[0]).name in ("python", "python3", "node", "bun") and len(argv) > 1 else argv[0]
    script = Path(candidate)
    if not script.is_absolute() or not script.is_file():
        raise LoopError("avaliador precisa ser arquivo absoluto existente fora do worktree")
    script = script.resolve(strict=True)
    if within(script, top):
        raise LoopError("avaliador não pode residir no checkout editável")
    expected = evaluator.get("trusted_sha256", "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected) or digest(script) != expected.lower():
        raise LoopError("hash aprovado do avaliador não corresponde ao arquivo")
    required = evaluator.get("required_checks", [])
    if not isinstance(required, list) or not required or any(not isinstance(x, str) or not x for x in required):
        raise LoopError("required_checks deve listar os checks obrigatórios do gate")
    if evaluator.get("require_gate_verdict", "pass") != "pass":
        raise LoopError("loop exige veredito pass no quality gate")
    tier = loop.get("tier", 2)
    if type(tier) is not int or tier not in range(4):
        raise LoopError("[loop].tier deve estar entre 0 e 3")
    loop["tier"] = tier
    for key in ("max_iterations", "max_minutes", "max_stagnant"):
        if type(loop.get(key)) is not int or loop[key] < 1:
            raise LoopError(f"[loop].{key} deve ser inteiro positivo")
    if number(loop.get("min_improvement"), "min_improvement") <= 0:
        raise LoopError("min_improvement deve ser positivo")
    if number(loop.get("max_paid_usd", 0), "max_paid_usd") < 0:
        raise LoopError("max_paid_usd não pode ser negativo")
    if loop.get("harness") not in ("claude", "opencode", "omp"):
        raise LoopError("[loop].harness deve ser claude, opencode ou omp")
    if not git(top, "status", "--porcelain", "--untracked-files=all") == "":
        raise LoopError("working tree do usuário tem alterações; salve/snapshot antes de iniciar")
    return path, top, config, script, target


def state_root(project):
    default = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "dev-workflows"
    root = Path(os.environ.get("DW_STATE_HOME", default)).expanduser().resolve()
    if within(root, project) or within(project, root):
        raise LoopError("estado do controlador deve ficar fora do checkout do projeto")
    return root / hashlib.sha256(os.fsencode(project)).hexdigest()[:20]


def prepare_home(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)


@contextlib.contextmanager
def locked(home):
    prepare_home(home)
    with (home / "lock").open("a+") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise LoopError("já existe uma execução ativa neste projeto") from exc
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def save(folder, state):
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = folder / "state.json"
    tmp = folder / f".{uuid.uuid4().hex}.json"
    with tmp.open("x") as out:
        os.chmod(tmp, 0o600)
        json.dump(state, out, ensure_ascii=False, indent=2)
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, path)


def load(home, run_id):
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise LoopError("ID de execução inválido")
    path = home / run_id / "state.json"
    if not path.is_file():
        raise LoopError("execução não encontrada")
    with path.open() as f:
        state = json.load(f)
    return path.parent, state


def evaluator_result(cfg, script, repo, folder, deadline=None):
    if digest(script) != cfg["loop"]["evaluator"]["trusted_sha256"].lower():
        raise LoopError("avaliador protegido foi alterado")
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    env = os.environ.copy()
    env["DW_REPORT_DIR"] = str(folder)
    argv = cfg["loop"]["evaluator"]["argv"]
    result = isolated_command(argv, repo, bounded_timeout(
        int(cfg["loop"]["evaluator"].get("timeout_seconds", 600)), deadline), env, writable=[folder])
    if result.returncode:
        raise LoopError(f"avaliador retornou {result.returncode}: {result.stderr.strip()[:300]}")
    if digest(script) != cfg["loop"]["evaluator"]["trusted_sha256"].lower():
        raise LoopError("avaliador protegido foi alterado durante a avaliação")
    try:
        data = json.loads(result.stdout, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NaN")))
        score = number(data["value"], "score")
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise LoopError("avaliador não produziu JSON com score válido") from exc
    goal = cfg["loop"]["goal"]
    if (data.get("schema_version") != 1 or data.get("metric") != goal["name"]
            or data.get("unit") != goal["unit"] or data.get("direction") != goal["direction"]):
        raise LoopError("métrica/unidade/direção divergente da meta")
    checks = data.get("checks")
    if not isinstance(checks, dict) or not checks or any(x != "pass" for x in checks.values()):
        raise LoopError("avaliador não aprovou todos os seus checks")
    paths = data.get("evidence")
    if not isinstance(paths, list) or not paths:
        raise LoopError("avaliador não forneceu evidência verificável")
    evidence = []
    for raw in paths:
        if not isinstance(raw, str):
            raise LoopError("caminho inválido de evidência")
        p = Path(raw).resolve(strict=False)
        if not p.is_file() or not within(p, folder.resolve()):
            raise LoopError("evidência deve existir fora do worktree no diretório de relatórios")
        evidence.append({"file": str(p), "sha256": digest(p)})
    return score, evidence, checks


def attained(score, target, direction):
    return score >= target if direction == "maximize" else score <= target


def improved(score, best, minimum, direction):
    return score - best >= minimum if direction == "maximize" else best - score >= minimum


def worktree(project, folder, ref):
    if folder.exists():
        raise LoopError(f"worktree já existe: {folder}")
    folder.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    git(project, "-c", "core.hooksPath=/dev/null", "worktree", "add", "--detach", str(folder), ref)
    return folder

def assert_worktree(project, repo, expected_head, marker_sha256=None):
    """Reject redirected Git pointers or a branch before controller Git writes."""
    marker = repo / ".git"
    if marker.is_symlink() or not marker.is_file():
        raise LoopError("ponteiro .git do worktree foi removido ou substituído")
    try:
        text = marker.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise LoopError("ponteiro .git do worktree ilegível") from exc
    match = re.fullmatch(r"gitdir: ([^\r\n]+)\r?\n?", text)
    if not match:
        raise LoopError("ponteiro .git do worktree inválido")
    marker_hash = digest(marker)
    if marker_sha256 is not None and marker_hash != marker_sha256:
        raise LoopError("ponteiro .git do worktree mudou durante a tentativa")
    admin = Path(match.group(1))
    admin = (repo / admin).resolve() if not admin.is_absolute() else admin.resolve()
    common = Path(git(project, "rev-parse", "--git-common-dir"))
    common = (project / common).resolve() if not common.is_absolute() else common.resolve()
    if not admin.is_dir() or admin.parent != common / "worktrees":
        raise LoopError("gitdir do worktree não pertence ao repositório original")
    actual = command(["git", "rev-parse", "--absolute-git-dir"], repo)
    if actual.returncode or Path(actual.stdout.strip()).resolve() != admin:
        raise LoopError("ponteiro .git redireciona o worktree")
    detached = command(["git", "symbolic-ref", "-q", "HEAD"], repo)
    if detached.returncode != 1 or git(repo, "rev-parse", "HEAD") != expected_head:
        raise LoopError("worktree não está no commit detached esperado")
    return marker_hash



def changed_paths(repo, base):
    changed = set(git(repo, "diff", "--name-only", base).splitlines())
    changed.update(git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
    return sorted(p for p in changed if p and not p.startswith(".dev-workflows/"))


def fingerprint(repo, names):
    h = hashlib.sha256()
    for name in names:
        p = repo / name
        h.update(os.fsencode(name))
        h.update(b"\0")
        if p.is_symlink():
            h.update(os.fsencode(os.readlink(p)))
        elif p.is_file():
            h.update(digest(p).encode())
            h.update(str(p.stat().st_mode & 0o777).encode())
        else:
            h.update(b"deleted")
    return h.hexdigest()


def gate_result(repo, base, tier, required, changes, deadline=None):
    t = time.time_ns()
    result = isolated_command([sys.executable, str(GATE), "--dir", str(repo), "--base", base,
                               "--tier", str(tier)], repo, bounded_timeout(3600, deadline))
    report_path = repo / ".dev-workflows" / "gate.json"
    if not report_path.is_file() or report_path.stat().st_mtime_ns < t:
        raise LoopError("quality gate não gerou relatório atual")
    report = json.loads(report_path.read_text())
    if result.returncode or report.get("verdict") != "pass" or report.get("base") != base or report.get("tier") != tier:
        raise LoopError(f"quality gate não aprovou o diff: {report.get('verdict', 'sem relatório')}")
    checks = {c.get("name"): c.get("status") for c in report.get("checks", [])}
    if any(checks.get(name) != "pass" for name in required):
        raise LoopError("checks obrigatórios ausentes, não verificados ou falhos")
    deleted = set(git(repo, "diff", "--name-only", "--diff-filter=D", base).splitlines())
    if not set(changes).difference(deleted).issubset(set(report.get("changed_files", []))):
        raise LoopError("quality gate não cobriu todos os arquivos alterados")
    return {"verdict": report["verdict"], "tier": tier, "checks": checks,
            "base": base, "changed_files": report["changed_files"], "sha256": digest(report_path)}


def role_model(config, tool, role, cwd):
    models = config.get("models", {})
    role_cfg = models.get("roles", {}).get(role, {})
    if role_cfg.get("model_key"):
        if not role_cfg.get("manual_unranked_approval", False):
            raise LoopError(f"{role}: modelo fixado sem aprovação explícita unranked")
        if tool != "claude" or role_cfg.get("billing_mode") != "claude_subscription":
            raise LoopError("modelo fixo não substitui descoberta de disponibilidade/conta em OpenCode ou OMP")
        model_key = role_cfg["model_key"]
        if model_key not in ("haiku", "sonnet", "opus", "inherit"):
            raise LoopError("Claude por assinatura aceita apenas aliases de modelo suportados")
        return {"model_key": model_key, "billing_mode": "claude_subscription",
                "score": None, "reason": "unranked: fixado explicitamente pelo usuário"}
    providers = models.get("allowed_providers")
    if not isinstance(providers, list) or not providers or any(not isinstance(x, str) for x in providers):
        raise LoopError("[models].allowed_providers deve listar os providers autorizados da conta")
    argv = [sys.executable, str(MODEL_CATALOG), "route", "--tool", tool, "--role", role,
            "--providers", ",".join(providers), "--format", "json",
            "--budget-usd", str(number(config["loop"].get("max_paid_usd", 0), "max_paid_usd"))]
    if models.get("benchmark_metric"):
        argv.extend(["--benchmark-metric", models["benchmark_metric"]])
    if models.get("bands"):
        argv.extend(["--bands-json", json.dumps(models["bands"])])
    for key, flag in (("max_price_age_hours", "--max-price-age-hours"),
                      ("max_score_age_days", "--max-score-age-days")):
        if key in models:
            argv.extend([flag, str(models[key])])
    if role_cfg.get("band"):
        argv.extend(["--band", role_cfg["band"]])
    if "max_loss_points" in role_cfg:
        argv.extend(["--max-loss-points", str(role_cfg["max_loss_points"])])
    if "tokens" in role_cfg:
        argv.extend(["--tokens", json.dumps(role_cfg["tokens"])])
    if (models.get("allow_proxy_score") and role_cfg.get("allow_proxy_score", True)
            and config["loop"]["tier"] < 3):
        argv.append("--allow-proxy-score")
    if models.get("cache_dir"):
        argv.extend(["--cache-dir", models["cache_dir"]])
    p = command(argv, cwd)
    if p.returncode:
        raise LoopError(f"roteamento {role}: {p.stderr.strip()[:300]}")
    try:
        result = json.loads(p.stdout)
        selected = result.get("selected")
        if not selected or not selected.get("model_key"):
            raise LoopError(f"{role}: sem modelo elegível: {result.get('reason', 'sem nota')}")
    except (ValueError, AttributeError) as exc:
        raise LoopError("roteador não devolveu JSON válido") from exc
    return selected


def authorize(config, model, remaining):
    billing = model.get("billing_mode")
    if billing in ("free", "subscription", "claude_subscription"):
        return
    if billing == "go":
        quota = model.get("quota_window_remaining")
        debit = model.get("quota_window_debit")
        if (not isinstance(quota, dict) or not isinstance(debit, dict) or
                any(k not in quota or k not in debit or number(quota[k], k) < number(debit[k], k)
                    for k in ("5h", "weekly", "monthly"))):
            raise SafetyPause("Go: cota não confirmada nas três janelas; sem fallback para saldo Zen")
        if model.get("use_balance_fallback") is not False:
            raise SafetyPause("Go: fallback para saldo Zen desconhecido ou cobrado; não autorizado")
        return
    if billing not in ("zen", "payg"):
        raise SafetyPause("modalidade de cobrança desconhecida; despacho não autorizado")
    label = "Zen" if billing == "zen" else "API paga"
    if model.get("balance_confirmed") is not True:
        raise SafetyPause(f"{label}: saldo ou permissão de cobrança da conta não confirmado")
    cap = number(config["loop"].get("max_paid_usd", 0), "max_paid_usd")
    estimate = model.get("estimated_native_usd")
    if cap == 0 or estimate is None or number(estimate, "estimated_native_usd") > cap - remaining:
        raise SafetyPause(f"{label}: orçamento explícito e estimativa nativa atual são obrigatórios")
    if not sys.stdin.isatty():
        raise SafetyPause(f"{label}: autorização interativa exigida imediatamente antes do gasto")
    question = (f"Autorizar {model['model_key']} via {label}, estimativa USD {estimate}, "
                f"limite restante USD {cap - remaining}? Digite SIM: ")
    if input(question) != "SIM":
        raise SafetyPause(f"gasto {label} não autorizado")

def mark_call_pending(state, folder, model):
    if model.get("billing_mode") in ("zen", "payg", "go"):
        state["unreconciled_paid_call"] = True
        save(folder, state)



def selected_roles(config, cwd):
    tier = config["loop"]["tier"]
    roles = ["implementer"]
    if tier >= 2:
        roles = ["planner", "implementer", "reviewer"]
    if tier >= 3:
        roles.append("security-auditor")
    return {role: role_model(config, config["loop"]["harness"], role, cwd) for role in roles}


def same_route(previous, current):
    return all(previous.get(key) == current.get(key) for key in
               ("model_key", "billing_mode", "provider", "variant", "estimated_native_usd", "native_tariff"))


def verified_model(config, state, role):
    previous = state["route_plan"][role]
    if previous.get("billing_mode") == "claude_subscription":
        return previous  # CLI authentication is checked immediately before dispatch.
    try:
        current = role_model(config, config["loop"]["harness"], role, Path(state["project"]))
    except LoopError as exc:
        raise SafetyPause(f"{role}: disponibilidade, preço ou quota não revalidada: {exc}") from exc
    if not same_route(previous, current):
        raise SafetyPause(f"{role}: rota ou tarifa mudou; novo plan e aprovação necessários")
    if current.get("billing_mode") == "go":
        for key in ("5h", "weekly", "monthly"):
            current["quota_window_remaining"][key] = str(min(
                number(previous["quota_window_remaining"][key], key),
                number(current["quota_window_remaining"][key], key)))
    state["route_plan"][role] = current
    return current


def report_run(state):
    return {k: state.get(k) for k in
            ("run_id", "status", "baseline_score", "best_score", "target", "iteration",
             "best_commit", "best_worktree", "spent_paid_usd", "elapsed_seconds",
             "baseline_evidence", "baseline_checks", "baseline_gate", "attempts",
             "route_plan", "gate_sha256", "evaluator_sha256", "error")}


def plan(config_path):
    path, project, cfg, script, target = config_at(config_path)
    preflight_isolation(project)
    routes = {}
    roles = (["planner", "implementer", "reviewer", "security-auditor"] if cfg["loop"]["tier"] >= 3
             else ["planner", "implementer", "reviewer"] if cfg["loop"]["tier"] >= 2 else ["implementer"])
    preflight = command([sys.executable, str(GATE), "--dir", str(project),
                         "--base", git(project, "rev-parse", "HEAD"),
                         "--tier", str(cfg["loop"]["tier"]), "--list"], project)
    if preflight.returncode:
        raise LoopError(f"quality gate indisponível: {preflight.stderr.strip()[:300]}")
    planned = {fields[1]: " ".join(fields[3:]) for line in preflight.stdout.splitlines()
               if len(fields := line.split()) >= 4 and fields[0].startswith("T")}
    gate = {name: planned.get(name, "ausente") for name in cfg["loop"]["evaluator"]["required_checks"]}
    for role in roles:
        try:
            routes[role] = role_model(cfg, cfg["loop"]["harness"], role, project)
        except LoopError as exc:
            routes[role] = {"status": "unavailable", "reason": str(exc)}
    return {"config": str(path), "enabled": cfg["loop"].get("enabled", False), "root": str(project),
            "evaluator_sha256": digest(script), "gate_sha256": digest(GATE),
            "baseline": "not_run", "target": str(target),
            "tier": cfg["loop"]["tier"], "routes": routes, "gate_preflight": gate,
            "risks": ["modelos e permissões devem ser revalidados antes de cada chamada",
                      "worktree não substitui isolamento de processo e acesso a rede",
                      "preço OpenRouter não equivale à cobrança da ferramenta"],
            "max_paid_usd": str(number(cfg["loop"].get("max_paid_usd", 0), "max_paid_usd"))}


def new_run(config_path):
    path, project, cfg, script, target = config_at(config_path)
    if cfg["loop"].get("enabled") is not True:
        raise LoopError("loop desativado: habilite [loop].enabled explicitamente")
    home = state_root(project)
    with locked(home):
        routes = selected_roles(cfg, project)
        for model in routes.values():
            if (model.get("billing_mode") in ("zen", "payg")
                    and number(cfg["loop"].get("max_paid_usd", 0), "max_paid_usd") == 0):
                raise LoopError("modelo pago: gasto não autorizado; max_paid_usd=0")
        base = git(project, "rev-parse", "HEAD")
        run_id = uuid.uuid4().hex
        folder = home / run_id
        folder.mkdir(mode=0o700)
        work = worktree(project, folder / "worktrees" / "baseline", base)
        state = {"version": 1, "run_id": run_id, "project": str(project), "config": str(path),
                 "config_sha256": digest(path), "evaluator_sha256": digest(script),
                 "gate_sha256": digest(GATE), "base": base,
                 "best_commit": base, "best_worktree": str(work), "best_score": None,
                 "baseline_score": None,
                 "target": str(target), "iteration": 0, "spent_paid_usd": "0", "stagnant": 0,
                 "started_at": time.time(), "elapsed_seconds": 0, "status": "planned", "attempts": [],
                 "route_plan": routes}
        save(folder, state)
        try:
            deadline = state["started_at"] + cfg["loop"]["max_minutes"] * 60
            score, evidence, checks = evaluator_result(
                cfg, script, work, folder / "evidence" / "baseline", deadline)
            if changed_paths(work, base):
                raise LoopError("avaliador modificou baseline; medição inicial inválida")
            state.update(best_score=str(score), baseline_score=str(score), baseline_evidence=evidence,
                         baseline_checks=checks, status="baselined")
            save(folder, state)
            if attained(score, target, cfg["loop"]["goal"]["direction"]):
                state["baseline_gate"] = gate_result(work, base, cfg["loop"]["tier"],
                                                     cfg["loop"]["evaluator"]["required_checks"], [], deadline)
                state["status"] = "success"
                save(folder, state)
            else:
                iterate(folder, state, cfg, script)
        except (LoopError, OSError, ValueError) as exc:
            state.update(status="error", error=str(exc))
            save(folder, state)
        return report_run(state)


def check_resumption(state, cfg, project, script, path):
    if state["project"] != str(project) or state["config_sha256"] != digest(path):
        raise LoopError("configuração/checkout mudou desde o início; não retomar automaticamente")
    if (state["evaluator_sha256"] != digest(script) or state["gate_sha256"] != digest(GATE)
            or git(project, "rev-parse", "HEAD") != state["base"]):
        raise LoopError("avaliador, gate ou base Git mudaram; retomar exige nova avaliação")
    if state["status"] not in ("exhausted", "paused", "running", "baselined"):
        raise LoopError(f"execução com estado {state['status']} não pode ser retomada")
    if state.get("unreconciled_paid_call"):
        raise LoopError("tentativa paga com consumo/quota indeterminados; concilie antes de novo run")
    routes = selected_roles(cfg, project)
    if set(routes) != set(state["route_plan"]) or any(
            not same_route(state["route_plan"][role], fresh) for role, fresh in routes.items()):
        raise LoopError("catálogo, preço, conta ou modelos mudaram; não retomar sem novo plan")
    if not Path(state["best_worktree"]).is_dir():
        raise LoopError("worktree vencedor foi removido; não retomar")


def resume_run(config_path, run_id):
    path, project, cfg, script, target = config_at(config_path)
    home = state_root(project)
    with locked(home):
        folder, state = load(home, run_id)
        check_resumption(state, cfg, project, script, path)
        if (state["status"] == "running" and len(state["attempts"]) < state["iteration"]
                and any(row.get("billing_mode") in ("zen", "payg", "go") for row in state["route_plan"].values())):
            raise LoopError("tentativa paga interrompida: consumo/quota indeterminados; concilie antes de novo run")
        if cfg["loop"].get("enabled") is not True:
            raise LoopError("loop desativado")
        if state["status"] == "running" and len(state["attempts"]) < state["iteration"]:
            state["attempts"].append({"iteration": state["iteration"], "result": "interrupted", "reason": "tentativa interrompida, não reutilizada"})
        state["status"] = "baselined"
        save(folder, state)
        try:
            iterate(folder, state, cfg, script)
        except (LoopError, OSError, ValueError) as exc:
            state.update(status="error", error=str(exc))
            save(folder, state)
        return report_run(state)


def iterate(folder, state, cfg, script):
    from harness_runner import invoke

    minimum = number(cfg["loop"]["min_improvement"], "min_improvement")
    target = number(state["target"], "target")
    project = Path(state["project"])
    path = Path(state["config"])
    direction = cfg["loop"]["goal"]["direction"]
    deadline = state["started_at"] + cfg["loop"]["max_minutes"] * 60
    while state["iteration"] < cfg["loop"]["max_iterations"]:
        if (folder / "stop.requested").exists():
            state["status"] = "cancelled"
            break
        if time.time() >= deadline:
            state["status"] = "exhausted"
            break
        if state["stagnant"] >= cfg["loop"]["max_stagnant"]:
            state["status"] = "exhausted"
            break
        if (digest(path) != state["config_sha256"] or digest(script) != state["evaluator_sha256"]
                or digest(GATE) != state["gate_sha256"]):
            state["status"] = "paused"
            state["error"] = "configuração, avaliador ou gate alterado durante a execução"
            break
        if git(project, "rev-parse", "HEAD") != state["base"] or git(project, "status", "--porcelain", "--untracked-files=all"):
            state["status"] = "paused"
            state["error"] = "checkout original alterado durante a execução; preservar mudanças do usuário"
            break
        step = state["iteration"] + 1
        base = state["best_commit"]
        work = worktree(project, folder / "worktrees" / f"iteration-{step:03}", base)
        marker_hash = assert_worktree(project, work, base)
        state.update(status="running", iteration=step)
        save(folder, state)
        attempt = {"iteration": step, "worktree": str(work), "from": base}
        paid = number(state["spent_paid_usd"], "spent_paid_usd")
        try:
            tool = cfg["loop"]["harness"]
            routes = state["route_plan"]
            timeout = int(cfg["loop"].get("agent_timeout_seconds", 900))
            prompt = (f"Use dev-router com tier mínimo {cfg['loop']['tier']}. Meta do aplicativo: "
                      f"{cfg['loop']['goal']['name']} {direction} {target} {cfg['loop']['goal']['unit']}. "
                      f"Score atual {state['best_score']}. Faça UMA hipótese pequena por iteração; "
                      "preserve testes e quality gate. Não modifique o avaliador, config, catálogos ou testes protegidos. "
                      "Não publique, instale dependências ou produza efeitos externos sem autorização. "
                      f"Feedback anterior: {state['attempts'][-1]['reason'] if state['attempts'] else 'nenhum'}. ")
            if "planner" in routes:
                model = verified_model(cfg, state, "planner")
                authorize(cfg, model, paid)
                mark_call_pending(state, folder, model)
                planned = invoke(tool, "planner", prompt + "Planeje uma única hipótese; só leitura.", str(work),
                                 model["model_key"], timeout=bounded_timeout(timeout, deadline),
                                 env={"DEV_WORKFLOWS_AUTONOMOUS": "1"})
                assert_worktree(project, work, base, marker_hash)
                paid = charged(planned, model, cfg, state, folder)
                if planned["returncode"]:
                    raise SafetyPause("planejamento falhou; nenhuma outra chamada autorizada")
                prompt += "Plano (não é autorização): " + planned["output"][:3000] + ". "
            model = verified_model(cfg, state, "implementer")
            authorize(cfg, model, paid)
            mark_call_pending(state, folder, model)
            done = invoke(tool, "implementer", prompt + "Implemente e relate nível declarado e evidências.", str(work),
                          model["model_key"], timeout=bounded_timeout(timeout, deadline),
                          env={"DEV_WORKFLOWS_AUTONOMOUS": "1"})
            paid = charged(done, model, cfg, state, folder)
            if done["returncode"]:
                raise SafetyPause("agente de implementação falhou; nenhuma outra chamada autorizada")
            assert_worktree(project, work, base, marker_hash)
            changes = changed_paths(work, base)
            if not changes:
                raise LoopError("agente não modificou código verificável")
            if path.relative_to(project).as_posix() in changes or any(c.startswith(".dev-workflows/") for c in changes):
                raise LoopError("tentativa alterou configuração ou estado protegido")
            if (git(project, "rev-parse", "HEAD") != state["base"]
                    or git(project, "status", "--porcelain", "--untracked-files=all")):
                raise LoopError("checkout original alterado durante a tentativa; preservar mudanças do usuário")
            assert_worktree(project, work, base, marker_hash)
            # This commit is only a candidate in a detached worktree, never a promotion.
            git(work, "add", "-A", "--", ".", ":(exclude).dev-workflows/**")
            git(work, "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgSign=false",
                "-c", "user.name=Dev Workflows", "-c", "user.email=dev-workflows@localhost",
                "commit", "-m", f"dev-workflows: candidate iteration {step}")
            candidate_commit = git(work, "rev-parse", "HEAD")
            assert_worktree(project, work, candidate_commit, marker_hash)
            if git(project, "rev-parse", "HEAD") != state["base"]:
                raise LoopError("checkout original alterado durante o snapshot")

            # Gate/review the exact commit, not agent-created ignored files.
            verified = worktree(project, folder / "verification" / "worktrees" / f"iteration-{step:03}", candidate_commit)
            verified_marker = assert_worktree(project, verified, candidate_commit)
            if changed_paths(verified, base) != changes:
                raise LoopError("snapshot da tentativa diverge dos arquivos alterados")
            before = fingerprint(verified, changes)
            gate = gate_result(verified, base, cfg["loop"]["tier"],
                               cfg["loop"]["evaluator"]["required_checks"], changes, deadline)
            assert_worktree(project, verified, candidate_commit, verified_marker)
            if changed_paths(verified, base) != changes or before != fingerprint(verified, changes):
                raise LoopError("código mudou durante o quality gate")
            attempt["gate"] = gate
            for role in ("reviewer", "security-auditor"):
                if role in routes:
                    model = verified_model(cfg, state, role)
                    authorize(cfg, model, paid)
                    mark_call_pending(state, folder, model)
                    review = invoke(tool, role, "Revise exclusivamente o diff da tentativa. Responda JSON: "
                                    '{"verdict":"pass|fail","findings":[]}.', str(verified), model["model_key"],
                                    timeout=bounded_timeout(timeout, deadline),
                                    env={"DEV_WORKFLOWS_AUTONOMOUS": "1"})
                    paid = charged(review, model, cfg, state, folder)
                    if review["returncode"]:
                        raise SafetyPause(f"{role} falhou; nenhuma outra chamada autorizada")
                    if review_verdict(review["output"]) != "pass":
                        raise LoopError(f"{role} rejeitou ou não concluiu a revisão")
            assert_worktree(project, verified, candidate_commit, verified_marker)
            if changed_paths(verified, base) != changes or fingerprint(verified, changes) != before:
                raise LoopError("código mudou depois do gate/revisão")

            # Score a second clean checkout: gate artifacts cannot bias the metric.
            scored = worktree(project, folder / "scoring" / "worktrees" / f"iteration-{step:03}", candidate_commit)
            scored_marker = assert_worktree(project, scored, candidate_commit)
            try:
                score, evidence, checks = evaluator_result(
                    cfg, script, scored, folder / "evidence" / f"iteration-{step:03}", deadline)
            except LoopError as exc:
                raise SafetyPause(f"avaliador inválido: {exc}") from exc
            assert_worktree(project, scored, candidate_commit, scored_marker)
            if (changed_paths(scored, candidate_commit) or digest(path) != state["config_sha256"]
                    or git(project, "rev-parse", "HEAD") != state["base"]):
                raise LoopError("código/configuração/base mudou durante a avaliação")
            attempt.update(score=str(score), evidence=evidence, evaluator_checks=checks)
            best = number(state["best_score"], "best_score")
            if not improved(score, best, minimum, direction):
                raise LoopError(f"sem melhoria mínima sobre {best}: score {score}")
            bounded_timeout(1, deadline)
            state.update(best_commit=candidate_commit, best_worktree=str(scored), best_score=str(score), stagnant=0)
            attempt.update(result="accepted", reason="melhoria medida em snapshot limpo e gate aprovado",
                           commit=candidate_commit)
            if attained(score, target, direction):
                state["status"] = "success"
        except SafetyPause as exc:
            attempt.update(result="paused", reason=str(exc))
            state["status"] = "paused"
        except RuntimeError as exc:
            attempt.update(result="paused", reason=f"runtime recusou ou falhou: {exc}")
            state["status"] = "paused"
        except (LoopError, OSError, ValueError) as exc:
            attempt.update(result="rejected", reason=str(exc))
            state["stagnant"] += 1
        state["attempts"].append(attempt)
        state["elapsed_seconds"] = round(time.time() - state["started_at"], 2)
        save(folder, state)
        if state["status"] in ("success", "paused"):
            break
    else:
        state["status"] = "exhausted"
    if state["status"] == "running":
        state["status"] = "exhausted"
    save(folder, state)


def usage_cost(result, model):
    value = (result.get("usage") or {}).get("cost_usd")
    if model.get("billing_mode") in ("zen", "payg") and value is None:
        raise SafetyPause("modelo pago: custo real da chamada não foi informado; pausa obrigatória")
    cost = number(value, "cost_usd") if value is not None else Decimal(0)
    if cost < 0:
        raise SafetyPause("custo negativo informado pelo provedor; pausa obrigatória")
    if model.get("billing_mode") == "go":
        quota = model["quota_window_remaining"]
        debit = model["quota_window_debit"]
        for window in ("5h", "weekly", "monthly"):
            quota[window] = str(number(quota[window], window) - number(debit[window], window))
    return cost if model.get("billing_mode") in ("zen", "payg") else Decimal(0)


def charged(result, model, config, state, folder):
    total = number(state["spent_paid_usd"], "spent_paid_usd") + usage_cost(result, model)
    state["spent_paid_usd"] = str(total)
    if model.get("billing_mode") in ("zen", "payg", "go"):
        state["unreconciled_paid_call"] = False
    save(folder, state)
    if (model.get("billing_mode") in ("zen", "payg")
            and total > number(config["loop"]["max_paid_usd"], "max_paid_usd")):
        raise SafetyPause(f"modelo pago: custo real USD {total} excedeu limite aprovado; nenhuma outra chamada autorizada")
    return total


def review_verdict(output):
    try:
        report = json.loads(output)
    except ValueError:
        return "invalid"
    return report.get("verdict") if report.get("verdict") in ("pass", "fail") and isinstance(report.get("findings"), list) else "invalid"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("plan", "run", "status", "resume", "stop"))
    parser.add_argument("--config", default=".dev-workflows.toml")
    parser.add_argument("--run", dest="run_id")
    args = parser.parse_args(argv)
    try:
        if args.action == "plan":
            result = plan(args.config)
        elif args.action == "run":
            result = new_run(args.config)
        else:
            if not args.run_id:
                raise LoopError("--run <id> obrigatório")
            path = Path(args.config).resolve(strict=True)
            project = Path(git(path.parent, "rev-parse", "--show-toplevel")).resolve()
            home = state_root(project)
            if args.action == "resume":
                result = resume_run(args.config, args.run_id)
            else:
                folder, state = load(home, args.run_id)
                if args.action == "stop":
                    (folder / "stop.requested").touch(exist_ok=True)
                result = report_run(state)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if args.action in ("plan", "status", "stop") or result.get("status") == "success" else 1
    except (LoopError, FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
