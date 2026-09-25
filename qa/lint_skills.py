#!/usr/bin/env python3
"""Structural lint for the plugin: frontmatter, sizes, references, links and leftover machine-specific paths.

Run from anywhere: python3 qa/lint_skills.py   (exit 1 on any error)
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_LINES = 150
MAX_DESC = 1024
FORBIDDEN = [r"~/\.hermes", r"vision_analyze", r"search_files", r"test_quality\.py", r"wf_quality_harness"]
MODELS = {"haiku", "sonnet", "opus", "inherit"}
TOOLS = {"Read", "Edit", "Write", "Bash", "Grep", "Glob", "WebFetch", "WebSearch", "NotebookEdit", "Agent", "Skill"}
errors = []


def err(path, msg):
    errors.append(f"{os.path.relpath(path, ROOT)}: {msg}")


def frontmatter(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        err(path, "sem frontmatter")
        return {}, text
    fm = m.group(1)
    meta = dict(re.findall(r"^([\w-]+):[ \t]*(.*)$", fm, re.M))
    for key in ("uses", "external", "skills"):
        lst = re.search(rf"^\s*{key}:\s*\[(.*?)\]", fm, re.M)
        if lst:
            meta[key] = [s.strip().strip("'\"") for s in lst.group(1).split(",") if s.strip()]
    return meta, text


def vendored():
    rows = open(os.path.join(ROOT, "skills", "NOTICE.md"), encoding="utf-8").read()
    return set(re.findall(r"^\|\s*`([\w-]+)`\s*\|", rows, re.M))


def check_links(path, text):
    text = re.sub(r"```.*?```|`[^`\n]*`", "", text, flags=re.S)
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"(https?:|mailto:|#)", target):
            continue
        p = os.path.normpath(os.path.join(os.path.dirname(path), target.split("#")[0]))
        if not os.path.exists(p):
            err(path, f"link quebrado: {target}")


def main():
    skills_dir = os.path.join(ROOT, "skills")
    names = {d for d in os.listdir(skills_dir) if os.path.isfile(os.path.join(skills_dir, d, "SKILL.md"))}
    third_party = vendored()
    catalog = open(os.path.join(ROOT, "docs", "SKILLS.md"), encoding="utf-8").read()

    for name in sorted(names):
        path = os.path.join(skills_dir, name, "SKILL.md")
        meta, text = frontmatter(path)
        if meta.get("name") != name:
            err(path, f"name '{meta.get('name')}' difere da pasta '{name}'")
        desc = meta.get("description", "")
        if not desc:
            err(path, "description vazia")
        if name in third_party:
            continue
        if len(desc) > MAX_DESC:
            err(path, f"description com {len(desc)} caracteres (máx {MAX_DESC})")
        lines = text.count("\n")
        if lines > MAX_LINES:
            err(path, f"{lines} linhas (máx {MAX_LINES}); mova detalhes para references/")
        for used in meta.get("uses", []):
            if used not in names:
                err(path, f"uses: '{used}' não existe em skills/")
        for ext in meta.get("external", []):
            if f"`{ext}`" not in catalog:
                err(path, f"external: '{ext}' não está em docs/SKILLS.md")
        for dirpath, _, files in os.walk(os.path.join(skills_dir, name)):
            for f in files:
                if f.endswith(".md"):
                    p = os.path.join(dirpath, f)
                    body = open(p, encoding="utf-8").read()
                    check_links(p, body)
                    for pat in FORBIDDEN:
                        if re.search(pat, body):
                            err(p, f"referência específica de máquina: {pat}")

    agents_dir = os.path.join(ROOT, "agents")
    for f in sorted(os.listdir(agents_dir)):
        path = os.path.join(agents_dir, f)
        meta, text = frontmatter(path)
        if meta.get("name") != f[:-3]:
            err(path, f"name '{meta.get('name')}' difere do arquivo")
        if meta.get("model") not in MODELS:
            err(path, f"model '{meta.get('model')}' inválido")
        bad = {t.strip() for t in meta.get("tools", "").split(",")} - TOOLS
        if bad:
            err(path, f"tools desconhecidas: {', '.join(sorted(bad))}")
        for s in meta.get("skills", []):
            if s not in names:
                err(path, f"skills: '{s}' não existe em skills/")
        for pat in FORBIDDEN:
            if re.search(pat, text):
                err(path, f"referência específica de máquina: {pat}")

    hooks = json.load(open(os.path.join(ROOT, "hooks", "hooks.json")))
    for groups in hooks["hooks"].values():
        for g in groups:
            for h in g["hooks"]:
                for script in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w/.-]+)", h["command"]):
                    if not os.path.isfile(os.path.join(ROOT, script)):
                        err(os.path.join(ROOT, "hooks", "hooks.json"), f"script inexistente: {script}")

    for doc in ("README.md", "README.pt-BR.md", "CONTRIBUTING.md", os.path.join("docs", "SKILLS.md")):
        p = os.path.join(ROOT, doc)
        if os.path.exists(p):
            check_links(p, open(p, encoding="utf-8").read())

    for e in errors:
        print("ERRO " + e)
    print(f"{len(names)} skills, {len(os.listdir(agents_dir))} agentes, {len(errors)} erro(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
