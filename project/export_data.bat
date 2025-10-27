@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Redis Data Export Tool
echo ========================================
echo.

REM Check if in cs5481 environment
if not "%CONDA_DEFAULT_ENV%"=="cs5481" (
    echo [ERROR] Please activate cs5481 environment first:
    echo   conda activate cs5481
    echo.
    pause
    exit /b 1
)

echo [INFO] Exporting Redis data to local files...
echo.

python export_redis_data.py

if errorlevel 1 (
    echo.
    echo [ERROR] Export failed
    pause
    exit /b 1
)

echo.
pause
