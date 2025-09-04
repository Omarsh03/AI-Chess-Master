@echo off
echo Starting Chess Game...

REM Try to activate conda environment first
echo Checking for conda environment...
call conda activate env_3_8_20 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Conda environment not found, checking Python installation...
    python --version 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo Python is not installed or not in PATH
        echo Please install Python and the required packages:
        type requirements.txt
        pause
        exit /b 1
    )
    echo Installing required packages...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install required packages
        pause
        exit /b 1
    )
)

echo Starting server...
start "Chess Server" cmd /k python server.py
echo Waiting for server to initialize...
timeout /t 3 /nobreak > nul
echo Starting client...
start "Chess Client" cmd /k python client.py
echo Game started! Both windows will stay open to show any errors.
echo Press any key to exit this window...
pause
