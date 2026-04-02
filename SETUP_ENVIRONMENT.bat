@echo off
title Driver Detection - ENVIRONMENT SETUP
color 0B
echo ============================================
echo   SETTING UP PYTHON 3.10 ENVIRONMENT
echo   (MediaPipe 478-Point Architecture)
echo ============================================
echo.

:: Ensure we are in the script's directory
cd /d "%~dp0"

:: Step 0: Find Python 3.10
echo [0/3] Checking for Python 3.10...

:: Check 'py' launcher
where py >nul 2>&1
if %errorlevel% neq 0 goto :check_python

echo [INFO] Python Launcher detected.
py -3.10 --version >nul 2>&1
if %errorlevel% neq 0 goto :check_python

set PYTHON_CMD=py -3.10
goto :found

:check_python
echo [INFO] Checking 'python' command...
python --version >version.tmp 2>&1
if %errorlevel% neq 0 goto :no_python

set /p PY_VER=<version.tmp
del version.tmp
echo Found %PY_VER%

echo %PY_VER% | findstr /C:"3.10" >nul
if %errorlevel% neq 0 goto :wrong_version

set PYTHON_CMD=python
goto :found

:no_python
echo [ERROR] No Python found.
echo Please install Python 3.10 from https://www.python.org/
pause
exit /b 1

:wrong_version
echo [ERROR] Python 3.10 not found. 
echo Only %PY_VER% was detected.
echo Please install Python 3.10 specifically.
pause
exit /b 1

:found
echo [SUCCESS] Using command: %PYTHON_CMD%
echo.

:: Create Venv
if exist "venv310\Scripts\activate.bat" goto :install_deps

echo [1/3] Creating virtual environment (venv310)...
%PYTHON_CMD% -m venv venv310
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create venv. 
    pause
    exit /b 1
)
echo       Done.

:install_deps
echo [2/3] Installing dependencies...
echo.
call venv310\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Activation failed.
    pause
    exit /b 1
)

python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Finalizing MediaPipe components...
pip install mediapipe
if %errorlevel% neq 0 (
    echo [ERROR] MediaPipe installation failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   SETUP COMPLETE!
echo   MediaPipe 478-Point Engine is ARMED.
echo   You can now use RUN_APP.bat to start.
echo ============================================
pause
