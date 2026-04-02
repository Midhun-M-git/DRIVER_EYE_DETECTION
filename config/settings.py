import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Camera
CAMERA_INDEX = 0
CAMERA_URL_DEFAULT = "http://192.168.29.232:8080/video"
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

# Eye/Mouth detection thresholds
EYE_CLOSED_THRESHOLD_SECONDS = 2.0   # alert after eyes closed this long
DROWSY_THRESHOLD_SECONDS = 1.0        # warning after this
EAR_THRESHOLD = 0.22                  # Lowered slightly for MediaPipe precision
MAR_THRESHOLD = 0.15                  # Initial yawn threshold for inner-lip MAR

# YOLOv8
YOLO_MODEL_PATH = os.path.join(BASE_DIR, "models", "yolov8n-face.pt")
YOLO_CONF = 0.35

# Paths
LOG_FILE = os.path.join(BASE_DIR, "logs", "session.log")
ALERT_SOUND = os.path.join(BASE_DIR, "assets", "sounds", "alert.wav")

# UI
WINDOW_TITLE = "Driver Eye Detection System"
WINDOW_SIZE = "1100x700"

# WhatsApp Alerts
WHATSAPP_NUMBER = "+917907194007"
WHATSAPP_COOLDOWN_SECONDS = 60  # Only send 1 alert per minute