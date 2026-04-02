import cv2
import threading

class CameraStream:
    """
    Threaded camera reader for smooth, drop-free frames.
    """
    def __init__(self, index=0, width=640, height=480):
        # Use CAP_DSHOW for local webcams (integers), use default backend for IP cameras (URLs).
        if str(index).isdigit():
            self.cap = cv2.VideoCapture(int(index), cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(index)
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.ret,  self.frame = self.cap.read()
        self._running = True
        self._lock    = threading.Lock()
        self._thread  = threading.Thread(target=self._update, daemon=True)
        self._thread.start()

    def _update(self):
        while self._running:
            ret, frame = self.cap.read()
            with self._lock:
                self.ret, self.frame = ret, frame

    def read(self):
        with self._lock:
            return self.ret, self.frame.copy() if self.frame is not None else (False, None)

    def release(self):
        self._running = False
        self._thread.join(timeout=2)
        self.cap.release()