# AGENTS.md — BackToWin for AI agents

BackToWin reinstalls Windows 10/11 end-to-end from official Microsoft images — including the Windows 11 → 10 downgrade — and rolls the system back automatically if a run fails. The reinstall itself is performed by the installed BackToWin desktop app, never by the agent. This MCP server exposes 8 tools so an agent can run the whole flow around it.

## Setup (Claude Desktop / Cursor / any MCP client)

`claude_desktop_config.json` (Cursor: `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "BackToWin": {
      "command": "python",
      "args": ["C:\\BackToWin\\backtowin-mcp\\oneboot_mcp\\server.py"],
      "env": { "ONEBOOT_CLOUD_URL": "https://backtowin.net" }
    }
  }
}
```

- Keep `ONEBOOT_CLOUD_URL` at `https://backtowin.net` unless the user explicitly provides another endpoint.
- Restart the client after editing the config. Windows recommended (the bundled runtime in the release zip ships a ready Python environment).

## The 8 tools

| Tool | What it does |
|---|---|
| `oneboot_assess` | Read-only profile: licensing/edition context for the reinstall decision |
| `oneboot_quote` | Pricing and license options (facts only, no pressure) |
| `oneboot_check_machine` | Read-only machine profile: Windows version, firmware (UEFI/BIOS), disk encryption status; Windows 11 machines are eligible for the downgrade path |
| `oneboot_plan` | The install plan, including the backup checklist before anything destructive happens |
| `oneboot_image_info` | Official Microsoft image endpoints and hash-record guidance |
| `oneboot_verify_image` | Verify a downloaded image against official hash records — **refuses to proceed when no hash is on record** |
| `oneboot_activate` | Bind a license code to this machine (see below) |
| `oneboot_report_completion` | Post-install follow-up record |

## Activation

When the user wants a reinstall: the BackToWin app's activation window shows an 8-character hex app_code. Get it from the user or the app window, then call `oneboot_activate`.

- Free trial: 1 reinstall.
- Paid: $6.9 for 1 reinstall, $9.9 for 3 reinstalls.
- If a code does not work: full refund by email.

## Troubleshooting

- Tool calls fail with connection errors → check the machine's internet reachability; the server never bypasses its cloud endpoint.
- `oneboot_verify_image` refuses an image → that is by design (fail-closed); download the image from the endpoint given by `oneboot_image_info` and verify again.
- Everything user-facing (pricing, stats, guides, FAQ) lives at <https://backtowin.net> — the agent flow mirrors those facts.

## Links

- Homepage: <https://backtowin.net>
- Windows app downloads (EN / DE / FR): <https://github.com/weib321/backtowin/releases/latest>
- This MCP server releases: <https://github.com/weib321/backtowin-mcp/releases/latest>
