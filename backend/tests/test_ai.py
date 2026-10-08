import cv2
import numpy as np

from app.ai.detector import ColorBlobDetector
from app.ai.hashing import hamming, phash_int
from app.ai.qr import instruction_followed, read_qr
from app.ai.same_place import orb_inliers
from app.ai.scoring import dirtiness
from tools import synthetic


def test_dirtiness_bands():
    assert dirtiness(0, 0) == 0
    assert dirtiness(1, 0.01) == 1
    assert dirtiness(4, 0.05) == 2
    assert dirtiness(8, 0.05) == 3
    assert dirtiness(15, 0.05) == 4
    assert dirtiness(30, 0.05) == 5
    assert dirtiness(2, 0.4) == 3          # a few big items still make a dirty spot
    assert dirtiness(30, 0.9) == 5         # capped


def test_colorblob_counts_red_items():
    scene = synthetic.place(1)
    assert ColorBlobDetector().detect(scene).count == 0
    assert ColorBlobDetector().detect(synthetic.with_litter(scene, 5)).count >= 4


def test_hash_same_and_different():
    a = synthetic.place(1)
    assert hamming(phash_int(a), phash_int(a.copy())) == 0
    assert hamming(phash_int(a), phash_int(synthetic.place(2))) > 10


def test_qr_is_read_with_prefix_only():
    assert read_qr(synthetic.qr_sticker("GL-BIN-007"), "GL-BIN") == "GL-BIN-007"
    assert read_qr(synthetic.qr_sticker("https://example.com"), "GL-BIN") is None
    assert read_qr(synthetic.place(3), "GL-BIN") is None


def test_qr_is_read_next_to_another_qr_code():
    """A bin sticker beside a shop's or an advert's QR code: OpenCV's single decode returns the
    other code (or nothing), which used to hide the sticker and fail an honest cleanup."""
    sticker = cv2.resize(synthetic.qr_sticker("GL-BIN-007"), (320, 240))
    for other in ("https://example.com/menu", "WIFI:S:cafe;T:WPA;P:12345678;;"):
        advert = cv2.resize(synthetic.qr_sticker(other), (320, 240))
        for pair in ([advert, sticker], [sticker, advert]):
            frame = np.vstack([np.hstack(pair), cv2.resize(synthetic.place(3), (640, 240))])
            frame = cv2.imdecode(np.frombuffer(synthetic.encode(frame), np.uint8), cv2.IMREAD_COLOR)
            assert read_qr(frame, "GL-BIN") == "GL-BIN-007"
        assert read_qr(cv2.resize(synthetic.qr_sticker(other), (320, 240)), "GL-BIN") is None


def test_instruction_order():
    assert instruction_followed([True, True, False, False, False, False], "qr_first")
    assert not instruction_followed([False, False, False, False, True, True], "qr_first")
    assert instruction_followed([False, False, False, False, True, True], "qr_last")
    assert not instruction_followed([True, True, False, False, False, False], "qr_last")
    assert not instruction_followed([False] * 6, "qr_first")
    assert not instruction_followed([True] * 6, "qr_first")    # the spot is never shown


def test_same_place_scores_higher_than_a_different_place():
    scene = synthetic.place(5)
    same = orb_inliers(synthetic.with_litter(scene, 4), synthetic.view(scene, 2))
    other = orb_inliers(synthetic.with_litter(scene, 4), synthetic.place(6))
    assert same >= 20
    assert other < 20
