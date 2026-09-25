"""Build the native OMP package from the canonical dev-workflows checkout."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path


OWNER_MARKER = ".dev-workflows-omp-package"
def _owner_value(src: Path) -> str:
    return f"dev-workflows\nsource_root={src}\n"


def _content_digest(package: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(package.rglob("*")):
        if path.is_symlink():
            raise FileExistsError(f"symlink em pacote gerado: {path}")
        if not path.is_file() or path.name == OWNER_MARKER:
            continue
        h.update(path.relative_to(package).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(str(path.stat().st_mode & 0o777).encode("ascii"))
        with path.open("rb") as src:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()

AGENT_NAMES = (
    "explorer", "implementer", "planner", "reviewer",
    "security-auditor", "ui-critic", "verifier",
)
MODEL_ID = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?::(?:none|minimal|low|medium|high|xhigh|max))?$")
TOOL_NAMES = {
    "Read": "read", "Edit": "edit", "Write": "write", "Bash": "bash",
    "Grep": "grep", "Glob": "glob", "WebFetch": "web_search",
}


def _agent(src: Path, name: str, models: dict[str, str], package_root: Path) -> str:
    text = (src / "agents" / f"{name}.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", text, re.S)
    if not match:
        raise ValueError(f"frontmatter inválido em agents/{name}.md")
    raw, prompt = match.groups()
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    if meta.get("name") != name or not meta.get("description"):
        raise ValueError(f"metadados incompletos em agents/{name}.md")

    source_tools = [item.strip() for item in meta.get("tools", "").split(",") if item.strip()]
    # An explicit OMP allowlist prevents read-only agents from inheriting write tools.
    tools = list(dict.fromkeys(TOOL_NAMES[item] for item in source_tools if item in TOOL_NAMES))
    if not tools:
        raise ValueError(f"nenhuma ferramenta OMP reconhecida em agents/{name}.md")
    lines = ["---", f"name: {name}", f"description: {meta['description']}", "tools: " + ", ".join(tools)]
    skills = re.search(r"^skills:\s*\[(.*?)\]\s*$", raw, re.M)
    if skills:
        values = [value.strip().strip("'\"") for value in skills.group(1).split(",") if value.strip()]
        if values:
            lines.append("autoloadSkills:")
            lines.extend(f"  - {value}" for value in values)
    model = models.get(name)
    if model is not None:
        if not isinstance(model, str) or not MODEL_ID.fullmatch(model):
            raise ValueError(f"ID de modelo inválido para {name}: {model!r}")
        lines.append(f"model: {model}")
    body = prompt.replace("${CLAUDE_PLUGIN_ROOT}", str(package_root))
    return "\n".join(lines + ["---", "", body])


def build_package(src_root, dest, models=None):
    """Atomically build an owned OMP plugin package at *dest*.

    ``models`` maps canonical agent names (roles) to verified concrete
    ``provider/model[:thinking]`` selectors. Missing roles intentionally omit
    ``model`` so OMP inherits the parent model.
    """
    src = Path(src_root).resolve()
    target = Path(dest).expanduser().absolute()
    roles = {} if models is None else dict(models)
    unknown = set(roles) - set(AGENT_NAMES)
    if unknown:
        raise ValueError("papéis desconhecidos: " + ", ".join(sorted(unknown)))
    if not (src / "agents").is_dir() or not (src / "skills").is_dir():
        raise ValueError(f"checkout canônico inválido: {src}")
    if target.is_symlink():
        raise FileExistsError(f"destino é symlink; recusando substituir: {target}")
    if target.exists():
        marker = target / OWNER_MARKER
        if not target.is_dir() or not marker.is_file():
            raise FileExistsError(f"destino existente não pertence a dev-workflows: {target}")
        if marker.read_text(encoding="utf-8") != _owner_value(src) + f"sha256={_content_digest(target)}\n":
            raise FileExistsError(f"pacote existente tem alterações manuais ou origem diferente: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.stage-", dir=target.parent))
    backup = None
    try:
        skills_src = src / "skills"
        skills_dest = stage / "skills"
        shutil.copytree(skills_src, skills_dest, symlinks=False,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        skill_count = sum(1 for path in skills_dest.glob("*/SKILL.md") if path.is_file())
        for path in skills_dest.rglob("*"):
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeError:
                continue
            if "${CLAUDE_PLUGIN_ROOT}" in content:
                path.write_text(content.replace("${CLAUDE_PLUGIN_ROOT}", str(target)), encoding="utf-8")
        if skill_count != 21:
            raise ValueError(f"esperadas 21 skills canônicas; encontradas {skill_count}")

        agents_dest = stage / "agents"
        agents_dest.mkdir()
        for name in AGENT_NAMES:
            if not (src / "agents" / f"{name}.md").is_file():
                raise ValueError(f"agente canônico ausente: {name}")
            (agents_dest / f"{name}.md").write_text(_agent(src, name, roles, target), encoding="utf-8")

        # The quality-gate executable is a package asset; Claude hooks are deliberately
        # excluded. The loop/controller remains responsible for enforcing its verdict.
        gate = src / "scripts" / "quality-gate"
        if gate.is_file():
            (stage / "scripts").mkdir()
            shutil.copy2(gate, stage / "scripts" / "quality-gate")
        manifest = {
            "name": "dev-workflows",
            "version": "1.0.0",
            "description": "Skills e agentes nativos para oh-my-pi; gate imposto pelo controlador externo.",
            "omp": {"extensions": []},
        }
        (stage / "package.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (stage / OWNER_MARKER).write_text(_owner_value(src) + f"sha256={_content_digest(stage)}\n", encoding="utf-8")

        if target.exists():
            backup = Path(tempfile.mkdtemp(prefix=f".{target.name}.backup-", dir=target.parent))
            backup.rmdir()
            os.replace(target, backup)
        try:
            os.replace(stage, target)
        except BaseException:
            if backup is not None:
                os.replace(backup, target)
                backup = None
            raise
        if backup is not None:
            shutil.rmtree(backup)
            backup = None
        return target
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if backup is not None and backup.exists():
            if not target.exists():
                os.replace(backup, target)
            else:
                shutil.rmtree(backup)
