@echo off
REM AI Cryptocurrency Auto-Trading System - Web UI Launcher
REM This script launches the Streamlit web dashboard

echo Starting AI Cryptocurrency Auto-Trading System Web UI...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

REM Check if web_ui.py exists
if not exist "web_ui.py" (
    echo Error: web_ui.py not found in current directory
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

REM Launch Streamlit web UI
echo Opening web UI at http://localhost:8501
echo Press Ctrl+C to stop the server
echo.
streamlit run web_ui.py

pause
