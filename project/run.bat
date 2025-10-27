@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Financial Data Crawler - Run Menu
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

echo [OK] cs5481 environment active
echo.

:menu
echo ========================================
echo Select Operation:
echo ========================================
echo 1. Run configuration check
echo 2. Run crawler once (single run)
echo 3. Run crawler in loop mode (continuous, press Ctrl+C to stop)
echo 4. View Redis data
echo 5. Export data to files (for data analysis team)
echo 6. Run tests
echo 7. Exit
echo ========================================
echo.

set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto :check_config
if "%choice%"=="2" goto :run_crawler
if "%choice%"=="3" goto :run_crawler_loop
if "%choice%"=="4" goto :view_data
if "%choice%"=="5" goto :export_data
if "%choice%"=="6" goto :run_tests
if "%choice%"=="7" goto :exit
echo [ERROR] Invalid choice
echo.
goto :menu

:check_config
echo.
echo [INFO] Running configuration validation...
python validate_config.py
echo.
pause
goto :menu

:run_crawler
echo.
echo [INFO] Running crawler control center (single run)...
python control_center.py
echo.
pause
goto :menu

:run_crawler_loop
echo.
echo ========================================
echo [INFO] Starting crawler in LOOP MODE
echo ========================================
echo.
echo This will run the crawler continuously.
echo Default interval: 1 hour between runs
echo.
echo ========================================
echo HOW TO STOP:
echo ========================================
echo 1. Press Ctrl+C (recommended)
echo 2. Then press 'Y' to confirm termination
echo 3. Or close the window directly
echo ========================================
echo.
pause
echo.
echo [INFO] Starting loop...
python control_center.py --loop
echo.
echo [INFO] Loop stopped
pause
goto :menu

:view_data
echo.
echo [INFO] Viewing Redis data...
python view_redis_data.py
echo.
pause
goto :menu

:export_data
echo.
echo [INFO] Exporting Redis data to files...
python export_redis_data.py
echo.
pause
goto :menu

:run_tests
echo.
echo [INFO] Running tests...
pytest tests/ -v
echo.
pause
goto :menu

:exit
echo.
echo Goodbye!
exit /b 0
