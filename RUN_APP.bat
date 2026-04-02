@echo off
title Driver Detection - RUNNER
color 0E
echo ============================================
echo   LAUNCHING DRIVER EYE DETECTION SYSTEM
echo   (MediaPipe 478-Point Architecture)
echo ============================================
echo.

:: Ensure we are in the script's directory
cd /d "%~dp0"

:: Check if venv exists
if exist "venv310\Scripts\activate.bat" goto :activate

echo [ERROR] Virtual environment (venv310) not found!
echo Please run SETUP_ENVIRONMENT.bat first to install the MediaPipe engine.
pause
exit /b 1

:activate
echo [1/2] Activating venv310...
call venv310\Scripts\activate.bat
if %errorlevel% neq 0 goto :activate_fail

echo [2/2] Launching application (Python 3.10)...
python main.py
if %errorlevel% neq 0 goto :app_fail

echo.
echo [INFO] Application closed cleanly.
pause
exit /b 0

:activate_fail
echo [ERROR] Activation failed!
pause
exit /b 1

:app_fail
echo.
echo [INFO] Application exited with error code %errorlevel%.
pause
exit /b 1
