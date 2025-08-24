@echo off
rem (MODIFIED) This script now runs the compiled launcher.
rem The launcher handles everything: unzipping python and running the main app.
rem This is the file your end-users will click.

echo Starting Flowork... Please wait.

rem Ensure we are in the script's directory
cd /d "%~dp0"

rem Check if the compiled executable exists
IF EXIST Flowork.exe (
    start "Flowork" Flowork.exe
) ELSE (
    echo [ERROR] Flowork.exe not found!
    echo Please compile launcher.py to Flowork.exe first.
    pause
)