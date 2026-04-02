import sqlite3
import time
import os
from datetime import datetime

class DriverAnalytics:
    """
    Fleet Manager Local DB Handler.
    Automates logging of driver infractions (Drowsiness, Yawning, Distraction).
    D1 & D2 enhancements: Uses precise timestamps and durations to calculate 
    time-decay and severity-weighted robust Risk Scores.
    """
    def __init__(self, db_path="data/fleet_analytics.db"):
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", db_path))
        self.session_id = int(time.time())
        self.start_time = datetime.now()
        self._session_ended = False
        self._last_risk = 0.0
        
        self.events = []
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                        session_id INTEGER PRIMARY KEY,
                        start_time TEXT,
                        end_time TEXT,
                        duration_sec REAL,
                        risk_score REAL
                     )''')
        c.execute('''CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        event_type TEXT,
                        timestamp TEXT,
                        duration_sec REAL,
                        severity REAL
                     )''')
        conn.commit()
        conn.close()

    def log_event(self, event_type, duration_sec=0.0):
        """
        D2: Severity-weighted scoring.
        A 4-second closure is scored much higher natively.
        """
        now = datetime.now()
        severity = 1.0
        
        if event_type == "drowsy":
            severity = max(1.0, duration_sec * 1.5)  # Severe if long closure
        elif event_type == "distraction":
            severity = max(1.0, duration_sec * 1.2)
        elif event_type == "yawn":
            severity = 1.5  # Fixed severity for a distinct yawn event
            
        self.events.append({
            "type": event_type,
            "time": now,
            "duration": duration_sec,
            "severity": severity
        })
        
        # Flush immediately to DB
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO events (session_id, event_type, timestamp, duration_sec, severity)
                     VALUES (?, ?, ?, ?, ?)''',
                  (self.session_id, event_type, now.strftime("%Y-%m-%d %H:%M:%S"), duration_sec, severity))
        conn.commit()
        conn.close()

    def log_drowsiness(self):
        self.log_event("drowsy", duration_sec=2.0) # Legacy fallback wrapper

    def log_yawn(self):
        self.log_event("yawn", duration_sec=1.5)

    def log_distraction(self):
        self.log_event("distraction", duration_sec=1.5)

    def end_session(self):
        if getattr(self, "_session_ended", False):
            return getattr(self, "_last_risk", 0.0)
            
        self._session_ended = True
        end_time = datetime.now()
        session_duration = (end_time - self.start_time).total_seconds()
        
        # D1: Time-decay event weighting
        total_risk = 0.0
        for ev in self.events:
            minutes_ago = (end_time - ev["time"]).total_seconds() / 60.0
            # Events in the last 10 min count 3x more than events from 1h ago
            # We use an exponential decay: Weight = 0.95 ^ minutes_ago
            # e.g., 60 mins ago: 0.95^60 = 0.04 (negligible)
            # e.g., 5 mins ago: 0.95^5 = 0.77
            decay_factor = (0.95 ** max(0, minutes_ago))
            
            # Base logic map
            w = 0
            if ev["type"] == "drowsy":
                w = 20 * ev["severity"]
            elif ev["type"] == "distraction":
                w = 10 * ev["severity"]
            elif ev["type"] == "yawn":
                w = 5 * ev["severity"]
                
            total_risk += w * decay_factor
            
        final_risk = min(100.0, total_risk)
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO sessions 
                     (session_id, start_time, end_time, duration_sec, risk_score)
                     VALUES (?, ?, ?, ?, ?)''',
                  (self.session_id, self.start_time.strftime("%Y-%m-%d %H:%M:%S"), 
                   end_time.strftime("%Y-%m-%d %H:%M:%S"), session_duration, final_risk))
        conn.commit()
        conn.close()
        self._last_risk = round(final_risk, 1)
        return self._last_risk
