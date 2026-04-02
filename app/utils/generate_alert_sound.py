"""
Run this script once to generate a simple alert beep WAV.
Usage: python app/utils/generate_alert_sound.py
"""
import struct, wave, math, os

def generate_beep(filename, freq=1000, duration=0.8, volume=0.8, sample_rate=44100):
    n_samples = int(sample_rate * duration)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            t   = i / sample_rate
            val = volume * math.sin(2 * math.pi * freq * t)
            wf.writeframes(struct.pack("<h", int(val * 32767)))
    print(f"Alert sound saved → {filename}")

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sounds", "alert.wav")
    generate_beep(os.path.abspath(out))