"""Synthetic scenes for automated tests and for rehearsing the flow without going outside.

A "place" is a textured random scene (ORB finds plenty of corners in it). "Litter" is red
rectangles, which ColorBlobDetector counts. A cleanup "video" is a handful of frames of the same
place seen from slightly different angles, with the bin QR sticker at the start or the end.
"""
import cv2
import numpy as np
import qrcode

W, H = 640, 480


def place(seed):
    rng = np.random.default_rng(seed)
    img = rng.integers(60, 200, (H, W, 3), dtype=np.uint8)
    img = cv2.GaussianBlur(img, (7, 7), 0)
    for _ in range(60):
        b, g, r = (int(c) for c in rng.integers(0, 255, 3))
        colour = (b, g, min(r, max(b, g)))                       # red never dominates: not "litter"
        kind = rng.integers(0, 3)
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        if kind == 0:
            cv2.rectangle(img, (x, y), (x + int(rng.integers(10, 80)), y + int(rng.integers(10, 80))), colour, -1)
        elif kind == 1:
            cv2.circle(img, (x, y), int(rng.integers(5, 40)), colour, -1)
        else:
            cv2.line(img, (x, y), (int(rng.integers(0, W)), int(rng.integers(0, H))), colour, int(rng.integers(1, 5)))
    return img


def with_litter(img, count, seed=0):
    rng = np.random.default_rng(seed + 1000)
    out = img.copy()
    for _ in range(count):
        x, y = int(rng.integers(20, W - 60)), int(rng.integers(20, H - 60))
        cv2.rectangle(out, (x, y), (x + 34, y + 24), (0, 0, 230), -1)   # BGR red
    return out


def view(img, step):
    """The same place from a slightly different camera position."""
    angle = (step % 5 - 2) * 1.2
    scale = 1.0 + 0.015 * (step % 3)
    m = cv2.getRotationMatrix2D((W / 2, H / 2), angle, scale)
    m[0, 2] += 6 * step
    m[1, 2] += 3 * (step % 4)
    return cv2.warpAffine(img, m, (W, H), borderMode=cv2.BORDER_REFLECT)


def qr_sticker(text="GL-BIN-001", step=0):
    q = qrcode.QRCode(border=4, box_size=10)
    q.add_data(text)
    q.make(fit=True)
    sticker = np.array(q.make_image(fill_color="black", back_color="white").convert("RGB"))[:, :, ::-1]
    sticker = cv2.resize(sticker, (300, 300), interpolation=cv2.INTER_NEAREST)
    frame = np.full((H, W, 3), (40 + 10 * step, 90, 60), dtype=np.uint8)   # a green bin
    y, x = (H - 300) // 2, (W - 300) // 2 + 5 * step
    frame[y:y + 300, x:x + 300] = sticker
    return frame


def cleanup_frames(scene, instruction, count=6, qr_text="GL-BIN-001"):
    """Frames that follow the instruction: QR sticker first (2 frames) or last (2 frames)."""
    spot = [view(scene, i + 1) for i in range(count - 2)]
    sticker = [qr_sticker(qr_text, i) for i in range(2)]
    return sticker + spot if instruction == "qr_first" else spot + sticker


def encode(img):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    assert ok
    return buf.tobytes()
