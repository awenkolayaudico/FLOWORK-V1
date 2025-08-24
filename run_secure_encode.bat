@echo off
echo ===========================================
echo == Running Secure Encode Script (.py -> .pyd) ==
echo == Source files will NOT be deleted.      ==
echo ===========================================
echo.

REM Assuming you are running this from a 'poetry shell' activated environment
python scripts/secure_encode.py

echo.
echo ===========================================
echo == Script finished.                      ==
echo ===========================================
pause