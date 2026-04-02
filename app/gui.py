import customtkinter as ctk
import cv2
import time
import threading
import collections
from PIL import Image
import numpy as np
import sys

from app.camera import CameraStream
from app.detection.eye_detector import EyeDetector
from app.detection.yolo_detector import YOLOFaceDetector
from app.alerts.alarm import AlarmSystem
from app.alerts.phone_alert import PhoneAlert
from app.utils.logger import get_logger
from app.utils.fps_counter import FPSCounter
from app.db.analytics import DriverAnalytics
from app.api.server import start_server, shared_state

from config.settings import (
    CAMERA_INDEX, CAMERA_URL_DEFAULT, FRAME_WIDTH, FRAME_HEIGHT,
    EYE_CLOSED_THRESHOLD_SECONDS, EAR_THRESHOLD, MAR_THRESHOLD, YOLO_MODEL_PATH, YOLO_CONF,
    LOG_FILE, ALERT_SOUND, WINDOW_TITLE, WINDOW_SIZE,
    WHATSAPP_NUMBER, WHATSAPP_COOLDOWN_SECONDS
)


class DriverMonitorApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title(f"{WINDOW_TITLE} - Fleet Edition")
        
        # Appearance configs
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Responsive Window Handling
        self.root.after(0, lambda: self.root.state('zoomed')) # Maximize correctly for Windows
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        
        # Core Services
        self.logger      = get_logger(LOG_FILE)
        self.alarm       = AlarmSystem(ALERT_SOUND)
        self.phone_alert = PhoneAlert(WHATSAPP_NUMBER, WHATSAPP_COOLDOWN_SECONDS)
        self.fps_counter = FPSCounter()
        self.analytics   = DriverAnalytics()
        
        # Boot Fleet API
        try:
            start_server()
            self.logger.info("Fleet API booted successfully on Port 5000.")
        except Exception as e:
            self.logger.error(f"Fleet API failed to bind: {e}")

        # State vars
        self._running           = False
        self._session_start     = None
        self._total_alerts      = 0
        self._total_yawns       = 0
        self._alert_active      = False
        self._yawn_active       = False
        self._distract_active   = False
        self._closed_since      = None
        self._yawn_since        = None
        self._distracted_since  = None
        
        # C2 state
        self._blink_timestamps  = collections.deque()
        self._was_closed        = False

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ──────────────────────────── UI BUILD ──────────────────────────────

    def _build_ui(self):
        # Header Section
        self.header_frame = ctk.CTkFrame(self.root, fg_color="#10141a", corner_radius=0)
        self.header_frame.pack(side="top", fill="x")

        title_label = ctk.CTkLabel(
            self.header_frame, 
            text="🚘 DRIVER EYE DETECTION & FLEET ANALYTICS", 
            font=ctk.CTkFont(size=22, weight="bold", family="Helvetica"), 
            text_color="#00ffb7"
        )
        title_label.pack(side="left", padx=30, pady=20)
        
        server_badge = ctk.CTkLabel(self.header_frame, text="🟢 API: PORT 5000", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00ff00")
        server_badge.pack(side="left", padx=20)
        
        exit_btn = ctk.CTkButton(
            self.header_frame, text="✖ EXIT FULLSCREEN", 
            hover_color="#b30000", fg_color="#990000", text_color="white", width=140,
            command=lambda: self.root.attributes("-fullscreen", False)
        )
        exit_btn.pack(side="right", padx=30, pady=20)

        # Main Layout Container
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ── LEFT: DUAL VIDEO FEEDS ──
        self.videos_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.videos_container.pack(side="left", fill="both", expand=True, padx=(0, 15))

        # Feed 1: Original
        self.frame_orig_wrapper = ctk.CTkFrame(self.videos_container, fg_color="#171b24", corner_radius=15)
        self.frame_orig_wrapper.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(self.frame_orig_wrapper, text="LIVE RAW FEED", text_color="#aaaaaa", font=ctk.CTkFont(weight="bold", size=15)).pack(pady=(15, 5))
        self.video_label_orig = ctk.CTkLabel(self.frame_orig_wrapper, text="WAITING FOR SIGNAL...", font=ctk.CTkFont(size=14, slant="italic"))
        self.video_label_orig.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Feed 2: Annotated
        self.frame_ann_wrapper = ctk.CTkFrame(self.videos_container, fg_color="#171b24", corner_radius=15)
        self.frame_ann_wrapper.pack(side="left", fill="both", expand=True, padx=(10, 0))
        
        ctk.CTkLabel(self.frame_ann_wrapper, text="AI ANALYSIS ZONE (YOLOv8 + Dlib 3D)", text_color="#aaaaaa", font=ctk.CTkFont(weight="bold", size=15)).pack(pady=(15, 5))
        self.video_label_ann = ctk.CTkLabel(self.frame_ann_wrapper, text="INITIALIZING AI MODELS...", font=ctk.CTkFont(size=14, slant="italic"))
        self.video_label_ann.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # ── RIGHT: CONTROLS & SETTINGS (SCROLLABLE) ──
        self.right_frame = ctk.CTkScrollableFrame(self.main_container, width=380, corner_radius=15, fg_color="#11151c", scrollbar_button_color="#00ffb7", scrollbar_button_hover_color="#00cc88")
        self.right_frame.pack(side="right", fill="y")

        self.status_bar = ctk.CTkLabel(
            self.right_frame, text="● SYSTEM STOPPED",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#6c757d", fg_color="#0a0c10", corner_radius=10, height=45
        )
        self.status_bar.pack(fill="x", padx=25, pady=(25, 20))

        # Camera Source selection
        ctk.CTkLabel(self.right_frame, text="CAMERA SOURCE", font=ctk.CTkFont(size=13, weight="bold"), text_color="#888888").pack(anchor="w", padx=25)
        self.camera_mode = ctk.StringVar(value="webcam")
        self.cam_radio_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.cam_radio_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        self.radio_webcam = ctk.CTkRadioButton(self.cam_radio_frame, text="Webcam", variable=self.camera_mode, value="webcam", command=self._toggle_cam_entry)
        self.radio_webcam.pack(side="left", padx=(5, 15))
        
        self.radio_ipcam = ctk.CTkRadioButton(self.cam_radio_frame, text="IP Camera URL", variable=self.camera_mode, value="ipcam", command=self._toggle_cam_entry)
        self.radio_ipcam.pack(side="left")
        
        self.ipcam_entry = ctk.CTkEntry(self.right_frame, placeholder_text="http://192.168.x.x:8080/video", height=35)
        self.ipcam_entry.insert(0, CAMERA_URL_DEFAULT)

        ctk.CTkFrame(self.right_frame, height=2, fg_color="#202633").pack(fill="x", padx=25, pady=20)

        # AI Sensitivities
        ctk.CTkLabel(self.right_frame, text="AI SENSITIVITY CALIBRATION", font=ctk.CTkFont(size=13, weight="bold"), text_color="#888888").pack(anchor="w", padx=25)

        # EAR Slider
        ear_lbl_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        ear_lbl_frame.pack(fill="x", padx=25, pady=(15, 0))
        ctk.CTkLabel(ear_lbl_frame, text="Minimum Eye Area (EAR)", font=ctk.CTkFont(size=12)).pack(side="left")
        self.ear_val_label = ctk.CTkLabel(ear_lbl_frame, text=f"{EAR_THRESHOLD:.2f}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00ffb7")
        self.ear_val_label.pack(side="right")
        self.ear_slider = ctk.CTkSlider(self.right_frame, from_=0.10, to=0.40, number_of_steps=30, button_color="#00b386", button_hover_color="#00e6ac")
        self.ear_slider.set(EAR_THRESHOLD)
        self.ear_slider.pack(fill="x", padx=25, pady=(5, 10))
        self.ear_slider.configure(command=lambda v: self.ear_val_label.configure(text=f"{v:.2f}"))

        # Delay Slider
        del_lbl_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        del_lbl_frame.pack(fill="x", padx=25, pady=(10, 0))
        ctk.CTkLabel(del_lbl_frame, text="Max Delay (Close Eye/Distracted)", font=ctk.CTkFont(size=12)).pack(side="left")
        self.delay_val_label = ctk.CTkLabel(del_lbl_frame, text=f"{EYE_CLOSED_THRESHOLD_SECONDS:.1f}s", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00ffb7")
        self.delay_val_label.pack(side="right")
        self.delay_slider = ctk.CTkSlider(self.right_frame, from_=0.5, to=5.0, number_of_steps=45, button_color="#00b386", button_hover_color="#00e6ac")
        self.delay_slider.set(EYE_CLOSED_THRESHOLD_SECONDS)
        self.delay_slider.pack(fill="x", padx=25, pady=(5, 10))
        self.delay_slider.configure(command=lambda v: self.delay_val_label.configure(text=f"{v:.1f}s"))

        # MAR Slider (Mouth/Yawn)
        mar_lbl_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        mar_lbl_frame.pack(fill="x", padx=25, pady=(10, 0))
        ctk.CTkLabel(mar_lbl_frame, text="Yawn Sensitivity (MAR)", font=ctk.CTkFont(size=12)).pack(side="left")
        self.mar_val_label = ctk.CTkLabel(mar_lbl_frame, text=f"{MAR_THRESHOLD:.2f}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00ffb7")
        self.mar_val_label.pack(side="right")
        self.mar_slider = ctk.CTkSlider(self.right_frame, from_=0.05, to=0.50, number_of_steps=45, button_color="#00b386", button_hover_color="#00e6ac")
        self.mar_slider.set(MAR_THRESHOLD)
        self.mar_slider.pack(fill="x", padx=25, pady=(5, 10))
        self.mar_slider.configure(command=lambda v: self.mar_val_label.configure(text=f"{v:.2f}"))

        ctk.CTkFrame(self.right_frame, height=2, fg_color="#202633").pack(fill="x", padx=25, pady=20)

        # Advanced Live Telemetry
        ctk.CTkLabel(self.right_frame, text="ADVANCED FLEET METRICS", font=ctk.CTkFont(size=13, weight="bold"), text_color="#888888").pack(anchor="w", padx=25)

        self._stat_labels = {}
        stats_data = [
            ("fps",      "FPS / Render",      "0"),
            ("ear",      "Current EAR",       "–"),
            ("mar",      "Current MAR",       "–"),
            ("blink",    "Blink Rate / min",  "0"),
            ("yaw",      "Head Yaw (L/R)",    "0.0°"),
            ("pitch",    "Head Pitch (U/D)",  "0.0°"),
            ("alerts",   "Alerts Fired",      "0"),
            ("session",  "System Uptime",     "00:00"),
        ]
        
        telemetry_frame = ctk.CTkFrame(self.right_frame, fg_color="#181e26", corner_radius=10)
        telemetry_frame.pack(fill="x", padx=25, pady=(10, 20))
        
        for key, label, default in stats_data:
            row_frame = ctk.CTkFrame(telemetry_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=15, pady=4)
            ctk.CTkLabel(row_frame, text=label, font=ctk.CTkFont(size=12), text_color="#aaaaaa", width=140, anchor="w").pack(side="left")
            val = ctk.CTkLabel(row_frame, text=default, font=ctk.CTkFont(size=13, weight="bold"), anchor="e")
            val.pack(side="right")
            self._stat_labels[key] = val

        # Start/Stop Action Buttons
        self.btn_start = ctk.CTkButton(
            self.right_frame, text="INITIATE MONITORING", 
            command=self._start, fg_color="#00cc88", hover_color="#00ffaa", text_color="#003322",
            font=ctk.CTkFont(size=15, weight="bold"), height=50, corner_radius=10
        )
        self.btn_start.pack(fill="x", padx=25, pady=5)

        self.btn_stop = ctk.CTkButton(
            self.right_frame, text="HALT SYSTEM", 
            command=self._stop, fg_color="#ff3333", hover_color="#ff6666", text_color="#4d0000",
            font=ctk.CTkFont(size=15, weight="bold"), height=50, corner_radius=10, state="disabled"
        )
        self.btn_stop.pack(fill="x", padx=25, pady=(5, 30))

        # Floating Alert Box (Packed at Bottom)
        self.alert_box = ctk.CTkLabel(
            self.right_frame, text="SYSTEM IDLE & READY",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#0a0c10", corner_radius=10, text_color="#44ff88", height=50
        )
        self.alert_box.pack(fill="x", side="bottom", padx=25, pady=25)


    # ──────────────────────────── ROUTING ───────────────────────────────

    def _toggle_cam_entry(self):
        if self.camera_mode.get() == "ipcam":
            self.ipcam_entry.pack(fill="x", padx=30, pady=(5,0), after=self.cam_radio_frame)
        else:
            self.ipcam_entry.pack_forget()

    def _start(self):
        self._running           = True
        self._session_start     = time.time()
        self._total_alerts      = 0
        self._total_yawns       = 0
        self._alert_active      = False
        self._yawn_active       = False
        self._distract_active   = False
        self._closed_since      = None
        self._yawn_since        = None
        self._distracted_since  = None
        
        self._blink_timestamps.clear()
        self._was_closed        = False

        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_bar.configure(text="● ACTIVE & SCANNING", text_color="#00ffb7", fg_color="#0a1a14")
        self._set_alert_box("SYSTEM ARMED", "#1a1a2e", "#44ff88")

        # Load AI Hybrid Pipeline
        from app.detection.yolo_detector import YOLOFaceDetector
        from config.settings import YOLO_MODEL_PATH, YOLO_CONF
        
        self.eye_detector  = EyeDetector(
            ear_threshold=self.ear_slider.get(),
            mar_threshold=self.mar_slider.get()
        )
        self.yolo_detector = YOLOFaceDetector(YOLO_MODEL_PATH, conf=YOLO_CONF)
        
        # Fresh Db Session
        self.analytics = DriverAnalytics()

        cam_src = CAMERA_INDEX if self.camera_mode.get() == "webcam" else self.ipcam_entry.get()
        self.cam_stream    = CameraStream(cam_src, FRAME_WIDTH, FRAME_HEIGHT)

        self.logger.info("Monitoring session initiated.")
        threading.Thread(target=self._detection_loop, daemon=True).start()
        self._update_session_timer()

    def _stop(self):
        self._running = False
        if hasattr(self, "cam_stream"):
            self.cam_stream.release()
        self.alarm.stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        
        # Calculate Risk and log to SQLite gracefully upon manual termination
        risk_score = self.analytics.end_session()
        self.logger.info(f"Session Terminated. Final Risk Score Logged: {risk_score}")

        self.status_bar.configure(text=f"● SYSTEM STOPPED (Risk: {risk_score})", text_color="#6c757d", fg_color="#0a0c10")
        self._set_alert_box("SYSTEM IDLE & READY", "#0a0c10", "#44ff88")
        
        self.video_label_orig.configure(image=None, text="WAITING FOR SIGNAL...")
        self.video_label_ann.configure(image=None, text="INITIALIZING AI MODELS...")
        self.logger.info("Monitoring session closed cleanly.")

    def _on_close(self):
        self._stop()
        self.root.destroy()
        sys.exit(0)

    # ──────────────────────────── CORE MULTITHREADING ───────────────────

    def _detection_loop(self):
        error_count = 0
        while self._running:
            ret, frame = self.cam_stream.read()
            if not ret or frame is None:
                error_count += 1
                if error_count > 100:  
                    self.logger.error("Camera signal lost completely or network dropped. Terminating loop.")
                    self.root.after(0, self._stop)
                    break
                time.sleep(0.05)
                continue
                
            error_count = 0
            self.fps_counter.tick()

            frame_resized = cv2.resize(frame, (640, 480))
            frame_orig = frame_resized.copy()
            frame_ann  = frame_resized.copy()

            # Sync GUI Sliders to detector
            self.eye_detector.ear_threshold = self.ear_slider.get()
            self.eye_detector.mar_threshold = self.mar_slider.get()
            alert_delay = self.delay_slider.get()
            composite_risk = 0.0

            now = time.time()
            if self._session_start is None:
                continue
            is_calib = (now - self._session_start) < 30.0

            # 1. YOLO face region bounding (with Temporal Face ID matching)
            yolo_boxes = self.yolo_detector.detect_faces(frame_ann)

            # 2. Hybrid AI Analysis Zone
            face_box = yolo_boxes[0] if yolo_boxes else None
            frame_ann, state = self.eye_detector.process_frame(frame_ann, is_calibrating=is_calib, face_box=face_box)
            
            # 3. Draw tracked YOLO bounding
            frame_ann = self.yolo_detector.annotate(frame_ann, yolo_boxes)

            # ── FLASK API STREAM SYNC ──
            shared_state["frame"]   = frame_ann.copy()
            shared_state["metrics"] = state
            shared_state["metrics"]["fps"] = self.fps_counter.fps

            # ── Fleet Telemetry Logic ──
            
            # C2: Blink tracking ring buffer
            if state["eyes_closed"] and not self._was_closed:
                pass # Dropping
            elif not state["eyes_closed"] and self._was_closed:
                self._blink_timestamps.append(now)
            self._was_closed = state.get("eyes_closed", False)

            # Prune blinks older than 60s
            while self._blink_timestamps and (now - self._blink_timestamps[0] > 60.0):
                self._blink_timestamps.popleft()
            blinks_per_min = len(self._blink_timestamps)

            if is_calib:
                remaining = int(30.0 - (now - self._session_start))
                self._set_alert_box(f"CALIBRATING BASELINES... ({remaining}s)", "#333300", "#ffff00")
            else:
                # C3: Composite Weighted Risk Scoring Engine
                ear_severity = 0.0
                distraction_time = 0.0
                blink_multiplier = 0.0
                
                # Yawming checks
                if state["yawning"]:
                    if self._yawn_since is None:
                        self._yawn_since = now
                    elif (now - self._yawn_since) > 0.8 and not self._yawn_active:
                        self._yawn_active = True
                        self.analytics.log_event("yawn", duration_sec=(now-self._yawn_since))
                        self._total_yawns += 1
                        self.logger.warning("Driver Yawn Detected (Fatigue Indicator)")
                    # Always show yawn in UI
                    if not self._alert_active:
                        self._set_alert_box("YAWN DETECTED - FATIGUE!", "#4a3000", "#ffcc00")
                else:
                    self._yawn_since = None
                    self._yawn_active = False

                # Distraction checks
                if state["distracted"]:
                    if self._distracted_since is None:
                        self._distracted_since = now
                    distraction_time = now - self._distracted_since
                else:
                    if self._distracted_since is not None and (now - self._distracted_since) > 1.2:
                         self.analytics.log_event("distraction", duration_sec=(now - self._distracted_since))
                    self._distracted_since = None
                    self._distract_active = False

                if distraction_time > (alert_delay * 1.5) and not self._distract_active:
                    self._distract_active = True
                    self.logger.warning("DISTRACTED DRIVER: Head turned from road.")
                    self.phone_alert.send_alert("WARNING: Distracted Driver Detected! Head turned away from road.")
                
                # Show distraction in UI only after 0.8s debounce (avoid flicker from brief glances)
                if distraction_time > 0.8 and not self._alert_active:
                    self._set_alert_box("DISTRACTED! LOOK AT ROAD!", "#3a0050", "#cc88ff")

                # Drowsiness / Eyes Closed
                if state["eyes_closed"]:
                    if self._closed_since is None:
                        self._closed_since = now
                    ear_severity = now - self._closed_since
                else:
                    self._closed_since = None
                    
                # Blink drop penalty (less than 6 blinks/min is microsleepy)
                if blinks_per_min < 6 and (now - self._session_start) > 60:
                    blink_multiplier = 0.2
                    
                # Normalized composite equation
                # ear_score peaks at 1.0 when eyes are closed for exactly `alert_delay` seconds
                ear_score = ear_severity / (alert_delay + 0.1)
                dist_score = distraction_time / ((alert_delay * 1.5) + 0.1)
                
                # RE-WEIGHTED: Distraction (0.8) and Ear (1.0) so either can breach 0.7
                composite_risk = (ear_score * (1.1 + blink_multiplier)) + (dist_score * 0.8)
                
                # ── Alert TRIGGER ──
                if composite_risk >= 0.7 and not self._alert_active:
                    self._alert_active = True
                    self._total_alerts += 1
                    self.analytics.log_event("drowsy", duration_sec=ear_severity)
                    self.alarm.trigger()
                    self.logger.warning(f"CRITICAL ALERT! Composite risk {composite_risk:.2f}")
                    self._set_alert_box("CRITICAL ALERT!", "#990000", "white")
                    self.phone_alert.send_alert(f"URGENT: Driver Alert! Composite risk breached {composite_risk:.2f}")

                # ── Alert CLEAR: reset immediately when eyes open ──
                elif self._alert_active and not state["eyes_closed"] and ear_severity == 0.0:
                    self.alarm.stop()
                    self._alert_active = False
                    self._closed_since = None
                    self._set_alert_box("SYSTEM ACTIVE", "#0f331f", "#00ffb7")

                # ── Intermediate Warnings (highest-severity state wins) ──
                elif not self._alert_active and not state["distracted"]:
                    if ear_severity > 0.5 and state["eyes_closed"]:
                        self._set_alert_box(f"DROWSY - EYES DROOPING! ({ear_severity:.1f}s)", "#6b2600", "#ff8844")
                    elif composite_risk > 0.4:
                        self._set_alert_box(f"DROWSY WARNING  risk:{composite_risk:.0%}", "#3a2600", "#ffcc00")
                    elif state.get("yawning"):
                        self._set_alert_box("YAWN DETECTED - FATIGUE!", "#4a3000", "#ffcc00")
                    else:
                        self._set_alert_box("EYES OPEN OK", "#0f331f", "#00ffb7")

            # ── Video Overlay Layer (highest priority = alert > distracted > yawn > ok) ──
            if self._alert_active:
                overlay = frame_ann.copy()
                cv2.rectangle(overlay, (0,0), (frame_ann.shape[1], frame_ann.shape[0]), (0,0,180), -1)
                cv2.addWeighted(overlay, 0.35, frame_ann, 0.65, 0, frame_ann)
                cv2.putText(frame_ann, "WAKE UP DRIVER!",
                            (int(frame_ann.shape[1]/2) - 200, int(frame_ann.shape[0]/2)),
                            cv2.FONT_HERSHEY_DUPLEX, 1.5, (0,0,255), 4)
            elif state.get("distracted", False) and distraction_time > 0.8:
                overlay = frame_ann.copy()
                cv2.rectangle(overlay, (0,0), (frame_ann.shape[1], frame_ann.shape[0]), (100,0,150), -1)
                cv2.addWeighted(overlay, 0.25, frame_ann, 0.75, 0, frame_ann)
                cv2.putText(frame_ann, "LOOK AHEAD!",
                            (int(frame_ann.shape[1]/2) - 140, int(frame_ann.shape[0]/2)),
                            cv2.FONT_HERSHEY_DUPLEX, 1.5, (200,100,255), 3)
            elif state.get("yawning", False):
                overlay = frame_ann.copy()
                cv2.rectangle(overlay, (0,0), (frame_ann.shape[1], frame_ann.shape[0]), (0,100,150), -1)
                cv2.addWeighted(overlay, 0.2, frame_ann, 0.8, 0, frame_ann)
                cv2.putText(frame_ann, "YAWN - TAKE A BREAK!",
                            (int(frame_ann.shape[1]/2) - 220, int(frame_ann.shape[0]/2)),
                            cv2.FONT_HERSHEY_DUPLEX, 1.1, (0,220,255), 3)
            elif self._session_start is not None and (now - self._session_start) > 30.0 and not state["distracted"]:
                self._set_alert_box("EYES OPEN OK", "#0f331f", "#00ffb7")


            # Broadcast advanced vectors down to UI thread
            ui_state = {**state, "blink": blinks_per_min}
            self.root.after(0, self._update_stats, ui_state)

            try:
                rgb_orig = cv2.cvtColor(frame_orig, cv2.COLOR_BGR2RGB)
                rgb_ann  = cv2.cvtColor(frame_ann, cv2.COLOR_BGR2RGB)
                sw, sh = 720, 540
                img_o = Image.fromarray(rgb_orig).resize((sw, sh))
                img_a = Image.fromarray(rgb_ann).resize((sw, sh))
                photo_o = ctk.CTkImage(light_image=img_o, dark_image=img_o, size=(sw, sh))
                photo_a = ctk.CTkImage(light_image=img_a, dark_image=img_a, size=(sw, sh))
                self.root.after(0, self._apply_images, photo_o, photo_a)
            except Exception as e:
                self.logger.error(f"Image Render Buffer error: {e}")


    def _apply_images(self, photo_o, photo_a):
        self.video_label_orig.configure(text="", image=photo_o)
        self.video_label_orig.image = photo_o
        
        self.video_label_ann.configure(text="", image=photo_a)
        self.video_label_ann.image = photo_a


    def _update_stats(self, state):
        self._stat_labels["fps"].configure(text=f"{self.fps_counter.fps:.1f}")
        self._stat_labels["ear"].configure(text=f"{state['ear']:.3f}" if state["face_found"] else "X")
        self._stat_labels["mar"].configure(text=f"{state['mar']:.3f}" if state["face_found"] else "X")
        
        # Calculate blink rate from deque
        now = time.time()
        while self._blink_timestamps and (now - self._blink_timestamps[0] > 60.0):
            self._blink_timestamps.popleft()
        
        self._stat_labels["blink"].configure(text=str(len(self._blink_timestamps)))
        self._stat_labels["yaw"].configure(text=f"{state['yaw']:.1f}°")
        self._stat_labels["pitch"].configure(text=f"{state['pitch']:.1f}°")
        self._stat_labels["alerts"].configure(text=str(self._total_alerts))

    def _update_session_timer(self):
        if self._running and self._session_start:
            elapsed = int(time.time() - self._session_start)
            m, s    = divmod(elapsed, 60)
            self._stat_labels["session"].configure(text=f"{m:02d}:{s:02d}")
            self.root.after(1000, self._update_session_timer)

    def _set_alert_box(self, text, bg, fg):
        self.root.after(0, lambda t=text, b=bg, c=fg: self.alert_box.configure(text=t, fg_color=b, text_color=c))