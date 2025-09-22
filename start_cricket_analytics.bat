@echo off
echo Starting Cricket Analytics Website...
echo.

REM Check if virtual environment exists (.venv preferred)
if exist ".venv" (
    echo Using existing .venv
    call .venv\Scripts\activate.bat
) else (
    if not exist "venv" (
        echo Creating virtual environment in .venv...
        python -m venv .venv
        call .venv\Scripts\activate.bat
    ) else (
        echo Using existing venv
        call venv\Scripts\activate.bat
    )
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Start the application
echo.
echo Starting Flask application...
echo Open your browser and go to: http://localhost:5000
echo.
python app.py

pause
