@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "APP_NODE=node.exe"
where.exe node.exe >nul 2>&1
if errorlevel 1 (
  if exist "D:\node.exe" (
    set "APP_NODE=D:\node.exe"
  ) else (
    echo Node.js was not found. Install Node.js 20 or newer, then try again.
    pause
    exit /b 1
  )
)
"%APP_NODE%" "scripts\start.mjs" --open
if errorlevel 1 (
  echo.
  echo The app could not start. Please keep this window open to see the error above.
  pause
  exit /b 1
)
endlocal
