import os
import threading
import time

class AlarmSystem:
    """
    Robust Windows Audio API fallback.
    Plays a loud alerting loop indefinitely until stopped. Completely bypasses Pygame 
    mixer initialization errors by using native winsound ASYNC looping.
    """
    def __init__(self, sound_path=None):
        self.sound_path = sound_path
        self._playing   = False

    def trigger(self):
        if self._playing: return
        self._playing = True
        
        import winsound
        try:
            if self.sound_path and os.path.exists(self.sound_path):
                # Play asynchronously and Loop forever until stop() is called natively
                winsound.PlaySound(self.sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
            else:
                # If WAV missing, use hardware motherboard beep looping on a separate thread
                def _fallback():
                    while self._playing:
                        winsound.Beep(1200, 300)
                        time.sleep(0.1)
                threading.Thread(target=_fallback, daemon=True).start()
        except:
            pass

    def stop(self):
        if not self._playing: return
        self._playing = False
        import winsound
        try:
            # SND_PURGE forcefully terminates any ASYNC looping PlaySound executing globally
            winsound.PlaySound(None, winsound.SND_PURGE)
        except:
            pass