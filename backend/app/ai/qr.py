"""Reads the bin QR stickers in video frames and checks the random instruction was followed."""
import cv2

from .detector import load_bgr

_detector = cv2.QRCodeDetector()


def _texts(img):
    """QR texts in img, cheapest first. detectAndDecode returns one code only, so when it finds a
    code that is not readable or not ours (a shop's menu, an advert on the bin), decode all of them."""
    try:
        text, points, _ = _detector.detectAndDecode(img)
    except cv2.error:
        return
    yield text
    if points is None:                                   # no code at all: skip the slower search
        return
    try:
        found, texts, _points, _ = _detector.detectAndDecodeMulti(img)
    except cv2.error:
        return
    if found:
        yield from texts


def read_qr(image, prefix):
    """Return the decoded text if a bin QR code (starting with prefix) is visible, else None."""
    img = load_bgr(image)
    candidates = [img]
    h, w = img.shape[:2]
    if max(h, w) < 900:                                  # small frames: try an upscaled copy too
        candidates.append(cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    for candidate in candidates:
        for text in _texts(candidate):
            if text and text.startswith(prefix):
                return text
    return None


def instruction_followed(qr_flags, instruction):
    """qr_flags[i] is True when frame i shows a bin QR code.

    qr_first: the QR appears in the first third, and the spot is shown afterwards.
    qr_last:  the spot is shown first, and the QR appears from the second half on.
    """
    n = len(qr_flags)
    if n < 2 or not any(qr_flags):
        return False
    first = qr_flags.index(True)
    position = first / (n - 1)
    if instruction == "qr_first":
        return position <= 0.34 and any(not f for f in qr_flags[first + 1:])
    if instruction == "qr_last":
        return position >= 0.5 and first >= 1
    return False
