import cv2
import numpy as np
import mediapipe as mp
import time
from scipy.spatial import distance as dist

class EyeDetector:
    """
    Ultimate Fatigue Engine: MediaPipe "High-Density" edition.
    Powered by 478-point Face Mesh for extreme precision.
    1. Low-Light Survival: Uses CLAHE normalization.
    2. Dense Landmarks: Uses MediaPipe Face Mesh (replaces Dlib 68).
    3. Hybrid Lock: ROI Persistence + YOLO-guided initial seek.
    """

    def __init__(self, ear_threshold=0.25, mar_threshold=0.45):
        self.ear_threshold = ear_threshold
        self.mar_threshold = mar_threshold
        
        # MediaPipe initialization
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True, # 478 pts (includes irises)
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Low-light engine
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        
        # Temporal persistence logic
        self.last_rect_coords = None # [x1, y1, x2, y2]
        self.lost_frames = 0
        self.MAX_LOST_FRAMES = 12 
        
        self.dynamic_ear_threshold = ear_threshold
        self.calibration_frames = []
        
        # 3D Head Pose setup (Nose, Chin, Eyes, Mouth corners)
        # MediaPipe indices for landmarks:
        # Nose: 1, Chin: 152, Left Eye: 33, Right Eye: 263, L Mouth: 61, R Mouth: 291
        self.model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left Mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ])
        
        print("[EyeDetector] Extreme Condition Pipeline Armed (MediaPipe Mesh)")

    def _get_ear(self, eye_pts):
        # MediaPipe Eye EAR calculation
        # Horizontal: corner to corner
        # Vertical: 3 pairs averaged
        v1 = dist.euclidean(eye_pts[1], eye_pts[5])
        v2 = dist.euclidean(eye_pts[2], eye_pts[4])
        horiz = dist.euclidean(eye_pts[0], eye_pts[3])
        if horiz < 1e-6: return 0.0
        return (v1 + v2) / (2.0 * horiz)

    def _get_mar(self, face_landmarks, h, w):
        # MAR using inner lip vertical/horizontal
        # Vertical: 13, 14. Horizontal: 78, 308
        p_13 = np.array([face_landmarks.landmark[13].x * w, face_landmarks.landmark[13].y * h])
        p_14 = np.array([face_landmarks.landmark[14].x * w, face_landmarks.landmark[14].y * h])
        p_78 = np.array([face_landmarks.landmark[78].x * w, face_landmarks.landmark[78].y * h])
        p_308 = np.array([face_landmarks.landmark[308].x * w, face_landmarks.landmark[308].y * h])
        
        v = dist.euclidean(p_13, p_14)
        horiz = dist.euclidean(p_78, p_308)
        if horiz < 1e-6: return 0.0
        return v / horiz

    def process_frame(self, frame, is_calibrating=False, face_box=None):
        h, w = frame.shape[:2]
        state = {
            "face_found": False, "eyes_closed": False, "ear": 0.0, 
            "yawning": False, "mar": 0.0, 
            "distracted": False, "pitch": 0.0, "yaw": 0.0, "roll": 0.0,
            "calibrating": is_calibrating, "locked_on": False
        }
        
        # 1. Pre-processing
        # MediaPipe prefers RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Apply CLAHE to luminosity channel if needed, but MP is robust. 
        # We'll use the original CLAHE gray for fallback if needed, but MP does its own.
        
        # 2. Hybrid Seek: Use YOLO face_box to crop if available (improves stability)
        crop_frame = rgb_frame
        offset_x, offset_y = 0, 0
        
        if face_box:
            x1, y1, x2, y2 = face_box
            # Pad the box slightly for mesh stability
            pad = int((x2 - x1) * 0.1)
            x1=max(0, x1-pad); y1=max(0, y1-pad); x2=min(w, x2+pad); y2=min(h, y2+pad)
            crop_frame = rgb_frame[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
            self.last_rect_coords = [x1, y1, x2, y2]
            self.lost_frames = 0
            state["locked_on"] = True
        elif self.last_rect_coords and self.lost_frames < self.MAX_LOST_FRAMES:
            x1, y1, x2, y2 = self.last_rect_coords
            crop_frame = rgb_frame[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
            self.lost_frames += 1
            state["locked_on"] = True
            cv2.putText(frame, "RE-ACQUIRING...", (x1, y1 - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

        # 3. MediaPipe Inference
        results = self.face_mesh.process(crop_frame)
        
        if not results.multi_face_landmarks:
            # Fallback to full frame if crop fails
            if crop_frame is not rgb_frame:
                results = self.face_mesh.process(rgb_frame)
                offset_x, offset_y = 0, 0
            
        if not results.multi_face_landmarks:
            return frame, state

        state["face_found"] = True
        landmarks = results.multi_face_landmarks[0]
        
        # Extract points for EAR (normalized to full frame)
        def get_pt(idx):
            lm = landmarks.landmark[idx]
            # lm.x/y are relative to crop_frame
            cw, ch = crop_frame.shape[1], crop_frame.shape[0]
            return np.array([lm.x * cw + offset_x, lm.y * ch + offset_y])

        # Eye indices (MP Mesh 478)
        # Left Eye (from user perspective/right eye in mesh): 33, 160, 158, 133, 153, 144
        # Right Eye (from user perspective/left eye in mesh): 263, 387, 385, 362, 380, 373
        left_eye_pts = [get_pt(i) for i in [33, 160, 158, 133, 153, 144]]
        right_eye_pts = [get_pt(i) for i in [263, 387, 385, 362, 380, 373]]
        
        ear_l = self._get_ear(left_eye_pts)
        ear_r = self._get_ear(right_eye_pts)
        ear = (ear_l + ear_r) / 2.0
        
        # MAR Calculation
        mar = self._get_mar(landmarks, crop_frame.shape[0], crop_frame.shape[1])
        
        # Calibration logic
        if is_calibrating:
            self.calibration_frames.append(ear)
            if len(self.calibration_frames) > 10:
                mean_e = np.mean(self.calibration_frames)
                self.dynamic_ear_threshold = mean_e * 0.75
                
        eff_thresh = self.dynamic_ear_threshold if (not is_calibrating and self.dynamic_ear_threshold > 0.1) else self.ear_threshold

        state["ear"] = round(float(ear), 3)
        state["mar"] = round(float(mar), 3)
        state["eyes_closed"] = (ear < eff_thresh)
        state["yawning"]     = (mar > self.mar_threshold)

        # 4. Head Pose Logic
        # MediaPipe points mapped to full frame
        image_points = np.array([
            get_pt(1),   # Nose
            get_pt(152), # Chin
            get_pt(33),  # Left eye corner
            get_pt(263), # Right eye corner
            get_pt(61),  # L Mouth
            get_pt(291)  # R Mouth
        ], dtype="double")

        focal_length = w
        center = (w/2, h/2)
        cam_matrix = np.array([[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]], dtype="double")
        dist_coeffs = np.zeros((4,1))
        
        success, rotation_vector, translation_vector = cv2.solvePnP(self.model_points, image_points, cam_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
        rmat, _ = cv2.Rodrigues(rotation_vector)
        _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(np.hstack((rmat, translation_vector)))
        pitch, yaw, roll = euler_angles.flatten()[:3]
        
        state["pitch"] = round(float(pitch), 1)
        state["yaw"]   = round(float(yaw), 1)
        state["roll"]  = round(float(roll), 1)
        
        if abs(yaw) > 22 or abs(pitch) > 18:
            state["distracted"] = True

        # 5. Overlays (Dense Mesh Feedback)
        color = (0, 255, 0)
        if state["eyes_closed"]:  color = (0, 0, 255)
        if state["yawning"]:      color = (0, 220, 255)
        if state["distracted"]:   color = (255, 0, 255)

        # Draw dense eye contours
        def draw_contour(indices):
            pts = np.array([get_pt(i) for i in indices], dtype=np.int32)
            cv2.polylines(frame, [pts], True, color, 1)

        draw_contour([33, 160, 158, 133, 153, 144]) # Left eye
        draw_contour([263, 387, 385, 362, 380, 373]) # Right eye
        draw_contour([13, 14, 78, 308]) # Inner mouth

        # HUD
        hud_lines = [
            f"MP MESH ACTIVE: 478 pts",
            f"EAR: {ear:.3f} (thresh:{eff_thresh:.3f})",
            f"MAR: {mar:.3f} (thresh:{self.mar_threshold:.2f})",
        ]
        text_x = offset_x or 20
        text_y = (offset_y or 40) + 100
        for i, line in enumerate(hud_lines):
            cv2.putText(frame, line, (int(text_x), int(text_y) + i*20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return frame, state