@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Docker Redis Startup Script
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
python --version
echo ========================================
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running or not installed
    echo Please start Docker Desktop first
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Check if Redis container exists
docker ps -a --filter "name=redis-server" --format "{{.Names}}" | findstr /C:"redis-server" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Redis container exists
    
    REM Check if container is running
    docker ps --filter "name=redis-server" --format "{{.Names}}" | findstr /C:"redis-server" >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Redis container is running
        goto :test_connection
    ) else (
        echo [INFO] Starting Redis container...
        docker start redis-server
        if errorlevel 1 (
            echo [ERROR] Failed to start container
            pause
            exit /b 1
        )
        echo [OK] Redis container started
        timeout /t 2 >nul
        goto :test_connection
    )
)

echo [INFO] Creating new Redis container...
echo.

REM Create data directory
if not exist "redis_data" (
    echo [INFO] Creating redis_data directory...
    mkdir redis_data
)

REM Start Redis container
echo [INFO] Starting Redis container with persistence...
docker run -d ^
  --name redis-server ^
  -p 6379:6379 ^
  -v "%cd%\redis_data:/data" ^
  --restart unless-stopped ^
  redis:latest redis-server --appendonly yes --maxmemory 1gb

if errorlevel 1 (
    echo [ERROR] Failed to start Redis container
    pause
    exit /b 1
)

echo [OK] Redis container created successfully
timeout /t 2 >nul

:test_connection
echo.
echo [INFO] Testing Redis connection...
docker exec redis-server redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Redis connection failed
    pause
    exit /b 1
)

echo [OK] Redis connection successful!
echo.

REM Display Redis info
echo ========================================
echo Redis Container Information
echo ========================================
docker exec redis-server redis-cli INFO server | findstr "redis_version"
docker exec redis-server redis-cli INFO memory | findstr "used_memory_human"
docker exec redis-server redis-cli DBSIZE
echo.

echo ========================================
echo Startup Complete!
echo ========================================
echo.
echo Redis is running at: localhost:6379
echo Data directory: %cd%\redis_data
echo.
echo Common commands:
echo   View logs: docker logs redis-server
echo   Stop container: docker stop redis-server
echo   Restart container: docker restart redis-server
echo   Enter container: docker exec -it redis-server redis-cli
echo.

REM Prompt for configuration validation
set /p choice="Run configuration validation? (y/n): "
if /i "%choice%"=="y" (
    echo.
    echo [INFO] Checking Python dependencies...
    python -c "import redis" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Redis Python library not installed
        echo.
        set /p install="Install dependencies? (y/n): "
        if /i "!install!"=="y" (
            echo [INFO] Installing dependencies...
            pip install -r requirements.txt
            if errorlevel 1 (
                echo [ERROR] Failed to install dependencies
                pause
                exit /b 1
            )
            echo [OK] Dependencies installed successfully
        ) else (
            echo [INFO] Skipping configuration validation
            pause
            exit /b 0
        )
    )
    echo.
    echo [INFO] Running configuration validation...
    python validate_config.py
)

echo.
pause
