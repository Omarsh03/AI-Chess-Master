@echo off
setlocal EnableDelayedExpansion
echo ===============================
echo   AI Chess Master - Launcher
echo ===============================

echo Checking for conda environment (env_3_8_20)...
call conda activate env_3_8_20 >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo Conda environment not found, falling back to system Python.
    python --version >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo ERROR: Python is not installed or not in PATH.
        echo Please install Python 3.8+ and the required packages:
        type requirements.txt
        pause
        exit /b 1
    )
    echo Installing/refreshing required packages from requirements.txt...
    pip install -r requirements.txt
    if !ERRORLEVEL! NEQ 0 (
        echo ERROR: Failed to install required packages.
        pause
        exit /b 1
    )
)

echo Starting AI Chess Master...
python unified_app.py
if !ERRORLEVEL! NEQ 0 (
    echo The app closed with an error ^(exit code !ERRORLEVEL!^).
    pause
    exit /b 1
)

endlocal
