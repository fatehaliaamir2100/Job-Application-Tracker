@echo off
echo ====================================
echo  Job Application Tracker - Setup
echo ====================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Check for .env file
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo.
)

REM Check for credentials
if not exist "credentials.json" (
    echo.
    echo ⚠️  Gmail credentials not found!
    echo.
    echo Run this to set up Gmail API:
    echo   python scripts\setup_gmail.py
    echo.
    pause
    exit
)

echo.
echo ✅ Setup complete!
echo.
echo To run the app:
echo   start_app.bat
echo.
pause
