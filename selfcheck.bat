@echo off
chcp 65001 >nul
echo [BackToWin MCP self-check]
echo.
"%~dp0runtime\python\python.exe" "%~dp0oneboot_mcp\server.py" --test
echo.
pause
