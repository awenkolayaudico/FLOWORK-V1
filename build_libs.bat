@echo off
REM ###########################################################
REM # Flowork Libs Builder Script for Windows (Dev)           #
REM ###########################################################

echo.
echo [INFO] Starting Flowork library build process...
echo --------------------------------------------------

REM Step 1: Clean up old artifacts to ensure a fresh start.
echo [STEP 1/5] Cleaning up old artifacts...
if exist libs rmdir /s /q libs
if exist libs.zip del libs.zip
echo   -> Old 'libs' folder and 'libs.zip' deleted.

REM Step 2: Export production dependencies from pyproject.toml.
echo [STEP 2/5] Exporting dependencies from pyproject.toml...
poetry export -f requirements.txt --output requirements.txt --without-hashes --without dev
if %errorlevel% neq 0 (
    echo [ERROR] Failed to export dependencies from Poetry.
    goto end
)
echo   -> 'requirements.txt' created successfully (dev dependencies excluded).

REM Step 3: Install the exported dependencies into the local './libs' folder.
echo [STEP 3/5] Installing dependencies to ./libs folder...
pip install -r requirements.txt -t ./libs
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed. Make sure pip is installed and accessible.
    goto end
)
echo   -> All libraries installed into './libs'.

REM Step 4: Call the Python script to zip the newly created libs folder.
echo [STEP 4/5] Zipping the libs folder...
python scripts/create_zip.py
if %errorlevel% neq 0 (
    echo [ERROR] Zipping process failed. Check the Python script.
    goto end
)

REM Step 5: Clean up the temporary requirements.txt file.
echo [STEP 5/5] Cleaning up temporary files...
del requirements.txt
echo   -> 'requirements.txt' deleted.

echo --------------------------------------------------
echo [SUCCESS] Build complete! libs.zip has been updated.
echo.

:end
pause