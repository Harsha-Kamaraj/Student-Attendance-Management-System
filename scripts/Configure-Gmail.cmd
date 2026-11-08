@echo off
setlocal
if exist "%~dp0..\.venv\Scripts\python.exe" (
  "%~dp0..\.venv\Scripts\python.exe" "%~dp0configure_gmail.py"
) else (
  python "%~dp0configure_gmail.py"
)
pause
