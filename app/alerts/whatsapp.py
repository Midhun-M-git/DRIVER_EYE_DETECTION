import pywhatkit
import threading
import time
import datetime
from app.utils.logger import get_logger
from config.settings import LOG_FILE

logger = get_logger(LOG_FILE)

class WhatsAppAlert:
    """
    Sends WhatsApp messages using pywhatkit. 
    Runs on a background thread so it doesn't block GUI or camera processing.
    """
    def __init__(self, target_number, cooldown_seconds):
        self.target_number = target_number
        self.cooldown = cooldown_seconds
        self.last_sent_time = 0.0
        self._lock = threading.Lock()
        
    def send_alert(self, message):
        """Attempts to send alert if cooldown has passed."""
        with self._lock:
            now = time.time()
            if now - self.last_sent_time >= self.cooldown:
                self.last_sent_time = now
                threading.Thread(target=self._send_message_thread, args=(message,), daemon=True).start()
                return True
            return False

    def _send_message_thread(self, message):
        logger.info(f"Preparing to send WhatsApp alert to {self.target_number}...")
        try:
            # wait_time=25 allows slower wifi to fully mount the whatsapp web javascript before firing the automated ENTER keystroke
            pywhatkit.sendwhatmsg_instantly(
                phone_no=self.target_number,
                message=message,
                wait_time=25,
                tab_close=True,
                close_time=5
            )
            logger.info("WhatsApp alert sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send WhatsApp alert: {e}")
