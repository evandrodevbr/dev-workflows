#!/usr/bin/env python3
"""Install dev-workflows into Claude Code, OpenCode, OMP or Hermes Agent.

  python3 scripts/install.py claude      # plugin via local marketplace (skills, agents, hooks)
  python3 scripts/install.py opencode    # skills + agents + plugin under ~/.config/opencode
  python3 scripts/install.py omp         # native skills + agents under ~/.omp/plugins/dev-workflows
  python3 scripts/install.py hermes      # skills under ~/.hermes/skills (no agents/hooks there)

OpenCode and Hermes do not substitute ${CLAUDE_PLUGIN_ROOT}, so their copies point at this checkout:
keep it where it is, or re-run the install after moving it.
"""
import argparse, importlib.util, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER = ".dev-workflows-install"
TEXT_EXT = {".md", ".txt", ".json", ".toml", ".yaml", ".yml"}


def copy_tree(src, dst, force):
    if os.path.exists(dst) and not os.path.exists(os.path.join(dst, MARKER)) and not force:
        sys.exit(f"{dst} já existe e não foi instalado por este script. Use --force para sobrescrever.")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    for dirpath, _, names in os.walk(dst):
        for n in names:
            if os.path.splitext(n)[1] in TEXT_EXT:
                p = os.path.join(dirpath, n)
                text = open(p, encoding="utf-8", errors="ignore").read()
                if "${CLAUDE_PLUGIN_ROOT}" in text:
                    open(p, "w", encoding="utf-8").write(text.replace("${CLAUDE_PLUGIN_ROOT}", ROOT))
    open(os.path.join(dst, MARKER), "w").write(ROOT + "\n")


def install_skills(target_dir, force):
    os.makedirs(target_dir, exist_ok=True)
    names = sorted(d for d in os.listdir(os.path.join(ROOT, "skills"))
                   if os.path.isfile(os.path.join(ROOT, "skills", d, "SKILL.md")))
    for name in names:
        copy_tree(os.path.join(ROOT, "skills", name), os.path.join(target_dir, name), force)
    print(f"{len(names)} skills em {target_dir}")


def opencode_agent(path):
    """Claude Code agent frontmatter -> OpenCode subagent with explicit permissions."""
    with open(path, encoding="utf-8") as source:
        text = source.read()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        raise ValueError(f"frontmatter inválido em {path}")
    meta = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))
    tools = {t.strip() for t in meta.get("tools", "").split(",")}
    skills = re.findall(r"[\w-]+", meta.get("skills", ""))
    read_only = not bool(tools & {"Edit", "Write"})
    allowed = {
        "read": "Read" in tools,
        "edit": not read_only and bool(tools & {"Edit", "Write"}),
        "bash": not read_only and "Bash" in tools,
        "glob": "Glob" in tools,
        "grep": "Grep" in tools,
        "list": False,
        "task": False,
        "external_directory": False,
        "todowrite": False,
        "webfetch": "WebFetch" in tools,
        "websearch": "WebSearch" in tools,
        "lsp": False,
        "skill": "Skill" in tools,
        "question": False,
        "doom_loop": False,
    }
    body = m.group(2).replace("${CLAUDE_PLUGIN_ROOT}", ROOT)
    if skills:
        body = f"Antes de começar, carregue a(s) skill(s): {', '.join(skills)}.\n\n" + body
    head = ["# dev-workflows", f"description: {meta['description']}", "mode: subagent", "permission:", '  "*": deny']
    head += [f"  {key}: {'allow' if value else 'deny'}" for key, value in allowed.items()]
    return "---\n" + "\n".join(head) + "\n---\n\n" + body


def _omp_builder(path=None):
    path = path or os.path.join(ROOT, "adapters", "omp", "build.py")
    spec = importlib.util.spec_from_file_location("dev_workflows_omp_build", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"não foi possível carregar o adapter OMP: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.build_package


def install_omp(base=None, runner=None, build_package=None):
    """Build and link the OMP package without replacing a foreign installation."""
    omp_root = os.path.realpath(base or os.path.expanduser("~/.omp"))
    dest = os.path.join(omp_root, "plugins", "dev-workflows")
    if os.path.lexists(dest) and (os.path.islink(dest) or not os.path.isdir(dest)):
        sys.exit(f"{dest} existe e não é um pacote OMP deste checkout.")
    build = build_package or _omp_builder()
    try:
        build(ROOT, dest)
    except FileExistsError as exc:
        sys.exit(str(exc))
    run = runner or subprocess.run
    command = ["omp", "plugin", "link", dest]
    try:
        result = run(command, check=False)
    except OSError:
        sys.exit("OMP não encontrado; pacote gerado, mas `omp plugin link` não foi executado.")
    if result.returncode != 0:
        sys.exit(f"`omp plugin link {dest}` falhou com código {result.returncode}.")
    print(f"plugin OMP instalado em {dest}")


def install_opencode(force):
    base = os.path.expanduser("~/.config/opencode")
    install_skills(os.path.join(base, "skills"), force)
    agents_dir = os.path.join(base, "agents")
    os.makedirs(agents_dir, exist_ok=True)
    for f in sorted(os.listdir(os.path.join(ROOT, "agents"))):
        dst = os.path.join(agents_dir, f)
        if os.path.exists(dst) and "dev-workflows" not in open(dst, encoding="utf-8").read() and not force:
            sys.exit(f"{dst} já existe e não é deste pacote. Use --force para sobrescrever.")
        open(dst, "w", encoding="utf-8").write(opencode_agent(os.path.join(ROOT, "agents", f)))
    plugins_dir = os.path.join(base, "plugins")
    os.makedirs(plugins_dir, exist_ok=True)
    plugin = open(os.path.join(ROOT, "adapters", "opencode", "dev-workflows.ts"), encoding="utf-8").read()
    open(os.path.join(plugins_dir, "dev-workflows.ts"), "w", encoding="utf-8").write(plugin.replace("__DW_ROOT__", ROOT))
    print(f"agentes em {agents_dir}, plugin em {plugins_dir}/dev-workflows.ts")


def install_claude():
    for cmd in (["claude", "plugin", "marketplace", "add", ROOT], ["claude", "plugin", "install", "dev-workflows@dev-workflows"]):
        print("$ " + " ".join(cmd))
        if subprocess.run(cmd).returncode != 0:
            sys.exit("falhou; rode o comando acima manualmente para ver o erro")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target", choices=["claude", "opencode", "hermes", "omp"])
    ap.add_argument("--force", action="store_true", help="sobrescreve skills/agentes externos; OMP nunca sobrescreve pacote não pertencente")
    a = ap.parse_args()
    if a.target == "claude":
        install_claude()
    elif a.target == "opencode":
        install_opencode(a.force)
    elif a.target == "omp":
        install_omp()
    else:
        install_skills(os.path.expanduser("~/.hermes/skills"), a.force)
        print("Hermes: agentes e hooks não se aplicam; rode o gate manualmente.")


if __name__ == "__main__":
    main()
