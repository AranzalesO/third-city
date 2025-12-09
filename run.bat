@echo off
REM Helper script to run the Brand Monitoring Tool with correct Python environment

echo.
echo ================================================================================
echo  Brand Monitoring Tool - Launcher
echo ================================================================================
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Running analysis...
python -m src.main

echo.
echo ================================================================================
echo  Analysis Complete
echo ================================================================================
echo.
pause
