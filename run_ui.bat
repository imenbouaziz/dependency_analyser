@echo off
REM Dependency Analyzer Streamlit UI Launcher

echo ====================================
echo  Dependency Analyzer - Streamlit UI
echo ====================================
echo.

REM Check if streamlit is installed
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo [ERROR] Streamlit is not installed!
    echo.
    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
)

REM Launch Streamlit
echo Starting Streamlit UI...
echo.
echo The app will open in your browser at:
echo http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo.

streamlit run app.py

pause
