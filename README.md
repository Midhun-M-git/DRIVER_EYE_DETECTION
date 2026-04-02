# 🚘 Driver Eye Detection System (Elite Edition)

A high-reliability driver drowsiness monitoring system powered by **MediaPipe Face Mesh (478-Point Architecture)** and **YOLOv8** for face tracking. Optimized for real-time safety in low-light and extreme-movement conditions.

## 🌟 Features
- **478-Point Landmark Tracking**: High-density mesh for surgical precision of eye (`EAR`) and mouth (`MAR`) metrics.
- **Yawn Detection**: Automated yawn-invariant tracking (it knows when a yawn is occurring and when it's just drowsiness).
- **Staged Alerts**: Integrated visual and audio warnings (DROWSY vs. CRITICAL).
- **Responsive Dashboard**: CustomTkinter-based GUI with real-time telemetry sidebar.
- **REST API Support**: Built-in Flask server for remote fleet monitoring.

## 🛠️ Requirements
- Python 3.10 (Highly Recommended)
- OpenCV, MediaPipe, Ultralytics, PyTorch
- CustomTkinter

## 🚀 Quick Start
1. Run `SETUP_ENVIRONMENT.bat` to automatically build the virtual environment and install all dependencies.
2. Run `RUN_APP.bat` to launch the monitoring dashboard.

## ⚙️ Sensitivity Tuning
- **EAR Threshold**: Adjust how "closed" your eyes must be to trigger an alert.
- **MAR Threshold**: Tune yawn sensitivity using the live Mouth Aspect Ratio metric.
- **Delay**: Set the verification time (e.g., 2.0s) for persistent eye closure.

## 🛡️ License
MIT License. Developed for Advanced Road Safety.
