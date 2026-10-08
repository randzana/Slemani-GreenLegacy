"""Same-place check with OpenCV ORB features (no model needed).
Returns the number of RANSAC homography inliers between two photos: high = same scene."""
import cv2
import numpy as np

from .detector import load_bgr

_orb = cv2.ORB_create(nfeatures=1500)
_matcher = cv2.BFMatcher(cv2.NORM_HAMMING)


def _prepare(image, max_side=800):
    img = load_bgr(image)
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def orb_inliers(image_a, image_b):
    a, b = _prepare(image_a), _prepare(image_b)
    kp_a, des_a = _orb.detectAndCompute(a, None)
    kp_b, des_b = _orb.detectAndCompute(b, None)
    if des_a is None or des_b is None or len(kp_a) < 8 or len(kp_b) < 8:
        return 0
    good = []
    for pair in _matcher.knnMatch(des_a, des_b, k=2):
        if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance:
            good.append(pair[0])
    if len(good) < 8:
        return 0
    src = np.float32([kp_a[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_b[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    _h, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return int(mask.sum()) if mask is not None else 0
