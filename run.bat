@echo off
setlocal enabledelayedexpansion

:: Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not in PATH. Please install Python and try again.
    exit /b 1
)

:: Check if the virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate the virtual environment
call venv\Scripts\activate.bat

:: Install dependencies if needed
if not exist venv\.dependencies_installed (
    echo Installing dependencies...
    pip install -r requirements.txt
    type nul > venv\.dependencies_installed
)

:: Check if .env file exists
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file with your OpenAI API key.
    exit /b 1
)

:: Parse command line arguments
if "%1"=="api" (
    echo Starting API server only...
    python api.py
) else if "%1"=="app" (
    echo Starting Streamlit app only...
    streamlit run app.py
) else if "%1"=="automation" (
    echo Starting automation script only...
    python automation.py
) else (
    call :start_components
)

goto :eof

:start_components
    :: Start API server
    echo Starting API server...
    start /B cmd /C "python api.py > api.log 2>&1"
    
    :: Wait a moment for API to start
    timeout /t 2 /nobreak > nul
    
    :: Start automation script
    echo Starting automation script...
    start /B cmd /C "python automation.py > automation.log 2>&1"
    
    :: Start Streamlit app
    echo Starting Streamlit app...
    start /B cmd /C "streamlit run app.py > streamlit.log 2>&1"
    
    echo All components started!
    echo Logs are being written to api.log, automation.log, and streamlit.log
    echo Press Ctrl+C to stop all components.
    
    :: Pause to keep the console window open
    pause > nul
    
    goto :eof 