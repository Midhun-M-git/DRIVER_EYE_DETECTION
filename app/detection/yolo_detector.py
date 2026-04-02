import cv2
import numpy as np

class YOLOFaceDetector:
    """
    YOLOv8 used to detect persons/faces as a pre-filter
    to locate the driver region in the frame.
    """

    def __init__(self, model_path, conf=0.5):
        from ultralytics import YOLO
        self.conf  = conf
        self.model = YOLO(model_path)
        self.last_box = None
        print(f"[YOLODetector] Model loaded from {model_path}")

    def _iou(self, boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        if interArea == 0:
            return 0.0
            
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        iou = interArea / float(boxAArea + boxBArea - interArea)
        return iou

    def detect_faces(self, frame):
        """
        Returns list of bounding boxes (x1,y1,x2,y2) for detected persons.
        Applies Temporal Face ID to track the dominant driver.
        """
        results = self.model(frame, conf=self.conf, verbose=False)
        boxes   = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append((x1, y1, x2, y2))
                
        if not boxes:
            return []
            
        if self.last_box is None:
            best_box = max(boxes, key=lambda b: (b[2]-b[0])*(b[3]-b[1]))
            self.last_box = best_box
            return [best_box]
            
        best_iou = 0.0
        best_box = boxes[0]
        for b in boxes:
            iou = self._iou(self.last_box, b)
            if iou > best_iou:
                best_iou = iou
                best_box = b
                
        if best_iou > 0.3 or len(boxes) == 1:
            self.last_box = best_box
            return [best_box]
            
        best_box = max(boxes, key=lambda b: (b[2]-b[0])*(b[3]-b[1]))
        self.last_box = best_box
        return [best_box]

    def annotate(self, frame, boxes):
        for (x1, y1, x2, y2) in boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
            cv2.putText(frame, "Driver ID: 0", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        return frame