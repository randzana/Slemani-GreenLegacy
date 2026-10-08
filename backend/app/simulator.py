"""Stand-in camera for the iOS Simulator (and Android emulators), which have no real camera.

When the app finds no camera it asks these endpoints for pictures instead:
  GET /sim/report-photo                  a new random place with red "litter" (ColorBlobDetector)
  GET /sim/cleanup-frame?report_id=&instruction=&frame=&count=
                                         one frame of an honest after-video of that report's
                                         place: the red litter painted out, the bin QR sticker
                                         first or last as the instruction asks

Only on when SIM_CAMERA is set (on by default with DETECTOR_KIND=colorblob), never in a pilot.
"""
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from flask import Blueprint, Response, abort, current_app, request

from .db import query
from .storage import path_of

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import synthetic  # noqa: E402

bp = Blueprint("sim", __name__, url_prefix="/sim")


@bp.before_request
def only_when_enabled():
    if not current_app.config.get("SIM_CAMERA"):
        abort(404)


def _jpeg(img):
    return Response(synthetic.encode(img), mimetype="image/jpeg", headers={"Cache-Control": "no-store"})


def _without_litter(img):
    """Paint out the red blobs ColorBlobDetector counts, keeping the rest of the place."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 120, 90), (10, 255, 255)) | cv2.inRange(hsv, (170, 120, 90), (180, 255, 255))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)
    return cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)


@bp.get("/report-photo")
def report_photo():
    seed = random.randint(1, 1_000_000)
    return _jpeg(synthetic.with_litter(synthetic.place(seed), random.randint(4, 12), seed))


@bp.get("/cleanup-frame")
def cleanup_frame():
    try:
        report_id = int(request.args["report_id"])
        frame = int(request.args.get("frame", 0))
        count = int(request.args.get("count", 8))
    except (KeyError, ValueError):
        abort(400)
    instruction = request.args.get("instruction", "qr_first")
    row = query("SELECT photo_path FROM reports WHERE id = %s", (report_id,), one=True)
    if row is None:
        abort(404)
    before = cv2.imread(str(path_of(row["photo_path"])))
    if before is None:
        abort(404)
    scene = _without_litter(cv2.resize(before, (synthetic.W, synthetic.H)))
    frames = synthetic.cleanup_frames(scene, instruction, count=max(count, 4))
    return _jpeg(frames[min(max(frame, 0), len(frames) - 1)])
