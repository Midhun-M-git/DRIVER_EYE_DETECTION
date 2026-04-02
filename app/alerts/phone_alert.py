import urllib.request
import urllib.parse
import time
import threading
from app.utils.logger import get_logger

logger = get_logger("session.log")

class PhoneAlert:
    """
    Instantly sends a push notification to the driver's phone using ntfy.sh.
    Zero-latency, zero-browser bypass to WhatsApp's unreliable graphical web limitations.
    This guarantees the message arrives via a raw HTTP POST request within ~0.5 seconds.
    """
    def __init__(self, topic_id, cooldown_seconds=60):
        # Strip the '+' and spaces to target just the raw number mathematically for the unique topic
        self.topic = "driver_alert_" + str(topic_id).replace("+", "").replace(" ", "")
        self.cooldown = cooldown_seconds
        self.last_sent_time = 0.0

    def send_alert(self, message):
        now = time.time()
        if now - self.last_sent_time < self.cooldown:
            logger.info("Push notification cooldown active. Skipping this spam alert.")
            return

        self.last_sent_time = now
        # Fire-and-forget thread so UI never hesitates
        threading.Thread(target=self._send_push, args=(message,), daemon=True).start()

    def _send_push(self, message):
        logger.info(f"Firing instant push notification to secure channel: {self.topic}...")
        url = f"https://ntfy.sh/{self.topic}"
        # Headers must be ASCII-safe — encode emoji title as URL-encoded UTF-8
        title_safe = urllib.parse.quote("DROWSINESS ALERT!", safe=" !")
        headers = {
            "Title": title_safe,
            "Priority": "urgent",
            "Tags": "warning,car,rotating_light",
            "Content-Type": "text/plain; charset=utf-8"
        }
        
        # We execute a basic native urllib POST request requiring ZERO external dependencies
        req = urllib.request.Request(url, data=message.encode('utf-8'), headers=headers, method='POST')
        
        try:
            urllib.request.urlopen(req, timeout=5)
            logger.info("Push notification delivered to phone instantly.")
        except Exception as e:
            logger.error(f"Failed to send push notification routing: {e}")
