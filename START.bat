@echo off
title Driver Eye Detection System - Launcher
color 0A

echo ============================================
echo   DRIVER EYE DETECTION SYSTEM
echo   Powered by YOLOv8 + PyTorch
echo ============================================
echo.

cd /d D:\DriverEyeDetection

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.9+ from https://python.org
    echo        Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo [1/5] Python found.

:: Create virtual environment if not exists
if not exist "venv310\Scripts\activate.bat" (
    echo [2/5] Creating Python 3.10 virtual environment...
    py -3.10 -m venv venv310
    echo       Virtual environment created.
) else (
    echo [2/5] Virtual environment already exists.
)

:: Activate venv
call venv310\Scripts\activate.bat
echo [3/5] Virtual environment activated.

:: Install / upgrade pip silently
python -m pip install --upgrade pip --quiet

:: Install requirements
echo [4/5] Installing requirements (this may take a few minutes on first run)...
pip install -r requirements.txt
pip install mediapipe

:: Download YOLOv8-Face if not present
if not exist "models\yolov8n-face.pt" (
    echo       Downloading YOLOv8n-face model...
    :: Use curl or python to download from HF if needed, but assuming it exists from previous turns
)

echo [5/5] Launching application...
echo.
echo ============================================
echo   Press CTRL+C in this window to stop.
echo ============================================
echo.

python main.py

echo.
echo Application closed.
pause
```

---

### `D:\DriverEyeDetection\requirements.txt`
```
ultralytics>=8.0.0
torch>=2.0.0
torchvision>=0.15.0
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0
pygame>=2.5.0
customtkinter>=5.2.0
scipy>=1.11.0
dlib>=19.24.0
imutils>=0.5.4
playsound>=1.3.0