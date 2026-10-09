"""GreenLegacy Slemani API (practice build).

One Flask process holds the API and loads the YOLOv8 model, so there is a single thing to run
on a laptop. The municipality dashboard is served from /dashboard by the same process.
"""
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from .ai.describe import make_describer
from .ai.detector import make_detector
from .config import Config
from .db import close_db
from .otp import make_otp_sender


def create_app(overrides=None, detector=None, describer=None, otp_sender=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024
    app.detector = detector or make_detector(app.config)
    app.describer = describer if describer is not None else make_describer(app.config)
    app.otp_sender = otp_sender or make_otp_sender(app.config)      # email codes (app/otp.py)

    from . import admin, auth, otp, rewards, routes, simulator
    app.register_blueprint(auth.bp)
    app.register_blueprint(otp.bp)
    app.register_blueprint(routes.bp)
    app.register_blueprint(rewards.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(simulator.bp)
    app.teardown_appcontext(close_db)

    @app.get("/files/<path:name>")
    def files(name):
        return send_from_directory(app.config["UPLOAD_DIR"], name)

    @app.get("/health")
    def health():
        # what this running process actually uses, so tools/preflight.py --server can check it
        return jsonify({"ok": True, "map_center": app.config["MAP_CENTER"],
                        "detector": app.config["DETECTOR_KIND"],
                        "model": Path(app.config["MODEL_PATH"]).name})

    @app.after_request
    def cors(response):   # the Flutter web build and the dashboard may run on other ports
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    return app
