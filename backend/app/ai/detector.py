"""Litter detection.

YoloDetector     — the real one: YOLOv8 through ultralytics. Point MODEL_PATH at the public trash
                   model (and set LITTER_CLASSES=*) or at stock yolov8n.pt (bottles, cups...).
ColorBlobDetector — counts bright red blobs. Only for automated tests and for rehearsing the
                   flow with red paper "litter" when no model is available. Never for the demo.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class Detection:
    count: int
    classes: dict = field(default_factory=dict)   # class name -> count
    coverage: float = 0.0                          # share of the image covered by litter boxes
    boxes: list = field(default_factory=list)      # [x1, y1, x2, y2, class, confidence]


def load_bgr(image):
    """Accept a file path or an already-loaded BGR array."""
    if isinstance(image, np.ndarray):
        return image
    img = cv2.imread(str(image))
    if img is None:
        raise ValueError(f"cannot read image: {image}")
    return img


def _summarise(boxes, shape):
    h, w = shape[:2]
    mask = np.zeros((h, w), dtype=bool)
    classes = {}
    for x1, y1, x2, y2, cls, _conf in boxes:
        mask[max(0, y1):min(h, y2), max(0, x1):min(w, x2)] = True
        classes[cls] = classes.get(cls, 0) + 1
    return Detection(count=len(boxes), classes=classes, coverage=float(mask.mean()), boxes=boxes)


class YoloDetector:
    def __init__(self, model_path, litter_classes="*", confidence=0.25):
        self.model_path = model_path
        self.confidence = confidence
        names = [c.strip() for c in litter_classes.split(",") if c.strip()]
        self.litter = None if names == ["*"] else set(names)
        self._model = None
        self._class_ids = None

    def _model_once(self):
        if self._model is None:
            from ultralytics import YOLO   # imported lazily: heavy, and tests may not need it
            model = YOLO(self.model_path)
            if self.litter is not None:
                self._class_ids = [i for i, n in model.names.items() if n in self.litter]
            self._model = model
        return self._model

    def warm_up(self):
        """Load the model and run it once, so a wrong MODEL_PATH fails at startup and the first
        citizen's report is not the slow one."""
        self.detect(np.zeros((64, 64, 3), dtype=np.uint8))

    def detect(self, image):
        img = load_bgr(image)
        # Only litter classes take part, and NMS ignores the class: otherwise one glass can come
        # back as a cup, a bottle and a wine glass and be counted three times.
        result = self._model_once().predict(img, conf=self.confidence, classes=self._class_ids,
                                            agnostic_nms=True, verbose=False)[0]
        names = result.names
        boxes = []
        for b in result.boxes:
            cls = names[int(b.cls)]
            if self.litter is not None and cls not in self.litter:
                continue
            x1, y1, x2, y2 = (int(v) for v in b.xyxy[0].tolist())
            boxes.append([x1, y1, x2, y2, cls, round(float(b.conf), 3)])
        return _summarise(boxes, img.shape)


class ColorBlobDetector:
    """Counts saturated red blobs larger than min_area pixels. Test/rehearsal only."""

    def __init__(self, min_area=150):
        self.min_area = min_area

    def detect(self, image):
        img = load_bgr(image)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        low = cv2.inRange(hsv, (0, 150, 120), (8, 255, 255))
        high = cv2.inRange(hsv, (172, 150, 120), (180, 255, 255))
        mask = cv2.morphologyEx(low | high, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in contours:
            if cv2.contourArea(c) < self.min_area:
                continue
            x, y, w, h = cv2.boundingRect(c)
            boxes.append([x, y, x + w, y + h, "red_item", 1.0])
        return _summarise(boxes, img.shape)


def make_detector(cfg):
    kind = cfg.get("DETECTOR_KIND", "yolo")
    if kind == "colorblob":
        return ColorBlobDetector()
    return YoloDetector(cfg["MODEL_PATH"], cfg["LITTER_CLASSES"], cfg["DETECT_CONFIDENCE"])
