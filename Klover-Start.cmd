@echo off
chcp 65001 >nul
setlocal
set "PYTHONUTF8=1"
set "KLOVER_ROOT=%~dp0"
if not exist "%KLOVER_ROOT%apps\server\.venv\Scripts\python.exe" (
  echo 먼저 docs/dev/setup.md 맨 위 '쉬운 설치' 1단계부터 따라 하세요.
  pause
  exit /b 1
)
"%KLOVER_ROOT%apps\server\.venv\Scripts\python.exe" "%KLOVER_ROOT%scripts\launcher\run.py" %*
set "KLOVER_RESULT=%ERRORLEVEL%"
pause
exit /b %KLOVER_RESULT%
