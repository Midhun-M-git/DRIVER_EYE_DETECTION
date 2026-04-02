from flask import Flask, Response, jsonify
import threading
import cv2

app = Flask(__name__)

# Primary Data Transport Bus connecting Tkinter UI thread to network Flask thread natively
shared_state = {
    "frame": None,
    "metrics": {
        "ear": 0.0, "mar": 0.0,
        "pitch": 0.0, "yaw": 0.0, "roll": 0.0,
        "drowsy": False, "yawning": False, "distracted": False,
        "fps": 0.0
    }
}

def generate_mjpeg():
    """
    Indefinite loop grabbing the latest annotated memory frame and compressing it
    out over the network to browser clients via Multi-Part MJPEG serialization.
    """
    while True:
        if shared_state["frame"] is not None:
            ret, buffer = cv2.imencode('.jpg', shared_state["frame"], [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ret: continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else:
            yield b''

@app.route('/video_feed')
def video_feed():
    return Response(generate_mjpeg(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/metrics')
def metrics():
    # Expose raw driving metrics payload for automated telemetry dashboards to poll easily
    return jsonify(shared_state["metrics"])

def run_flask():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) # Suppress flask spam to keep cmd clean
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def start_server():
    """
    Spins the heavy networking webserver safely into a background system daemon
    so the 0.0.0.0 socket listener does not freeze the Tkinter core frame loop.
    """
    threading.Thread(target=run_flask, daemon=True, name="FlaskFleetServer").start()
