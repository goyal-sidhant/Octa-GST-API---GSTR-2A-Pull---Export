@echo off
REM GSTR-2A Puller - Windows Batch File
REM Double-click this file to run the GSTR-2A puller

echo ========================================================
echo           GSTR-2A BULK PULLER FOR OCTA GST
echo ========================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Check if required packages are installed
echo Checking dependencies...
python -c "import pandas" 2>nul
if %errorlevel% neq 0 (
    echo Installing required packages...
    pip install -r requirements.txt
    echo.
)

REM Check if config.py has been updated
python -c "from config import API_CREDENTIALS; exit(0 if API_CREDENTIALS['API_KEY'] != 'YOUR_API_KEY_HERE' else 1)" 2>nul
if %errorlevel% neq 0 (
    echo ========================================================
    echo WARNING: API credentials not configured!
    echo ========================================================
    echo Please update config.py with your OCTA GST credentials:
    echo   1. Open config.py in any text editor
    echo   2. Replace YOUR_API_KEY_HERE with your actual API key
    echo   3. Replace YOUR_API_SECRET_HERE with your actual API secret
    echo ========================================================
    pause
    exit /b 1
)

REM Run the main script
echo Starting GSTR-2A Puller...
echo --------------------------------------------------------
python main.py

echo.
echo ========================================================
echo Process completed. Check the output folder for results.
echo ========================================================
pause