# Driver Eye Detection System
**YOLOv8 + dlib + PyTorch | Real-time Drowsiness Alert**

## Quick Start
1. Install Python 3.9+ (check "Add to PATH")
2. Double-click `START.bat`
3. Everything installs automatically — app launches

## How it works
- **dlib 68-point landmarks** compute Eye Aspect Ratio (EAR)
- When EAR drops below threshold → eyes detected as CLOSED
- After configurable delay → alarm sounds + red overlay flashes
- **YOLOv8** detects the driver/person bounding box in frame

## Controls (in the GUI)
| Control | Purpose |
|---------|---------|
| EAR Threshold slider | Higher = more sensitive (triggers easier) |
| Alert Delay slider | Seconds of closed eyes before alarm |

## Folder Structure
```
DriverEyeDetection/
├── START.bat              ← double-click to run
├── main.py
├── requirements.txt
├── config/settings.py
├── models/                ← auto-downloaded models
├── assets/sounds/
├── logs/
└── app/
    ├── gui.py
    ├── camera.py
    ├── detection/
    │   ├── eye_detector.py   (dlib EAR)
    │   └── yolo_detector.py  (YOLOv8)
    ├── alerts/alarm.py
    └── utils/
```

## Requirements
- Windows 10/11
- Python 3.9, 3.10, or 3.11
- Webcam