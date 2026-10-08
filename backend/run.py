"""Start the API on the laptop. Phones on the same Wi-Fi/hotspot reach it at http://<laptop-ip>:5000"""
import os

from app import create_app

app = create_app()

import socket

def _find_port(preferred):
    for p in range(preferred, preferred + 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", p))
                if p != preferred:
                    print(f"Port {preferred} is occupied (e.g. macOS AirPlay). Using port {p} instead.")
                return p
            except OSError:
                continue
    return preferred

if __name__ == "__main__":
    if hasattr(app.detector, "warm_up"):
        try:
            app.detector.warm_up()
        except Exception as exc:
            raise SystemExit(f"Cannot load the model at {app.config['MODEL_PATH']}: {exc}\n"
                             "Run python tools/download_model.py or set MODEL_PATH.")
    port = int(os.environ.get("PORT", 5000))
    port = _find_port(port)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

