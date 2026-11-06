# BackToWin MCP

Give your AI agent a safe Windows reinstall tool. BackToWin ships as an MCP server
(stdio) with 8 read/plan/license tools — the reinstall itself is performed by the
BackToWin desktop app, never by the agent.

- Official site: https://backtowin.net
- Install guide: see [INSTALL.md](INSTALL.md) in this repo, or the zip from
  [Releases](https://github.com/weib321/backtowin-mcp/releases/latest)
- Free trial: 1 reinstall (in-app activation). Paid: $6.9 for 1, $9.9 for 3 —
  full refund by email if it does not work.

## Quick start (2 minutes)

1. Python 3.10+ (`python --version`; Windows note: the command is `python`, there is no `python3`)
2. `python -m pip install "mcp>=1.30,<2"`
3. Unzip the release package somewhere permanent
4. Add the config block from INSTALL.md to your MCP client (Claude Desktop / Cursor / Doubao)

## Repository layout

```
backtowin-mcp/
├── server.py            MCP stdio server (8 tools)
├── oneboot_kernel/      shared kernel (config, planner, image source, cloud client)
├── runtime/             bundled portable Python runtime (Windows offline install)
├── requirements.txt     mcp>=1.30,<2
├── INSTALL.md           step-by-step install
├── selfcheck.bat        Windows self-check
└── start-server.bat     Windows launcher
```

The cloud endpoint used by default is `https://backtowin.net` — licensing, trial codes
and stats. Telemetry is limited to license/exchange/followup calls; nothing else leaves
the machine.

## License

MIT — see [LICENSE](LICENSE).
