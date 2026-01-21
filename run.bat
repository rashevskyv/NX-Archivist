@echo off
setlocal

echo [NX-Archivist] Checking for .env file...
if not exist .env (
    echo [ERROR] .env file not found! 
    echo Please copy .env.example to .env and fill in your credentials.
    pause
    exit /b
)

echo [NX-Archivist] Update from github...
git pull

if not exist venv (
    echo [NX-Archivist] Making venv...
    python -m venv venv
)

echo [NX-Archivist] Activation venv and installing requirements...
call venv\Scripts\activate
pip install -r requirements.txt

echo [NX-Archivist] Bot launching...
python nx_archivist/main.py

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Bot crashed with exit code %ERRORLEVEL%.
    echo Check bot.log for details.
)

pause
