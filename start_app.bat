@echo off
echo ====================================
echo  Job Application Tracker
echo ====================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if Ollama is running
echo Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Ollama is not running!
    echo.
    echo Please start Ollama first:
    echo   ollama serve
    echo.
    pause
    exit
)

echo ✅ Ollama is running
echo.

REM Start the application
echo Starting Job Application Tracker...
echo.
echo Dashboard will be available at: http://localhost:8000
echo.
echo Press Ctrl+C to stop
echo.

python run.py
