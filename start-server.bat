@echo off
rem BackToWin MCP server (stdio).
rem MCP clients may use this bat as the command, or point directly at
rem runtime\python\python.exe with arg oneboot_mcp\server.py
"%~dp0runtime\python\python.exe" "%~dp0oneboot_mcp\server.py" %*
