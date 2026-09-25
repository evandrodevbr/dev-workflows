#!/usr/bin/env python3
"""Execução headless e conservadora para Claude Code, OpenCode e OMP."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import secrets
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "agents"
OMP_TOOLS = {
    "Read": "read", "Edit": "edit", "Write": "write", "Bash": "bash",
    "Grep": "grep", "Glob": "glob", "WebFetch": "web_search",
    "WebSearch": "web_search", "NotebookEdit": "notebook",
}

OMP_THINKING_LEVELS = {"off", "minimal", "low", "medium", "high", "xhigh", "max", "auto"}



class HarnessError(RuntimeError):
    """Harness request cannot be safely or exactly dispatched."""


def _load_catalog_module():
    path = ROOT / "scripts" / "model_catalog.py"
    spec = importlib.util.spec_from_file_location("dev_workflows_model_catalog", path)
    if spec is None or spec.loader is None:
        raise HarnessError("catálogo local indisponível")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _agent(role: str) -> tuple[dict[str, str], str]:
    if not re.fullmatch(r"[a-z][a-z0-9-]*", role):
        raise HarnessError(f"papel inválido: {role!r}")
    path = AGENTS / f"{role}.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HarnessError(f"papel desconhecido: {role}") from exc
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, re.S)
    if not match:
        raise HarnessError(f"frontmatter inválido para papel {role}")
    meta = dict(re.findall(r"^(\w+):\s*(.*)$", match.group(1), re.M))
    if meta.get("name") != role:
        raise HarnessError(f"identidade inválida para papel {role}")
    return meta, match.group(2).replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))


def _model_for_cli(tool: str, model_key: str, meta: dict[str, str]) -> tuple[str | None, str]:
    """Return CLI selector and exact catalog key; never strip an unsupported variant."""
    if not isinstance(model_key, str) or not model_key:
        raise HarnessError("model_key obrigatório")
    if tool == "claude":
        if model_key == "inherit":
            inherited = meta.get("model", "")
            if inherited == "inherit":
                raise HarnessError("Claude `inherit` não identifica um modelo verificável para este papel")
            selector = inherited
            catalog_key = inherited
        else:
            selector = model_key
            catalog_key = model_key
        if selector not in {"haiku", "sonnet", "opus"} and not re.fullmatch(r"claude-[A-Za-z0-9.-]+", selector):
            raise HarnessError("Claude CLI aceita aliases haiku/sonnet/opus ou IDs Claude; model_key não é exato para esta ferramenta")
        return (None if model_key == "inherit" else selector), catalog_key
    if model_key == "inherit":
        raise HarnessError("inherit não identifica provider/model para esta ferramenta")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.:+/-]+(?:#[A-Za-z0-9_.+-]+)?", model_key):
        raise HarnessError(f"model_key inválido ou não exato para {tool}: {model_key!r}")
    return model_key, model_key


def _require_catalog_entry(tool: str, model_key: str, cache_dir: str | None) -> dict[str, Any]:
    catalog = _load_catalog_module()
    snapshot = catalog.load_snapshot(tool, cache_dir)
    if not isinstance(snapshot, dict) or snapshot.get("tool") != tool:
        raise HarnessError(f"snapshot local de {tool} indisponível; despacho bloqueado")
    matches = [row for row in snapshot.get("models", [])
               if isinstance(row, dict) and row.get("tool") == tool and row.get("model_key") == model_key]
    if len(matches) != 1:
        raise HarnessError(f"model_key {model_key!r} não é um ID exato e único no catálogo local de {tool}")
    availability = matches[0].get("availability")
    if not isinstance(availability, dict) or any(availability.get(field) is not True
                                                  for field in ("local_listed", "authenticated", "entitled")):
        raise HarnessError(f"disponibilidade/autorização local não verificada para {model_key!r}; despacho bloqueado")
    return matches[0]

def _role_tools(meta: dict[str, str]) -> list[str]:
    declared = {item.strip() for item in meta.get("tools", "").split(",") if item.strip()}
    return [name for name in ("Read", "Grep", "Glob", "Edit", "Write") if name in declared]


def _opencode_loop_agent(meta: dict[str, str], role_prompt: str) -> str:
    tools = set(_role_tools(meta))
    allowed = {
        "read": "Read" in tools,
        "edit": bool(tools & {"Edit", "Write"}),
        "glob": "Glob" in tools,
        "grep": "Grep" in tools,
        "list": False,
        "bash": False,
        "task": False,
        "external_directory": False,
        "todowrite": False,
        "webfetch": False,
        "websearch": False,
        "lsp": False,
        "skill": False,
        "question": False,
        "doom_loop": False,
    }
    lines = ["---", f"description: {json.dumps(meta['description'], ensure_ascii=False)}",
             "mode: primary", "permission:", '  "*": deny']
    lines.extend(f"  {name}: {'allow' if enabled else 'deny'}" for name, enabled in allowed.items())
    return "\n".join(lines + ["---", "", role_prompt])


def _memfd(contents: bytes) -> int:
    if not hasattr(os, "memfd_create"):
        raise HarnessError("sandbox requer suporte a memfd para config efêmera")
    fd = os.memfd_create("dev-workflows-harness")
    os.write(fd, contents)
    os.lseek(fd, 0, os.SEEK_SET)
    return fd


def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _validate_autonomous_worktree(cwd: str) -> None:
    worktree = Path(cwd).resolve()
    if worktree.parent.name != "worktrees" or not (
        worktree.name == "baseline" or re.fullmatch(r"iteration-[0-9]+", worktree.name)
    ):
        raise HarnessError("modo autônomo exige worktree isolado baseline/iteration-*")
    checkout = ROOT.resolve()
    if _within(worktree, checkout) or _within(checkout, worktree):
        raise HarnessError("modo autônomo não pode gravar no checkout de origem")
    marker = worktree / ".git"
    if marker.is_symlink() or not marker.is_file():
        raise HarnessError("cwd autônomo não é um git worktree")
    match = re.fullmatch(r"gitdir:\s*(.+)\s*", marker.read_text(encoding="utf-8"))
    if not match:
        raise HarnessError("ponteiro .git inválido no worktree autônomo")
    gitdir = Path(match.group(1))
    if not gitdir.is_absolute():
        gitdir = worktree / gitdir
    gitdir = gitdir.resolve()
    if not gitdir.is_dir() or _within(gitdir, worktree):
        raise HarnessError("gitdir do worktree autônomo ausente ou inseguro")


def _sandbox_path(cwd: str, env: dict[str, str]) -> str:
    worktree = Path(cwd).resolve()
    entries: list[str] = []
    seen: set[Path] = set()
    for entry in env.get("PATH", "").split(os.pathsep):
        path = Path(entry or cwd).expanduser()
        if not path.is_absolute():
            path = worktree / path
        try:
            path = path.resolve()
        except OSError:
            continue
        if not path.is_dir() or _within(path, worktree) or path in seen:
            continue
        seen.add(path)
        entries.append(str(path))
    return os.pathsep.join(entries)


def _sandbox_command(tool: str, command: list[str], cwd: str, env: dict[str, str],
                     opencode_agent: str | None = None, temp_root: str | None = None
                     ) -> tuple[list[str], tuple[int, ...]]:
    if env.get("DEV_WORKFLOWS_AUTONOMOUS") != "1":
        return command, ()
    bwrap = shutil.which("bwrap", path="/usr/bin:/bin")
    if not bwrap:
        raise HarnessError("modo autônomo requer bwrap; despacho bloqueado")
    if not temp_root:
        raise HarnessError("sandbox sem diretório temporário privado")
    temp_data = f"{temp_root}/data"
    temp_config = f"{temp_root}/config"
    args = [
        bwrap, "--unshare-all", "--share-net", "--die-with-parent",
        "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev",
        "--bind", temp_root, temp_root,
        "--dir", f"{temp_root}/tmp", "--dir", f"{temp_root}/cache",
        "--dir", f"{temp_root}/state", "--dir", temp_data,
    ]
    args.extend(("--setenv", "PATH", _sandbox_path(cwd, env)))
    pass_fds: list[int] = []
    if tool == "opencode":
        for directory in (temp_config, f"{temp_config}/opencode", f"{temp_config}/opencode/agents",
                          f"{temp_data}/opencode"):
            args.extend(("--dir", directory))
        args.extend(("--setenv", "XDG_CONFIG_HOME", temp_config,
                     "--setenv", "XDG_DATA_HOME", temp_data,
                     "--setenv", "TMPDIR", f"{temp_root}/tmp"))
        config_home = Path(env.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        configured = env.get("OPENCODE_CONFIG")
        if not configured:
            for filename in ("opencode.json", "opencode.jsonc"):
                candidate = config_home / "opencode" / filename
                if candidate.is_file():
                    configured = str(candidate)
                    break
        if configured:
            args.extend(("--setenv", "OPENCODE_CONFIG", configured))
        auth_home = Path(env.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
        auth_file = auth_home / "opencode" / "auth.json"
        if auth_file.is_file():
            auth_target = f"{temp_data}/opencode/auth.json"
            fd = _memfd(b"")
            pass_fds.append(fd)
            args.extend(("--file", str(fd), auth_target, "--ro-bind", str(auth_file), auth_target))
        if opencode_agent is not None:
            role_name = command[command.index("--agent") + 1]
            agent_target = f"{temp_config}/opencode/agents/{role_name}.md"
            fd = _memfd(opencode_agent.encode("utf-8"))
            pass_fds.append(fd)
            args.extend(("--file", str(fd), agent_target))
        args.extend(("--setenv", "XDG_CACHE_HOME", f"{temp_root}/cache",
                     "--setenv", "XDG_STATE_HOME", f"{temp_root}/state"))
    else:
        args.extend(("--setenv", "TMPDIR", f"{temp_root}/tmp",
                     "--setenv", "XDG_CACHE_HOME", f"{temp_root}/cache",
                     "--setenv", "XDG_STATE_HOME", f"{temp_root}/state"))
        if tool == "omp":
            args.extend(("--dir", f"{temp_root}/omp-agent",
                         "--setenv", "PI_CODING_AGENT_DIR", f"{temp_root}/omp-agent"))
        elif tool == "claude":
            args.extend(("--setenv", "CLAUDE_CODE_SKIP_PROMPT_HISTORY", "1"))
    marker = str(Path(cwd) / ".git")
    args.extend(("--bind", cwd, cwd, "--ro-bind", marker, marker, "--chdir", cwd, "--", *command))
    # The network namespace is shared for provider APIs; it is not an API-only egress filter.
    return args, tuple(pass_fds)


def _run_process(command: list[str], cwd: str, env: dict[str, str], timeout: float, tool: str,
                 opencode_agent: str | None = None) -> subprocess.CompletedProcess:
    autonomous = env.get("DEV_WORKFLOWS_AUTONOMOUS") == "1"
    temp_dir = None
    pass_fds: tuple[int, ...] = ()
    try:
        if autonomous:
            safe_path = _sandbox_path(cwd, env)
            if not safe_path:
                raise HarnessError("PATH seguro vazio; despacho bloqueado")
            executable = shutil.which(command[0], path=safe_path)
            if not executable:
                raise HarnessError(f"CLI {command[0]!r} não encontrado em PATH seguro")
            if _within(Path(executable).resolve(), Path(cwd).resolve()):
                raise HarnessError(f"CLI {command[0]!r} está dentro do worktree; despacho bloqueado")
            command = [executable, *command[1:]]
            temp_dir = tempfile.TemporaryDirectory(prefix="dev-workflows-harness-", dir="/tmp")
        wrapped, pass_fds = _sandbox_command(
            tool, command, cwd, env, opencode_agent, temp_dir.name if temp_dir else None
        )
        return subprocess.run(wrapped, cwd=cwd, env=env, capture_output=True, text=True,
                              errors="replace", timeout=timeout, check=False, pass_fds=pass_fds)
    finally:
        for fd in pass_fds:
            os.close(fd)
        if temp_dir is not None:
            temp_dir.cleanup()


def _claude_auth_status(cwd: str, env: dict[str, str], timeout: float) -> bool:
    try:
        result = _run_process(["claude", "auth", "status", "--json"], cwd, env, timeout, "claude")
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    try:
        status = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return isinstance(status, dict) and status.get("loggedIn") is True


def _omp_cli_model(row: dict[str, Any], model_key: str) -> tuple[str, str | None]:
    variant = row.get("variant")
    if variant is None:
        if "#" in model_key:
            raise HarnessError(f"model_key OMP variante sem metadado variant: {model_key!r}")
        return model_key, None
    if variant not in OMP_THINKING_LEVELS:
        raise HarnessError(f"OMP CLI não oferece seleção exata da variante {variant!r}")
    base_key, separator, key_variant = model_key.rpartition("#")
    if not separator or key_variant != variant:
        raise HarnessError(f"variante OMP não corresponde ao model_key canônico {model_key!r}")
    provider, model_id = row.get("provider"), row.get("model_id")
    if not isinstance(provider, str) or not isinstance(model_id, str) or base_key != f"{provider}/{model_id}":
        raise HarnessError(f"provider/model_id do catálogo não confirma {model_key!r}")
    return base_key, variant




def _local_models_command(tool: str, model_key: str, cwd: str, env: dict[str, str],
                          timeout: float, thinking: str | None = None) -> bool:
    provider, model = model_key.split("/", 1)
    base_model = model.split("#", 1)[0]
    autonomous = env.get("DEV_WORKFLOWS_AUTONOMOUS") == "1"
    if tool == "opencode":
        command = ["opencode"] + (["--pure"] if autonomous else []) + ["models", provider]
    else:
        command = ["omp"] + (["--no-extensions"] if autonomous else []) + ["models", provider, "--json"]
    try:
        result = _run_process(command, cwd, env, timeout, tool)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    if tool == "omp":
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return False
        return _json_catalog_has_model(payload, provider, base_model, thinking)
    for line in result.stdout.splitlines():
        candidate = line.strip().strip("`'\" ")
        if candidate.startswith(provider + "/"):
            candidate = candidate[len(provider) + 1:]
        if candidate in {model, base_model}:
            return True
    return False


def _json_catalog_has_model(value: Any, provider: str, model_id: str, thinking: str | None = None) -> bool:
    if isinstance(value, list):
        return any(_json_catalog_has_model(item, provider, model_id, thinking) for item in value)
    if not isinstance(value, dict):
        return False
    row_provider = value.get("provider") or value.get("providerID") or value.get("provider_id")
    row_id = value.get("id") or value.get("modelID") or value.get("model_id")
    full_id = value.get("selector") or value.get("model_key") or value.get("model")
    matches = ((row_provider == provider and row_id == model_id)
               or (isinstance(full_id, str) and full_id == f"{provider}/{model_id}"))
    if matches and (thinking is None or
                    (isinstance(value.get("thinking"), list) and thinking in value["thinking"])):
        return True
    return any(_json_catalog_has_model(item, provider, model_id, thinking) for item in value.values()
               if isinstance(item, (dict, list)))


def _omp_tools(meta: dict[str, str], autonomous: bool = False) -> list[str]:
    if autonomous:
        return [OMP_TOOLS[name] for name in _role_tools(meta)]
    declared = {item.strip() for item in meta.get("tools", "").split(",") if item.strip()}
    read_only = not bool(declared & {"Edit", "Write"})
    tool_order = ("Read", "Edit", "Write", "Bash", "Grep", "Glob", "WebFetch", "WebSearch", "NotebookEdit")
    return list(dict.fromkeys(
        OMP_TOOLS[name] for name in tool_order
        if name in declared and not (read_only and name in {"Edit", "Write", "Bash"})
    ))

def _omp_skills(meta: dict[str, str]) -> list[str]:
    match = re.search(r"\[(.*?)\]", meta.get("skills", ""))
    return re.findall(r"[\w-]+", match.group(1)) if match else []


def _stderr_summary(stderr: str) -> str:
    if not stderr:
        return ""
    lines = len(stderr.splitlines())
    return f"[stderr omitido por segurança: {lines} linha(s), {len(stderr)} caracteres]"


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def invoke(tool: str, role: str, prompt: str, cwd: str, model_key: str,
           timeout: float = 600, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Invoke one role; only bounded autonomous OMP dispatch uses auto-approval.

    The local catalog must attest local listing, authentication and entitlement.
    OpenCode/OMP local models are rechecked immediately before dispatch. Autonomous
    calls require bwrap and a tool allowlist; no fallback or config rewrite occurs.
    """
    if tool not in {"claude", "opencode", "omp"}:
        raise HarnessError(f"ferramenta não suportada: {tool!r}")
    if not isinstance(prompt, str) or not prompt:
        raise HarnessError("prompt vazio")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise HarnessError("timeout deve ser positivo")
    workdir = str(Path(cwd).resolve())
    if not Path(workdir).is_dir():
        raise HarnessError(f"cwd não existe ou não é diretório: {cwd!r}")
    child_env = os.environ.copy()
    if env is not None:
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in env.items()):
            raise HarnessError("env deve conter somente pares string/string")
        child_env.update(env)
    autonomous = child_env.get("DEV_WORKFLOWS_AUTONOMOUS") == "1"
    if autonomous:
        _validate_autonomous_worktree(workdir)
    meta, role_prompt = _agent(role)
    cli_model, catalog_key = _model_for_cli(tool, model_key, meta)
    cache_dir = child_env.get("DEV_WORKFLOWS_MODEL_CACHE")
    if tool == "claude":
        if not _claude_auth_status(workdir, child_env, float(timeout)):
            raise HarnessError("claude auth status não confirmou uma sessão autenticada; despacho bloqueado")
        row = None if model_key in {"haiku", "sonnet", "opus", "inherit"} else _require_catalog_entry(tool, catalog_key, cache_dir)
    else:
        row = _require_catalog_entry(tool, catalog_key, cache_dir)
    omp_thinking = None
    local_model_key = catalog_key
    if tool == "omp":
        cli_model, omp_thinking = _omp_cli_model(row, catalog_key)
        local_model_key = cli_model
    if tool in {"opencode", "omp"} and not _local_models_command(
            tool, local_model_key, workdir, child_env, float(timeout), omp_thinking):
        raise HarnessError(f"provider/model indisponível na CLI local de {tool}: {catalog_key!r}; despacho bloqueado")

    opencode_agent = None
    if tool == "claude":
        if autonomous:
            safe_tools = _role_tools(meta)
            agent_config = json.dumps({
                role: {"description": meta["description"], "prompt": role_prompt, "tools": safe_tools}
            }, ensure_ascii=False)
            command = [
                "claude", "--bare", "--no-session-persistence", "-p", "--agent", role,
                "--agents", agent_config, "--tools", ",".join(safe_tools),
                "--permission-mode", "dontAsk",
            ]
            if cli_model is not None:
                command.extend(("--model", cli_model))
            if safe_tools:
                command.extend(("--allowedTools", *safe_tools))
        else:
            command = ["claude", "-p", "--agent", role, "--permission-mode", "dontAsk"]
            if cli_model is not None:
                command.extend(("--model", cli_model))
        command.append(prompt)
    elif tool == "opencode":
        agent_name = f"dev-workflows-loop-{role}-{secrets.token_hex(8)}" if autonomous else role
        command = ["opencode"] + (["--pure"] if autonomous else []) + ["run", "--agent", agent_name]
        if cli_model is not None:
            command.extend(("--model", cli_model))
        command.append(prompt)
        if autonomous:
            opencode_agent = _opencode_loop_agent(meta, role_prompt)
    else:
        command = ["omp", "-p", "--cwd", workdir]
        if autonomous:
            command.extend(("--no-extensions", "--no-lsp", "--no-session", "--auto-approve"))
        else:
            command.extend(("--approval-mode", "always-ask"))
        if cli_model is not None:
            command.extend(("--model", cli_model))
        if omp_thinking is not None:
            command.extend(("--thinking", omp_thinking))
        command.extend(("--append-system-prompt", role_prompt))
        skills = _omp_skills(meta)
        if skills:
            command.extend(("--skills", ",".join(skills)))
        tools = _omp_tools(meta, autonomous=autonomous)
        if tools:
            command.extend(("--tools", ",".join(tools)))
        else:
            command.append("--no-tools")
        command.append(prompt)
    try:
        result = _run_process(command, workdir, child_env, float(timeout), tool, opencode_agent)
        returncode = result.returncode
        stdout, stderr = result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout, stderr = _text(exc.stdout), _text(exc.stderr)
    except OSError:
        return {"returncode": 127, "output": f"CLI {tool} indisponível", "usage": None}
    output = _text(stdout).rstrip()
    summary = _stderr_summary(_text(stderr))
    if summary:
        output = f"{output}\n{summary}" if output else summary
    return {"returncode": returncode, "output": output, "usage": None}
