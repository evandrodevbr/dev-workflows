#!/usr/bin/env python3
"""Install dev-workflows into Claude Code, opencode or Hermes Agent.

  python3 scripts/install.py claude      # plugin via local marketplace (skills, agents, hooks)
  python3 scripts/install.py opencode    # skills + agents + plugin under ~/.config/opencode
  python3 scripts/install.py hermes      # skills under ~/.hermes/skills (no agents/hooks there)

opencode and Hermes do not substitute ${CLAUDE_PLUGIN_ROOT}, so the copies point at this checkout:
keep it where it is, or re-run the install after moving it.
"""
import argparse, os, re, shutil, subprocess, sys

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
    """Claude Code agent frontmatter -> opencode subagent frontmatter."""
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    meta = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))
    tools = {t.strip() for t in meta.get("tools", "").split(",")}
    skills = re.findall(r"[\w-]+", meta.get("skills", ""))
    perm = {"edit": "allow" if tools & {"Edit", "Write"} else "deny",
            "bash": "allow" if "Bash" in tools else "deny",
            "webfetch": "allow" if "WebFetch" in tools else "deny"}
    body = m.group(2).replace("${CLAUDE_PLUGIN_ROOT}", ROOT)
    if skills:
        body = f"Antes de começar, carregue a(s) skill(s): {', '.join(skills)}.\n\n" + body
    head = ["# dev-workflows", f"description: {meta['description']}", "mode: subagent", "permission:"]
    head += [f"  {k}: {v}" for k, v in perm.items()]
    return "---\n" + "\n".join(head) + "\n---\n\n" + body


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
    ap.add_argument("target", choices=["claude", "opencode", "hermes"])
    ap.add_argument("--force", action="store_true", help="sobrescreve pastas com o mesmo nome que não vieram deste script")
    a = ap.parse_args()
    if a.target == "claude":
        install_claude()
    elif a.target == "opencode":
        install_opencode(a.force)
    else:
        install_skills(os.path.expanduser("~/.hermes/skills"), a.force)
        print("Hermes: agentes e hooks não se aplicam; rode o gate manualmente.")


if __name__ == "__main__":
    main()
