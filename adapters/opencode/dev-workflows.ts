// dev-workflows for opencode: the same guard, formatter and gate scripts the Claude Code hooks run.
// Installed by `python3 scripts/install.py opencode`, which replaces __DW_ROOT__ with the checkout path.
// opencode cannot block the end of a turn, so a missing or failing gate is logged instead of blocking.
const ROOT = "__DW_ROOT__"

const DevWorkflows = async (ctx: any) => {
  const $ = ctx.$ ?? (globalThis as any).Bun?.$
  const directory = ctx.directory ?? ctx.location?.directory ?? process.cwd()
  return {
    "tool.execute.before": async (input: any, output: any) => {
      if (!["bash", "shell"].includes(String(input?.tool ?? "").toLowerCase())) return
      const command = output?.args?.command
      if (typeof command !== "string" || !command) return
      const r = await $`python3 ${ROOT}/scripts/hooks/bash_guard.py --check ${command}`.quiet().nothrow()
      if (r.exitCode === 2) throw new Error(String(r.stdout).trim())
    },
    "tool.execute.after": async (input: any, output: any) => {
      if (!["edit", "write", "patch", "multiedit"].includes(String(input?.tool ?? "").toLowerCase())) return
      const file = input?.args?.filePath ?? output?.args?.filePath
      if (typeof file === "string" && file) {
        await $`python3 ${ROOT}/scripts/hooks/post_edit.py --file ${file}`.quiet().nothrow()
      }
    },
    event: async ({ event }: any) => {
      if (event?.type !== "session.idle") return
      const r = await $`python3 ${ROOT}/scripts/hooks/stop_gate.py --check ${directory}`.quiet().nothrow()
      if (r.exitCode === 2) {
        await ctx.client?.app?.log?.({ body: { service: "dev-workflows", level: "warn", message: String(r.stdout).trim() } })
      }
    },
  }
}

export default { id: "dev-workflows", setup: DevWorkflows }
