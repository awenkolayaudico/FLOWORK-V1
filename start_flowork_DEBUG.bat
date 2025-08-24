@echo off
rem (MODIFIED) This batch file now correctly calls the LAUNCHER script, not the main script.
rem This is used for testing the launcher logic within the Poetry environment.

echo Starting Flowork in DEBUG mode via Poetry...

rem Run the launcher script, which will then handle running main.py
poetry run python launcher.py

pause