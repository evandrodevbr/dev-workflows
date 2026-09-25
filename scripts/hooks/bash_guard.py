#!/usr/bin/env python3
"""PreToolUse guard for shell commands: denies gate bypasses, asks before destructive git/db commands.

Claude Code: reads the hook JSON on stdin and prints a permissionDecision.
opencode:    `bash_guard.py --check "<command>"` prints the reason and exits 2 when the command must not run.
"""
import json, re, sys

DENY = [
    (r"(^|\s)--no-verify(\s|$)", "--no-verify pula os hooks do git. Corrija o que o hook reclamou em vez de pular."),
    (r"\bgit\s+push\b(?=.*\s(--force|-f)(\s|$))(?!.*--force-with-lease)", "push --force reescreve histórico remoto. Use --force-with-lease e só com pedido explícito do usuário."),
    (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)[a-zA-Z]*\s+(/|~|\$HOME|/\*|\.\.)(\s|/?$)", "rm -rf na raiz, no home ou no diretório pai não roda."),
]
ASK = [
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard descarta trabalho não commitado."),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f", "git clean -f apaga arquivos não rastreados."),
    (r"\bgit\s+(checkout|restore)\s+(--\s+)?\.(\s|$)", "descarta todas as mudanças locais."),
    (r"\b(DROP\s+(DATABASE|TABLE|SCHEMA)|TRUNCATE\s+TABLE)\b", "comando destrutivo de banco de dados."),
]


def decide(command):
    for pattern, why in DENY:
        if re.search(pattern, command, re.IGNORECASE):
            return "deny", why
    for pattern, why in ASK:
        if re.search(pattern, command, re.IGNORECASE):
            return "ask", why
    return None, None


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--check":
        decision, why = decide(sys.argv[2])
        if decision:  # opencode has no "ask": both block, the agent must ask the user
            print(f"[dev-workflows] {why} Peça confirmação ao usuário.")
            return 2
        return 0
    event = json.load(sys.stdin)
    decision, why = decide(event.get("tool_input", {}).get("command", ""))
    if decision:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                                 "permissionDecisionReason": f"[dev-workflows] {why}"}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
