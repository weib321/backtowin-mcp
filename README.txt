BackToWin MCP server - one-folder install
=========================================

WHAT IS THIS
  An MCP (stdio) server with 8 read/plan/license tools for BackToWin, the
  automatic Windows reinstall tool. Your AI client (Claude Desktop, Cursor,
  Doubao, ...) connects to it and its AI agent walks the reinstall flow.
  The bundled runtime\python is a full Python 3.12 - nothing to install.

WINDOWS SETUP (2 MINUTES)
  1. Unzip this folder to a stable path, e.g. C:\BackToWin\
     (result: C:\BackToWin\backtowin-mcp\)
  2. Add this block to your MCP client config and restart the client
     (Claude Desktop: Settings > Developer > Edit Config; Cursor: ~/.cursor/mcp.json):

     {
       "mcpServers": {
         "BackToWin": {
           "command": "C:\\BackToWin\\backtowin-mcp\\runtime\\python\\python.exe",
           "args": ["C:\\BackToWin\\backtowin-mcp\\oneboot_mcp\\server.py"],
           "env": { "ONEBOOT_CLOUD_URL": "https://backtowin.net" }
         }
       }
     }

  3. Ask your agent to call the tool oneboot_assess.
     Working install = text about reinstall risk, track record, pricing.

  Self-check (optional): double-click selfcheck.bat - it should end with ALL PASS.

MACOS / LINUX
  The bundled runtime is Windows-only. With your own python3:
    python3 -m pip install "mcp>=1.30,<2"
  then point your client at python3 and this folder's oneboot_mcp/server.py
  with the same ONEBOOT_CLOUD_URL env.

NOTES
  - Do not move python.exe out of its folder; it needs the files next to it.
  - ONEBOOT_CLOUD_URL points the server at the BackToWin cloud. Keep it unless
    support asks you to change it.
  - First run may trigger a SmartScreen/antivirus prompt; choose Allow.

中文说明
  本文件夹是一个 MCP(stdio) 服务器，带 8 个查询/规划/激活工具，供 AI 客户端
  （Claude Desktop、Cursor、豆包等）连接使用。runtime\python 是免安装的 Python 3.12。
  Windows 三步：
    1) 解压到固定路径，如 C:\BackToWin\（得到 C:\BackToWin\backtowin-mcp\）；
    2) 在客户端 MCP 配置里：command 填 runtime\python\python.exe，
       args 填 oneboot_mcp\server.py，env 加 ONEBOOT_CLOUD_URL=https://backtowin.net，
       重启客户端；
    3) 让 AI 调用 oneboot_assess 验证，能输出重装风险/战绩/价格即为成功。
  可双击 selfcheck.bat 自检，末尾出现 ALL PASS 即安装成功。
  macOS/Linux 用户：包内运行时仅限 Windows，请用系统 python3 执行
  python3 -m pip install "mcp>=1.30,<2" 后指向 oneboot_mcp/server.py。
