# Driver Eye Detection System

<div align="center">

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0097A7?style=for-the-badge&logo=google&logoColor=white)](https://developers.google.com/mediapipe)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

A real-time driver drowsiness and fatigue monitoring pipeline powered by MediaPipe Face Mesh (478-Point Architecture) and YOLOv8 for face tracking. Optimized for low-latency detection in low-light and high-movement automotive environments.

---

## Features

- **478-Point Landmark Mesh**: Dense facial landmark geometry for accurate Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR) computation.
- **Yawn Detection**: Automated kinematic distinction between natural mouth movement and prolonged yawns.
- **Staged Audio-Visual Alerts**: Multi-tier alert hierarchy distinguishing between early fatigue and critical micro-sleep states.
- **Telemetry Interface**: CustomTkinter desktop interface featuring real-time eye aspect metrics and status telemetry.
- **REST Fleet Telemetry**: Integrated Flask server designed for remote vehicle fleet monitoring and event logging.

---

## Prerequisites

- Python 3.10 or higher
- OpenCV, MediaPipe, Ultralytics, PyTorch
- CustomTkinter

---

## Quick Start

### Windows
1. Run `SETUP_ENVIRONMENT.bat` to configure the Python virtual environment and install dependencies.
2. Run `RUN_APP.bat` to launch the telemetry dashboard.

### macOS / Linux
```bash
chmod +x run.sh
./run.sh
```

---

## Threshold Calibration

- **EAR Threshold**: Set the baseline eye aspect ratio to adjust closed-eye sensitivity.
- **MAR Threshold**: Calibrate yawn detection threshold based on facial aspect metrics.
- **Consecutive Frame Delay**: Adjust the persistence threshold (e.g., 2.0 seconds) to prevent false positives from natural blinking.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
