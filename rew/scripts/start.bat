@echo off
REM Start bot with automatic requirements installation
cd /d "%~dp0"

echo ========================================
echo  Telegram Bot Launcher
echo ========================================

REM Validate configuration first
echo.
echo Validating configuration...
if exist "..\venv\Scripts\python.exe" (
    ..\venv\Scripts\python validate_config.py
) else (
    python validate_config.py
)
if errorlevel 1 (
    echo.
    echo ERROR: Configuration validation failed!
    echo Please fix the configuration in scripts/settings.json
    pause
    exit /b 1
)

REM Check if venv exists in rew
if not exist "..\venv\Scripts\python.exe" (
    echo.
    echo Creating virtual environment...
    python -m venv ..\venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo.
echo Installing/Updating requirements...
..\venv\Scripts\python -m pip install --upgrade pip
..\venv\Scripts\python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install requirements
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo.
echo ========================================
echo Starting bot...
echo ========================================
echo.

..\venv\Scripts\python main3.py

pause
