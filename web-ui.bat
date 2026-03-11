@echo off
REM AI Cryptocurrency Auto-Trading System - Web UI Launcher
REM This script launches the Streamlit web dashboard

echo Starting AI Cryptocurrency Auto-Trading System Web UI...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher from https://www.python.org/
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

REM Check if streamlit is installed
python -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo Streamlit is not installed. Installing now...
    echo.
    python -m pip install streamlit
    if errorlevel 1 (
        echo.
        echo Failed to install Streamlit automatically.
        echo Please run manually: python -m pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo.
    echo Streamlit installed successfully!
    echo.
)

REM Launch Streamlit web UI
echo Opening web UI at http://localhost:8501
echo Press Ctrl+C to stop the server
echo.
python -m streamlit run web_ui.py

pause
