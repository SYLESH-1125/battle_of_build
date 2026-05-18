@echo off
REM Project-local 'task' wrapper for Windows
REM Dispatches to serve.py for backend startup
cd /d "%~dp0"
if "%~1"=="serve" (
  py -3 serve.py
  exit /b !errorlevel!
) else (
  echo Usage: task serve
  echo.
  echo Runs the FastAPI backend with hot reload.
  exit /b 1
)
@echo off
REM Shim to emulate `task serve` for uv run task serve
setlocal ENABLEDELAYEDEXPANSION
if /I "%~1"=="serve" (
  shift
  pushd "%~dp0"
  where py >nul 2>&1
  if %ERRORLEVEL%==0 (
    py -3 -m uvicorn main:app --reload %*
  ) else (
    python -m uvicorn main:app --reload %*
  )
  set rc=%ERRORLEVEL%
  popd
  exit /B %rc%
)
echo Unsupported `task` command: %*
exit /B 2
